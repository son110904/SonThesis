"""
skill_gap_analyzer.py – Skill Gap Analysis (Bước 10).

Thuật toán: Set Difference (case-insensitive).

    matched_skills = skill nghề ∩ skill ứng viên
    missing_skills = skill nghề \\ skill ứng viên   (ưu tiên hiển thị core trước)
    extra_skills   = skill ứng viên \\ skill nghề
"""

from __future__ import annotations

import logging

from src.models import SkillGap

logger = logging.getLogger(__name__)


def _normalize(skill: str) -> str:
    return skill.strip().lower()


def analyze_skill_gap(
    candidate_skills: list[str],
    occupation_profile: dict,
) -> SkillGap:
    """
    So khớp kỹ năng ứng viên với kỹ năng nghề (core + optional).

    Args:
        candidate_skills:   Kỹ năng ứng viên.
        occupation_profile: Occupation Profile (core_skills, optional_skills dict).

    Returns:
        SkillGap(matched_skills, missing_skills, extra_skills).
        missing_skills sắp xếp giảm dần theo trọng số (skill quan trọng thiếu lên đầu).
    """
    core = occupation_profile.get("core_skills", {})
    optional = occupation_profile.get("optional_skills", {})

    # dict[skill gốc -> weight], ưu tiên core khi trùng tên
    occ_weights: dict[str, float] = dict(optional)
    occ_weights.update(core)

    candidate_norm = {_normalize(s): s for s in candidate_skills}

    matched: list[str] = []
    missing: list[tuple[str, float]] = []

    for skill, weight in occ_weights.items():
        if _normalize(skill) in candidate_norm:
            matched.append(skill)
        else:
            missing.append((skill, weight))

    # Skill quan trọng (weight cao) còn thiếu hiển thị trước
    missing.sort(key=lambda x: x[1], reverse=True)
    missing_skills = [s for s, _ in missing]

    occ_norm = {_normalize(s) for s in occ_weights}
    extra_skills = [orig for norm, orig in candidate_norm.items() if norm not in occ_norm]

    logger.info(
        f"Skill gap: matched={len(matched)}, missing={len(missing_skills)}, "
        f"extra={len(extra_skills)}"
    )
    return SkillGap(
        matched_skills=matched,
        missing_skills=missing_skills,
        extra_skills=extra_skills,
    )
