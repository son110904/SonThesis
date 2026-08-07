"""
llm_skill_extractor.py – Trích kỹ năng ẩn trong Experience/Projects bằng LLM.

Chỉ gọi khi LLM khả dụng VÀ CV có sections Experience/Projects/Dự án.
Dùng 1 lần gọi LLM cho toàn bộ CV (prompt ngắn gọn).

Trả về danh sách skill ở dạng thô để caller canonicalize.
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


_LLM_SYSTEM = (
    "You are a skill extraction assistant. Given the candidate profile sections below, "
    "extract all technical and professional skills mentioned in the EXPERIENCE and/or PROJECTS "
    "sections. Focus on:\n"
    "  - Technologies, frameworks, libraries (e.g. React, FastAPI, PyTorch, Docker)\n"
    "  - Tools and platforms (e.g. AWS, PostgreSQL, GitHub, Figma)\n"
    "  - Methodologies (e.g. Agile, Scrum, CI/CD)\n"
    "  - Domain-specific skills (e.g. NLP, Computer Vision, API Design)\n"
    "Return ONLY a JSON array of skill names as plain strings — no descriptions, "
    "no explanations. Use the exact casing you see in the text (e.g. 'PyTorch', 'REST API', 'Docker').\n"
    "If no skills are found in the given sections, return an empty array []."
)

_LLM_USER_TEMPLATE = """Extract skills from these CV sections:

{experiences}

{projects}

Return skills as a JSON array of strings only."""


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

    user_prompt = _LLM_USER_TEMPLATE.format(
        experiences=exp_text[:3000] if exp_text else "(không có)",
        projects=proj_text[:2000] if proj_text else "(không có)",
    )

    try:
        result = llm.chat_json(_LLM_SYSTEM, user_prompt, temperature=0.0, max_tokens=500)
        if not result:
            return []
        if isinstance(result, list):
            skills = [str(s).strip() for s in result if str(s).strip()]
            logger.info(f"LLM trích được {len(skills)} skills từ Experience/Projects.")
            return skills
        return []
    except Exception as e:
        logger.warning(f"LLM skill extraction thất bại: {e}")
        return []


def extract_skills_from_sections(raw_text: str) -> list[str]:
    """
    Hybrid skill extraction:
      1. Regex (giữ nguyên, nhanh, deterministic).
      2. LLM (bổ sung skill ẩn trong Experience/Projects).
      3. Hợp nhất, canonicalize.

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

    # 3. Hợp nhất
    seen: set[str] = set()
    merged: list[str] = []
    for s in regex_skills + llm_skills:
        cs = canonicalize_skill(s)
        if cs and cs.lower() not in seen:
            seen.add(cs.lower())
            merged.append(cs)

    logger.info(
        f"Hybrid skill extraction: {len(regex_skills)} regex + {len(llm_skills)} LLM "
        f"→ {len(merged)} unique (sau canonicalize)"
    )
    return merged
