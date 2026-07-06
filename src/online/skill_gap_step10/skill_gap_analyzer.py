"""
skill_gap_analyzer.py – Skill Gap Analysis (Bước 10).

    matched_skills = skill nghề mà ứng viên CÓ (khớp tuyệt đối hoặc ngữ nghĩa; core + optional)
    missing_skills = skill nghề thiếu thuộc tầng Core + Important (weight >= 0.15);
                     tầng Supporting (weight < 0.15) bị bỏ để tránh nhiễu
    extra_skills   = skill ứng viên có nhưng nghề không liệt kê

So khớp dùng chung semantic_skill_match (Bước 8): có thể truyền sẵn `match_result`
để khỏi embed lại. Nếu None → tự tính theo config mode.
"""

from __future__ import annotations

import logging
from typing import Optional

from src.config import SKILL_TIER_IMPORTANT
from src.models import SkillGap
from src.online.semantic_skill_match import SkillMatchResult, match_skills
from src.online.semantic_skill_match import _normalize

logger = logging.getLogger(__name__)


def analyze_skill_gap(
    candidate_skills: list[str],
    occupation_profile: dict,
    match_result: Optional[SkillMatchResult] = None,
) -> SkillGap:
    """
    So khớp kỹ năng ứng viên với kỹ năng nghề (core + optional).

    Args:
        candidate_skills:   Kỹ năng ứng viên.
        occupation_profile: Occupation Profile (core_skills, optional_skills dict).
        match_result:       Kết quả so khớp đã tính sẵn (tùy chọn).

    Returns:
        SkillGap(matched_skills, missing_skills, extra_skills).
        missing_skills gồm skill thiếu tầng Core + Important (weight >= 0.15),
        sắp giảm dần theo trọng số (skill cốt lõi quan trọng nhất lên đầu).
    """
    core = occupation_profile.get("core_skills", {})
    optional = occupation_profile.get("optional_skills", {})

    # dict[skill gốc -> weight], ưu tiên core khi trùng tên.
    # So khớp trên TOÀN BỘ skill (core + optional) để matched_skills phản ánh đúng
    # những gì ứng viên có; missing thì lọc theo tầng weight (xem dưới).
    occ_weights: dict[str, float] = dict(optional)
    occ_weights.update(core)

    if match_result is None:
        match_result = match_skills(candidate_skills, list(occ_weights.keys()))

    matched = list(match_result.matched.keys())

    # Skill còn thiếu chỉ xét Core + Important (weight >= SKILL_TIER_IMPORTANT);
    # bỏ tầng Supporting (đuôi-dài, weight ~0) để tránh liệt kê hàng trăm skill nhiễu.
    # Sắp theo weight giảm dần → skill cốt lõi quan trọng nhất lên đầu.
    unmatched_set = set(match_result.unmatched)
    missing = sorted(
        (
            (s, w) for s, w in occ_weights.items()
            if s in unmatched_set and w >= SKILL_TIER_IMPORTANT
        ),
        key=lambda x: x[1],
        reverse=True,
    )
    missing_skills = [s for s, _ in missing]

    # Extra: skill ứng viên KHÔNG được dùng để khớp skill nghề nào.
    used_candidates = {_normalize(c) for c in match_result.matched.values()}
    extra_skills = [c for c in candidate_skills if _normalize(c) not in used_candidates]

    logger.info(
        f"Skill gap (mode={match_result.mode_used}): matched={len(matched)}, "
        f"missing={len(missing_skills)}, extra={len(extra_skills)}"
    )
    return SkillGap(
        matched_skills=matched,
        missing_skills=missing_skills,
        extra_skills=extra_skills,
    )
