"""
recommender.py – Sinh AI Recommendation (Bước 11) bằng GPT-4o Mini.

Input: toàn bộ bối cảnh (scores, candidate profile, occupation, skill gap).
Output: văn bản khuyến nghị (markdown) gồm: nhận xét tổng quan, điểm mạnh,
kỹ năng còn thiếu, hướng cải thiện, gợi ý học tập.

Thiếu OPENAI_API_KEY → trả None (placeholder do tầng trên xử lý).
"""

from __future__ import annotations

import logging
from typing import Optional

from src.models import CandidateProfile, ScoreBreakdown, SkillGap
from src.online.recommendation.llm_client import LLMClient, get_llm_client

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Bạn là cố vấn nghề nghiệp chuyên nghiệp, phân tích mức độ phù hợp giữa ứng "
    "viên và một nhóm nghề. Trả lời bằng tiếng Việt, văn phong khích lệ nhưng "
    "thẳng thắn, có cấu trúc rõ ràng bằng markdown."
)

_USER_TEMPLATE = """Hãy phân tích mức độ phù hợp của ứng viên với nghề "{occupation}".

## Điểm số (thang 0-100)
- Match Score tổng: {match_score:.0f}
- Semantic Similarity: {semantic:.0f}
- Weighted Skill Score: {weighted:.0f}

## Hồ sơ ứng viên
- Kỹ năng: {cand_skills}
- Kinh nghiệm: {cand_exp}
- Dự án: {cand_proj}
- Học vấn: {cand_edu}

## Kỹ năng theo nghề
- Đã đáp ứng (matched): {matched}
- Còn thiếu (missing, ưu tiên cao trước): {missing}

Trả lời theo đúng các mục markdown sau:
### 1. Nhận xét tổng quan
(Đánh giá mức độ phù hợp dựa trên điểm số)
### 2. Điểm mạnh
(Dựa trên kỹ năng đã đáp ứng và hồ sơ)
### 3. Kỹ năng còn thiếu quan trọng
(Phân tích các kỹ năng missing đáng ưu tiên)
### 4. Hướng cải thiện
(Gợi ý cụ thể, khả thi)
### 5. Khuyến nghị học tập & phát triển
(Khóa học, chứng chỉ, lộ trình)
"""


def _fmt_list(items: list[str], limit: int = 15) -> str:
    if not items:
        return "(không có)"
    shown = items[:limit]
    suffix = f" … (+{len(items) - limit})" if len(items) > limit else ""
    return ", ".join(shown) + suffix


def generate_recommendation(
    occupation_display: str,
    scores: ScoreBreakdown,
    candidate_profile: CandidateProfile,
    skill_gap: SkillGap,
    llm: Optional[LLMClient] = None,
) -> Optional[str]:
    """
    Sinh khuyến nghị AI từ toàn bộ bối cảnh phân tích.

    Returns:
        Văn bản markdown, hoặc None nếu LLM không khả dụng / lỗi.
    """
    llm = llm or get_llm_client()
    if not llm.is_available():
        logger.warning("LLM không khả dụng → bỏ qua AI recommendation.")
        return None

    user_prompt = _USER_TEMPLATE.format(
        occupation=occupation_display,
        match_score=scores.match_score * 100,
        semantic=scores.semantic_similarity_score * 100,
        weighted=scores.weighted_skill_score * 100,
        cand_skills=_fmt_list(candidate_profile.skills, 25),
        cand_exp=_fmt_list(candidate_profile.experience, 6),
        cand_proj=_fmt_list(candidate_profile.projects, 6),
        cand_edu=_fmt_list(candidate_profile.education, 4),
        matched=_fmt_list(skill_gap.matched_skills, 25),
        missing=_fmt_list(skill_gap.missing_skills, 25),
    )

    text = llm.chat_text(_SYSTEM_PROMPT, user_prompt, temperature=0.4, max_tokens=1400)
    if text:
        logger.info(f"AI recommendation sinh thành công ({len(text)} ký tự)")
    return text
