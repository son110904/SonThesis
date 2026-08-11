"""
jd_recommender.py – AI CV Review cho JD Comparison (chế độ 2).

Tái dùng cùng schema 6 phần với AI CV Review thông thường:
  overall_assessment, strengths, missing_skills, cv_quality,
  recommendations, learning_roadmap.

Khác ở chỗ: không có occupation profile → JD context thay thế.
"""

from __future__ import annotations

import logging
from typing import Optional

from src.models import CandidateProfile
from src.online.recommendation_step11.llm_client import LLMClient, get_llm_client

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT_JD = (
    "Bạn là chuyên viên tuyển dụng cấp cao kiêm mentor nghề nghiệp, đang review CV "
    "của ứng viên đối với một Job Description cụ thể. Nhiệm vụ: đọc kỹ hồ sơ và JD "
    "để đưa ra nhận xét sắc bén, cá nhân hóa.\n"
    "RÀNG BUỘC BẮT BUỘC:\n"
    "1. Chỉ dựa trên NỘI DUNG THỰC TẾ trong CV và JD được cung cấp. TUYỆT ĐỐI "
    "không bịa ra kinh nghiệm, dự án hay kỹ năng không xuất hiện.\n"
    "2. Mỗi nhận xét phải gắn với BẰNG CHỨNG cụ thể từ CV. Không nhận xét chung chung.\n"
    "3. 'Còn thiếu' dựa trên kỹ năng trong JD nhưng không xuất hiện trong CV. "
    "Dùng kiến thức chuyên môn để tự bỏ false-positive (vd: FastAPI ⟹ REST API đã có).\n"
    "4. Hệ thống cung cấp 2 chỉ số độc lập (Semantic Similarity + Weighted Skill Score). "
    "Kết luận dựa trên TOÀN BỘ bối cảnh, không bị ép theo 1 công thức tổng.\n"
    "5. Nếu CV thiếu thông tin để đánh giá, NÓI RÕ là chưa thể hiện, không suy diễn.\n"
    "6. FRESHER/NEW GRADUATE: đánh giá theo góc nhìn khác — Education + Projects + "
    "Career Objective quan trọng hơn Experience.\n"
    "7. Trả về DUY NHẤT một JSON hợp lệ theo schema yêu cầu, bằng tiếng Việt."
)

_JSON_SCHEMA_HINT = """Trả về JSON với đúng các khóa sau:
{
  "overall_assessment": "string — đánh giá mức độ phù hợp của CV với JD cụ thể này (3-5 câu).",
  "strengths": ["string — mỗi điểm mạnh gắn với kinh nghiệm/dự án/kỹ năng CỤ THỂ trong CV"],
  "missing_skills": ["string — kỹ năng trong JD nhưng không xuất hiện hoặc chưa thể hiện rõ trong CV"],
  "cv_quality": ["string — nhận xét chất lượng viết CV"],
  "recommendations": ["string — đề xuất cải thiện CỤ THỂ, gắn trực tiếp với điểm yếu đã phát hiện"],
  "learning_roadmap": [
    {"phase": "string — tên giai đoạn", "focus": "string — trọng tâm", "items": ["string — việc cần làm"]}
  ]
}"""

_USER_TEMPLATE_JD = """Hãy review CV của ứng viên cho vị trí: "{jd_position}".

## Job Description (trích đoạn)
{jd_text_preview}

## Kỹ năng yêu cầu (từ JD)
{jd_skills}

## Tín hiệu điểm số (THANG 0-100, chỉ hỗ trợ)
- Semantic Similarity: {semantic:.0f}
- Tỉ lệ đáp ứng kỹ năng JD: {coverage:.0f}

## Hồ sơ ứng viên (NGUỒN SỰ THẬT)
- Kỹ năng: {cand_skills}
- Kinh nghiệm:
{cand_exp}
- Dự án:
{cand_proj}
- Học vấn: {cand_edu}

## Đối chiếu kỹ năng
- Đã đáp ứng (matched): {matched}
- Còn thiếu (missing, ưu tiên cao trước): {missing}

{schema}

Chỉ trả về JSON, không kèm văn bản ngoài JSON."""


def _fmt_inline(items: list[str], limit: int = 25) -> str:
    if not items:
        return "(không có)"
    shown = items[:limit]
    suffix = f" … (+{len(items) - limit})" if len(items) > limit else ""
    return ", ".join(shown) + suffix


def _fmt_bullets(items: list[str], limit: int = 8) -> str:
    if not items:
        return "  (không có)"
    return "\n".join(f"  - {it}" for it in items[:limit])


def _coerce_str_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        out = []
        for v in value:
            if isinstance(v, str) and v.strip():
                out.append(v.strip())
            elif isinstance(v, dict):
                out.append("; ".join(str(x) for x in v.values() if x))
        return out
    return []


def _normalize_review(raw: dict) -> dict:
    """Đảm bảo đủ 6 khóa, đúng kiểu — phòng khi LLM lệch schema."""
    roadmap_raw = raw.get("learning_roadmap") or []
    roadmap: list[dict] = []
    if isinstance(roadmap_raw, list):
        for step in roadmap_raw:
            if isinstance(step, dict):
                roadmap.append({
                    "phase": str(step.get("phase") or step.get("giai_doan") or "").strip(),
                    "focus": str(step.get("focus") or step.get("trong_tam") or "").strip(),
                    "items": _coerce_str_list(step.get("items") or step.get("skills")),
                })
            elif isinstance(step, str) and step.strip():
                roadmap.append({"phase": "", "focus": step.strip(), "items": []})

    overall = raw.get("overall_assessment")
    if isinstance(overall, list):
        overall = " ".join(str(x) for x in overall)

    return {
        "overall_assessment": (overall or "").strip(),
        "strengths": _coerce_str_list(raw.get("strengths")),
        "missing_skills": _coerce_str_list(raw.get("missing_skills")),
        "cv_quality": _coerce_str_list(raw.get("cv_quality")),
        "recommendations": _coerce_str_list(raw.get("recommendations")),
        "learning_roadmap": roadmap,
    }


def generate_jd_recommendation(
    candidate_profile: CandidateProfile,
    jd_text: str,
    jd_position: str,
    jd_skills: list[str],
    matched_skills: list[str],
    missing_skills: list[str],
    extra_skills: list[str],
    semantic_similarity_score: float,
    coverage_pct: float,
    llm: Optional[LLMClient] = None,
) -> Optional[dict]:
    """
    Sinh AI CV Review cho JD Comparison (chế độ 2).

    Returns:
        dict 6 khóa (cùng schema với AI CV Review thông thường),
        hoặc None nếu LLM unavailable.
    """
    llm = llm or get_llm_client()
    if not llm.is_available():
        logger.warning("LLM không khả dụng → bỏ qua JD Recommendation.")
        return None

    user_prompt = _USER_TEMPLATE_JD.format(
        jd_position=jd_position or "(không xác định được)",
        jd_text_preview=jd_text[:2000],
        jd_skills=_fmt_inline(jd_skills, 30),
        semantic=semantic_similarity_score * 100,
        coverage=coverage_pct * 100,
        cand_skills=_fmt_inline(candidate_profile.skills, 30),
        cand_exp=_fmt_bullets(candidate_profile.experience, 8),
        cand_proj=_fmt_bullets(candidate_profile.projects, 8),
        cand_edu=_fmt_inline(candidate_profile.education, 5),
        matched=_fmt_inline(matched_skills, 30),
        missing=_fmt_inline(missing_skills, 25),
        schema=_JSON_SCHEMA_HINT,
    )

    raw = llm.chat_json(_SYSTEM_PROMPT_JD, user_prompt, temperature=0.3, max_tokens=2000)
    if not raw:
        logger.warning("JD Recommendation: LLM trả rỗng/parse lỗi.")
        return None

    review = _normalize_review(raw)
    logger.info(
        f"JD Recommendation sinh thành công "
        f"(strengths={len(review['strengths'])}, missing={len(review['missing_skills'])}, "
        f"roadmap={len(review['learning_roadmap'])})"
    )
    return review
