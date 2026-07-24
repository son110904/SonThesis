"""
cv_improvement_service.py – Điều phối AI CV Improvement.

Tái dùng candidate profile + scores + skill gap ĐÃ TÍNH ở bước AI CV Review (Bước
11) — KHÔNG re-extract / re-embed / gọi lại LLM trích profile. Chỉ tốn 1 lần LLM
cho AI CV Improvement.
"""

from __future__ import annotations

import logging
from typing import Optional

from src.config import MATCH_ALPHA, MATCH_BETA
from src.models import CandidateProfile, ScoreBreakdown, SkillGap
from src.online.cv_improvement import generate_cv_improvement
from src.online.services.occupation_loader import get_occupation

logger = logging.getLogger(__name__)


def generate_cv_improvement_for_occupation(
    candidate_profile: dict,
    occupation_key: str,
    match_score: float,
    semantic_similarity_score: float,
    weighted_skill_score: float,
    matched_skills: list[str],
    missing_skills: list[str],
) -> Optional[dict]:
    """
    Sinh AI CV Improvement cho nghề đã chọn, dùng lại profile + điểm số đã tính.

    Args:
        candidate_profile: dict (skills/experience/projects/education/raw_text) —
            từ AnalysisResult.to_dict()["candidate_profile"] của bước AI CV Review.
        occupation_key:    nghề người dùng đang xem.
        match_score, semantic_similarity_score, weighted_skill_score: đã tính sẵn.
        matched_skills, missing_skills: đã tính sẵn (skill gap).

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
    # TÊN VỊ TRÍ sạch (vd "Lập trình viên Backend") để đưa vào nội dung cho LLM.
    return generate_cv_improvement(
        occupation_display=occupation.get("_sub_display") or occupation["_display"],
        occupation_profile=occupation,
        scores=scores,
        candidate_profile=profile,
        skill_gap=skill_gap,
    )
