"""
llm_skill_extractor.py – Trích kỹ năng bằng LLM (bổ sung cho regex).

Hai hàm công khai, cùng một triết lý "hybrid regex + LLM":
  - extract_skills_from_sections(cv_text): cho CV — LLM đọc Experience/Projects.
  - extract_jd_skills(jd_text):            cho JD — LLM đọc toàn bộ tin tuyển dụng.

Lý do cần LLM: tập regex dù lớn đến đâu cũng chỉ bắt được kỹ năng đã liệt kê
sẵn. Tin tuyển dụng ngành hẹp (vd Computer Vision) hay công nghệ mới ra đời sẽ
bị bỏ sót hoàn toàn. LLM đọc hiểu ngữ cảnh nên bắt được phần regex không phủ.

Cả hai đường đều đi qua canonicalize_skill + STOP_SKILLS để kỹ năng của ứng
viên và của JD nằm trên CÙNG một từ vựng — điều kiện bắt buộc để so khớp chuỗi
chính xác ở bước sau hoạt động đúng.

Thiếu OPENAI_API_KEY → tự động lùi về regex-only, không làm hỏng luồng.
"""

from __future__ import annotations

import logging
import re

from src.offline.skill_normalize import canonicalize_skill

logger = logging.getLogger(__name__)

# ─── Regex tách sections khỏi CV ──────────────────────────────────────────────
# Tìm tiêu đề section phổ biến (case-insensitive, flexible).
_SECTION_RE = re.compile(
    r"(?im)^\s*(?:"
    r"experience|work\s*experience|employment|working\s*history|"
    r"projects?|personal\s*projects?|portfolio|dự\s*án|"
    r"summary|profile|objective|career\s*objective|"
    r"certification|certificate|seminars?|chứng\s*chỉ"
    r")\s*[:\-]?\s*$",
    re.MULTILINE,
)
_WHITESPACE_RE = re.compile(r"\n{3,}")


def _extract_section_texts(raw_text: str) -> dict[str, str]:
    """
    Tách text theo sections.

    Returns:
        dict với keys: "experience", "projects", "summary", "certifications".
        Value là text thô của section đó (hoặc "" nếu không có).
    """
    lines = raw_text.splitlines()
    sections: dict[str, list[str]] = {}
    current_key = "other"
    current_lines: list[str] = []

    section_key_map = {
        "experience": ["experience", "work experience", "employment", "working history"],
        "projects": ["projects", "personal projects", "portfolio", "dự án"],
        "summary": ["summary", "profile", "objective", "career objective"],
        "certifications": ["certification", "certificate", "seminars", "chứng chỉ"],
    }

    for line in lines:
        matched_key = None
        stripped = line.strip()
        for key, keywords in section_key_map.items():
            for kw in keywords:
                if stripped.lower().startswith(kw) or stripped.lower().rstrip(":").strip() == kw:
                    matched_key = key
                    break
            if matched_key:
                break

        if matched_key:
            if current_lines:
                sections.setdefault(current_key, []).extend(current_lines)
            current_key = matched_key
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.setdefault(current_key, []).extend(current_lines)

    # Ghép lại thành text
    result = {}
    for key, lines in sections.items():
        text = "\n".join(lines)
        text = _WHITESPACE_RE.sub("\n\n", text).strip()
        result[key] = text

    return result


# LƯU Ý QUAN TRỌNG: llm_client.chat_json() gọi API với
# response_format={"type": "json_object"} → OpenAI BẮT BUỘC trả về một JSON
# OBJECT, không nhận mảng ở cấp cao nhất. Vì vậy prompt phải yêu cầu bọc trong
# khóa "skills". (Trước đây prompt xin mảng trần nên parser luôn nhận dict và
# trả rỗng — LLM extraction thực chất KHÔNG hoạt động dù log vẫn báo "hybrid".)
_JSON_OBJECT_HINT = (
    'Return ONLY a JSON object of the exact form {"skills": ["Skill A", "Skill B"]} '
    "— a single key \"skills\" whose value is an array of plain strings. "
    'If no skills are found, return {"skills": []}.'
)

_LLM_SYSTEM = (
    "You are a skill extraction assistant. Given the candidate profile sections below, "
    "extract all technical and professional skills mentioned in the EXPERIENCE and/or PROJECTS "
    "sections. Focus on:\n"
    "  - Technologies, frameworks, libraries (e.g. React, FastAPI, PyTorch, Docker)\n"
    "  - Tools and platforms (e.g. AWS, PostgreSQL, GitHub, Figma)\n"
    "  - Methodologies (e.g. Agile, Scrum, CI/CD)\n"
    "  - Domain-specific skills (e.g. NLP, Computer Vision, API Design)\n"
    "No descriptions, no explanations. Use conventional casing "
    "(e.g. 'PyTorch', 'REST API', 'Docker').\n"
    + _JSON_OBJECT_HINT
)

# CHÚ Ý: template này đi qua .format() nên KHÔNG được chứa dấu { } của ví dụ
# JSON — hint được nối vào sau khi format xong (xem _extract_llm_skills).
_LLM_USER_TEMPLATE = """Extract skills from these CV sections:

{experiences}

{projects}
"""


def _coerce_skill_list(result) -> list[str]:
    """
    Chuẩn hóa đầu ra LLM về list[str].

    Chấp nhận cả object {"skills": [...]} (định dạng yêu cầu) lẫn mảng trần và
    object có một khóa danh sách bất kỳ — LLM đôi khi tự đổi tên khóa.
    """
    if isinstance(result, list):
        items = result
    elif isinstance(result, dict):
        items = result.get("skills")
        if not isinstance(items, list):
            # Lấy giá trị dạng list đầu tiên nếu LLM đặt tên khóa khác.
            items = next((v for v in result.values() if isinstance(v, list)), [])
    else:
        return []
    return [str(s).strip() for s in items if str(s).strip()]


def _extract_llm_skills(raw_text: str) -> list[str]:
    """
    Gọi LLM 1 lần để trích skill ẩn từ Experience/Projects sections.

    Returns:
        List skill names (raw, chưa canonicalize). Empty list nếu LLM unavailable
        hoặc không trích được.
    """
    try:
        from src.online.recommendation_step11.llm_client import get_llm_client
    except Exception:
        return []

    llm = get_llm_client()
    if not llm.is_available():
        logger.debug("LLM unavailable — bỏ qua skill extraction từ Experience/Projects.")
        return []

    sections = _extract_section_texts(raw_text)
    exp_text = sections.get("experience", "")
    proj_text = sections.get("projects", "")

    # Nếu cả 2 section đều rỗng → bỏ qua
    if not exp_text.strip() and not proj_text.strip():
        logger.debug("CV không có Experience/Projects section — bỏ qua LLM extraction.")
        return []

    user_prompt = (
        _LLM_USER_TEMPLATE.format(
            experiences=exp_text[:3000] if exp_text else "(không có)",
            projects=proj_text[:2000] if proj_text else "(không có)",
        )
        + "\n"
        + _JSON_OBJECT_HINT
    )

    try:
        result = llm.chat_json(_LLM_SYSTEM, user_prompt, temperature=0.0, max_tokens=500)
        skills = _coerce_skill_list(result)
        logger.info(f"LLM trích được {len(skills)} skills từ Experience/Projects.")
        return skills
    except Exception as e:  # noqa: BLE001
        logger.warning(f"LLM skill extraction thất bại: {e}")
        return []


def _merge_and_canonicalize(regex_skills: list[str], llm_skills: list[str]) -> list[str]:
    """
    Gộp 2 nguồn → canonicalize → loại STOP_SKILLS → bỏ trùng.

    STOP_SKILLS phải áp cho CẢ đường LLM: bộ lọc này tồn tại để loại kỹ năng
    không phân biệt được ngành ("giao tiếp", "làm việc nhóm"...), mà LLM thì
    rất hay trả về đúng những thứ đó. Regex vốn đã lọc sẵn bên trong.
    """
    from src.offline.skill_extraction_step2.extractor import _is_stop_skill

    seen: set[str] = set()
    merged: list[str] = []
    for s in regex_skills + llm_skills:
        cs = canonicalize_skill(s)
        if not cs or _is_stop_skill(cs):
            continue
        if cs.lower() not in seen:
            seen.add(cs.lower())
            merged.append(cs)
    return merged


def extract_skills_from_sections(raw_text: str) -> list[str]:
    """
    Hybrid skill extraction cho CV:
      1. Regex (giữ nguyên, nhanh, deterministic).
      2. LLM (bổ sung skill ẩn trong Experience/Projects).
      3. Hợp nhất, canonicalize, lọc STOP_SKILLS.

    Returns:
        List skill đã canonicalize, không trùng.
    """
    # 1. Regex baseline — dùng extractor đã có
    from src.offline.preprocessing_step1.text_cleaner import clean_text
    from src.offline.skill_extraction_step2.extractor import extract_skills_from_text

    cleaned = clean_text(raw_text)
    regex_skills = extract_skills_from_text(cleaned)

    # 2. LLM bổ sung
    llm_skills = _extract_llm_skills(raw_text)

    merged = _merge_and_canonicalize(regex_skills, llm_skills)
    logger.info(
        f"Hybrid skill extraction (CV): {len(regex_skills)} regex + {len(llm_skills)} LLM "
        f"→ {len(merged)} unique (sau canonicalize)"
    )
    return merged


# ══════════════════════════════════════════════════════════════════════════
# JD side
# ══════════════════════════════════════════════════════════════════════════
_LLM_SYSTEM_JD = (
    "You are a skill extraction assistant. Given a job description, extract every "
    "technical and professional skill the employer REQUIRES or PREFERS.\n"
    "INCLUDE:\n"
    "  - Technologies, frameworks, libraries (e.g. PyTorch, OpenCV, Spring Boot)\n"
    "  - Tools, platforms, infrastructure (e.g. AWS, Docker, PostgreSQL)\n"
    "  - Methodologies and practices (e.g. Agile, CI/CD, MLOps)\n"
    "  - Domain/technical competencies (e.g. Computer Vision, Object Detection, "
    "Semantic Segmentation, Financial Reporting)\n"
    "  - Foreign languages when explicitly required (e.g. English, Japanese)\n"
    "EXCLUDE:\n"
    "  - Generic soft skills (teamwork, communication, hard-working, responsible)\n"
    "  - Job titles, seniority levels, years of experience, academic degrees\n"
    "  - Company benefits, salary, working hours, company names\n"
    "No descriptions. Keep each item SHORT (1-4 words) and use conventional casing "
    "(e.g. 'PyTorch', 'REST API', 'Computer Vision').\n"
    + _JSON_OBJECT_HINT
)

# Không chứa dấu { } của ví dụ JSON vì template đi qua .format() — hint nối sau.
_LLM_USER_TEMPLATE_JD = """Extract required skills from this job description:

\"\"\"
{jd_text}
\"\"\"
"""

# Cắt JD trước khi đưa vào prompt — phần yêu cầu ứng viên gần như luôn nằm
# trong khoảng này, phần sau thường là phúc lợi/giới thiệu công ty.
_MAX_JD_CHARS_FOR_LLM = 6000


def _extract_llm_jd_skills(jd_text: str) -> list[str]:
    """Gọi LLM 1 lần để trích kỹ năng yêu cầu từ JD. Trả [] nếu LLM không khả dụng."""
    try:
        from src.online.recommendation_step11.llm_client import get_llm_client
    except Exception:
        return []

    llm = get_llm_client()
    if not llm.is_available():
        logger.debug("LLM unavailable — JD skill extraction chỉ dùng regex.")
        return []
    if not jd_text or not jd_text.strip():
        return []

    user_prompt = (
        _LLM_USER_TEMPLATE_JD.format(jd_text=jd_text[:_MAX_JD_CHARS_FOR_LLM])
        + "\n"
        + _JSON_OBJECT_HINT
    )
    try:
        result = llm.chat_json(_LLM_SYSTEM_JD, user_prompt, temperature=0.0, max_tokens=700)
        skills = _coerce_skill_list(result)
        logger.info(f"LLM trích được {len(skills)} kỹ năng từ JD.")
        return skills
    except Exception as e:  # noqa: BLE001
        logger.warning(f"LLM JD skill extraction thất bại: {e}")
        return []


def extract_jd_skills(jd_text: str) -> list[str]:
    """
    Hybrid skill extraction cho JD (đối xứng với CV):
      1. Regex trên toàn JD.
      2. LLM đọc hiểu JD để bắt kỹ năng regex không phủ.
      3. Hợp nhất, canonicalize, lọc STOP_SKILLS.

    Returns:
        List kỹ năng yêu cầu, đã canonicalize, cùng từ vựng với kỹ năng ứng viên.
    """
    from src.offline.preprocessing_step1.text_cleaner import clean_text
    from src.offline.skill_extraction_step2.extractor import extract_skills_from_text

    if not jd_text or not jd_text.strip():
        return []

    regex_skills = extract_skills_from_text(clean_text(jd_text))
    llm_skills = _extract_llm_jd_skills(jd_text)

    merged = _merge_and_canonicalize(regex_skills, llm_skills)
    logger.info(
        f"Hybrid skill extraction (JD): {len(regex_skills)} regex + {len(llm_skills)} LLM "
        f"→ {len(merged)} unique (sau canonicalize)"
    )
    return merged
