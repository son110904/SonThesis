"""
recommender.py – AI CV Review (Bước 11) — CHỨC NĂNG TRUNG TÂM của hệ thống.

Hệ thống được định hướng là "AI CV Review": đọc, đánh giá và nhận xét CV của người
dùng đối với một vị trí mong muốn. Skill Gap chỉ đóng vai trò HỖ TRỢ giải thích.

LLM nhận bối cảnh (scores, candidate profile, core skills của nghề, matched/missing
skills) và trả về JSON có cấu trúc gồm 6 phần:
    - overall_assessment : Đánh giá tổng quan + GIẢI THÍCH nguyên nhân (không chung chung).
    - strengths          : Điểm mạnh, gắn trực tiếp với kinh nghiệm/dự án/kỹ năng trong CV.
    - missing_skills     : Kỹ năng còn thiếu / chưa thể hiện rõ (cụ thể).
    - cv_quality         : Chất lượng trình bày CV (mô tả ngắn, thiếu số liệu, thiếu vai trò…).
    - recommendations    : Đề xuất cải thiện CỤ THỂ, gắn với điểm yếu đã phát hiện.
    - learning_roadmap   : Lộ trình phát triển cá nhân hóa theo từng giai đoạn.

Ràng buộc với LLM (đưa vào system prompt):
    • Mọi nhận xét dựa trên NỘI DUNG THỰC TẾ của CV; không bịa kinh nghiệm/kỹ năng.
    • Mỗi nhận xét phải có lý do/bằng chứng. Không nói chung chung.
    • Không chỉ dựa vào Match Score — đó chỉ là tín hiệu hỗ trợ.
    • Văn phong như chuyên viên tuyển dụng / mentor đang review CV. Tiếng Việt.

Thiếu OPENAI_API_KEY → trả None (tầng trên xử lý placeholder).
"""

from __future__ import annotations

import logging
from typing import Optional

from src.models import CandidateProfile, ScoreBreakdown, SkillGap
from src.online.recommendation_step11.llm_client import LLMClient, get_llm_client

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Bạn là chuyên viên tuyển dụng cấp cao kiêm mentor nghề nghiệp, đang review CV của "
    "ứng viên cho một vị trí cụ thể. Nhiệm vụ: đọc kỹ hồ sơ và đưa ra nhận xét sắc bén, "
    "cá nhân hóa, như một người thật đang đánh giá CV.\n"
    "RÀNG BUỘC BẮT BUỘC:\n"
    "1. Chỉ dựa trên NỘI DUNG THỰC TẾ trong hồ sơ ứng viên được cung cấp. TUYỆT ĐỐI "
    "không bịa ra kinh nghiệm, dự án hay kỹ năng không xuất hiện.\n"
    "2. Mỗi nhận xét phải gắn với BẰNG CHỨNG cụ thể (trích chi tiết từ kinh nghiệm/dự "
    "án/kỹ năng của ứng viên). Không nhận xét chung chung kiểu 'hãy học thêm kỹ năng'.\n"
    "3. KHÔNG chỉ dựa vào Match Score; điểm số chỉ là tín hiệu hỗ trợ. Kết luận phải "
    "xây dựng từ toàn bộ hồ sơ, occupation profile, matched/missing skills.\n"
    "4. Nếu CV thiếu thông tin để đánh giá một mục, hãy NÓI RÕ là chưa thể hiện, thay "
    "vì suy diễn.\n"
    "5. Trả về DUY NHẤT một JSON hợp lệ theo schema yêu cầu, bằng tiếng Việt."
)

# Schema mô tả trong prompt để LLM trả JSON đúng cấu trúc.
_JSON_SCHEMA_HINT = """Trả về JSON với đúng các khóa sau:
{
  "overall_assessment": "string — đánh giá mức độ phù hợp của CV với vị trí, GIẢI THÍCH rõ nguyên nhân dựa trên hồ sơ thực tế (3-5 câu).",
  "strengths": ["string — mỗi điểm mạnh gắn với kinh nghiệm/dự án/kỹ năng CỤ THỂ trong CV"],
  "missing_skills": ["string — kỹ năng còn thiếu hoặc chưa thể hiện rõ, vd 'Chưa thấy kinh nghiệm Microservices', 'Redis chưa xuất hiện'"],
  "cv_quality": ["string — nhận xét về cách trình bày CV, vd 'Mô tả dự án quá ngắn', 'Chưa lượng hóa kết quả bằng số liệu', 'Chưa nêu rõ vai trò trong dự án'"],
  "recommendations": ["string — đề xuất cải thiện CỤ THỂ, gắn trực tiếp với điểm yếu vừa nêu"],
  "learning_roadmap": [
    {"phase": "string — tên giai đoạn, vd 'Giai đoạn 1 (0-1 tháng)'", "focus": "string — trọng tâm", "items": ["string — việc cần làm/kỹ năng cần học cụ thể"]}
  ]
}"""

_USER_TEMPLATE = """Hãy review CV của ứng viên cho vị trí "{occupation}".

## Tín hiệu điểm số (THANG 0-100, chỉ hỗ trợ — KHÔNG được kết luận chỉ dựa vào đây)
- Match Score tổng: {match_score:.0f}
- Semantic Similarity: {semantic:.0f}
- Weighted Skill Score: {weighted:.0f}

## Yêu cầu của vị trí (Occupation Profile)
- Kỹ năng cốt lõi (core): {core_skills}

## Hồ sơ ứng viên (trích từ CV — đây là NGUỒN SỰ THẬT)
- Kỹ năng: {cand_skills}
- Kinh nghiệm:
{cand_exp}
- Dự án:
{cand_proj}
- Học vấn: {cand_edu}

## Đối chiếu kỹ năng (hỗ trợ giải thích)
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
    """Chuẩn hóa giá trị LLM về list[str] (LLM đôi khi trả string đơn)."""
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


def generate_cv_review(
    occupation_display: str,
    occupation_profile: dict,
    scores: ScoreBreakdown,
    candidate_profile: CandidateProfile,
    skill_gap: SkillGap,
    llm: Optional[LLMClient] = None,
) -> Optional[dict]:
    """
    Sinh AI CV Review có cấu trúc (6 phần) từ toàn bộ bối cảnh.

    Returns:
        dict 6 khóa (xem _normalize_review), hoặc None nếu LLM không khả dụng / lỗi.
    """
    llm = llm or get_llm_client()
    if not llm.is_available():
        logger.warning("LLM không khả dụng → bỏ qua AI CV Review.")
        return None

    core_skills = list(occupation_profile.get("core_skills", {}).keys())

    user_prompt = _USER_TEMPLATE.format(
        occupation=occupation_display,
        match_score=scores.match_score * 100,
        semantic=scores.semantic_similarity_score * 100,
        weighted=scores.weighted_skill_score * 100,
        core_skills=_fmt_inline(core_skills, 20),
        cand_skills=_fmt_inline(candidate_profile.skills, 30),
        cand_exp=_fmt_bullets(candidate_profile.experience, 8),
        cand_proj=_fmt_bullets(candidate_profile.projects, 8),
        cand_edu=_fmt_inline(candidate_profile.education, 5),
        matched=_fmt_inline(skill_gap.matched_skills, 30),
        missing=_fmt_inline(skill_gap.missing_skills, 25),
        schema=_JSON_SCHEMA_HINT,
    )

    raw = llm.chat_json(_SYSTEM_PROMPT, user_prompt, temperature=0.3, max_tokens=2000)
    if not raw:
        logger.warning("AI CV Review: LLM trả rỗng/parse lỗi.")
        return None

    review = _normalize_review(raw)
    logger.info(
        f"AI CV Review sinh thành công "
        f"(strengths={len(review['strengths'])}, missing={len(review['missing_skills'])}, "
        f"cv_quality={len(review['cv_quality'])}, roadmap={len(review['learning_roadmap'])})"
    )
    return review


def cv_review_to_markdown(review: Optional[dict]) -> Optional[str]:
    """Render AI CV Review (dict) → markdown để lưu/hiển thị dạng văn bản (fallback)."""
    if not review:
        return None

    def _bullets(items: list[str]) -> str:
        return "\n".join(f"- {it}" for it in items) if items else "_(không có)_"

    parts: list[str] = []
    if review.get("overall_assessment"):
        parts.append("### 1. Đánh giá tổng quan\n" + review["overall_assessment"])
    parts.append("### 2. Điểm mạnh\n" + _bullets(review.get("strengths", [])))
    parts.append("### 3. Kỹ năng còn thiếu\n" + _bullets(review.get("missing_skills", [])))
    parts.append("### 4. Chất lượng CV\n" + _bullets(review.get("cv_quality", [])))
    parts.append("### 5. Khuyến nghị cải thiện\n" + _bullets(review.get("recommendations", [])))

    roadmap = review.get("learning_roadmap", [])
    if roadmap:
        lines = ["### 6. Lộ trình phát triển"]
        for step in roadmap:
            head = " — ".join(x for x in [step.get("phase"), step.get("focus")] if x)
            lines.append(f"**{head}**" if head else "**Giai đoạn**")
            for it in step.get("items", []):
                lines.append(f"- {it}")
        parts.append("\n".join(lines))

    return "\n\n".join(parts)


# ── Backward-compat: API cũ trả markdown string ────────────────────────────────
def generate_recommendation(
    occupation_display: str,
    scores: ScoreBreakdown,
    candidate_profile: CandidateProfile,
    skill_gap: SkillGap,
    occupation_profile: Optional[dict] = None,
    llm: Optional[LLMClient] = None,
) -> Optional[str]:
    """Wrapper tương thích cũ: sinh CV Review rồi render markdown."""
    review = generate_cv_review(
        occupation_display=occupation_display,
        occupation_profile=occupation_profile or {},
        scores=scores,
        candidate_profile=candidate_profile,
        skill_gap=skill_gap,
        llm=llm,
    )
    return cv_review_to_markdown(review)
