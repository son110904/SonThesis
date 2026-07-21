"""
email_service.py – Điều phối AI Application Email Generator.

Chỉ chạy khi người dùng CHỦ ĐỘNG bấm nút "Tạo email ứng tuyển" (tiết kiệm chi phí
LLM). Tái dùng candidate profile + scores + skill gap + AI CV Review ĐÃ TÍNH —
KHÔNG re-extract / re-embed / gọi lại LLM trích profile.
"""

from __future__ import annotations

import logging
from typing import Optional

from src.config import MATCH_ALPHA, MATCH_BETA
from src.models import CandidateProfile, ScoreBreakdown, SkillGap
from src.online.email_generation import generate_application_email
from src.online.services.occupation_loader import get_occupation

logger = logging.getLogger(__name__)


def generate_application_email_for_occupation(
    candidate_profile: dict,
    occupation_key: str,
    match_score: float,
    semantic_similarity_score: float,
    weighted_skill_score: float,
    matched_skills: list[str],
    missing_skills: list[str],
    cv_review: Optional[dict] = None,
) -> Optional[dict]:
    """
    Sinh Application Email cho nghề đã chọn, dùng lại profile + điểm số + AI CV
    Review đã tính.

    Args:
        candidate_profile: dict (skills/experience/projects/education/raw_text) —
            từ AnalysisResult.to_dict()["candidate_profile"].
        occupation_key:    nghề (Occupation Profile) mà người dùng đang xem.
        cv_review:         AI CV Review đã sinh trước đó (bối cảnh, có thể None).

    Raises:
        OccupationNotFound: occupation_key không hợp lệ.
    """
    occupation = get_occupation(occupation_key)
    profile = CandidateProfile(
        skills=candidate_profile.get("skills", []),
        experience=candidate_profile.get("experience", []),
        projects=candidate_profile.get("projects", []),
        education=candidate_profile.get("education", []),
        raw_text=candidate_profile.get("raw_text", ""),
    )
    scores = ScoreBreakdown(
        semantic_similarity_score=semantic_similarity_score,
        weighted_skill_score=weighted_skill_score,
        match_score=match_score,
        alpha=MATCH_ALPHA,
        beta=MATCH_BETA,
    )
    skill_gap = SkillGap(matched_skills=matched_skills, missing_skills=missing_skills)

    # "_display" là chuỗi ghép "lĩnh vực / vị trí" (nội bộ) — "_sub_display" mới là
    # TÊN VỊ TRÍ sạch (vd "Lập trình viên Backend") để dùng trong email gửi nhà tuyển dụng.
    return generate_application_email(
        occupation_display=occupation.get("_sub_display") or occupation["_display"],
        occupation_profile=occupation,
        scores=scores,
        candidate_profile=profile,
        skill_gap=skill_gap,
        cv_review=cv_review,
    )
