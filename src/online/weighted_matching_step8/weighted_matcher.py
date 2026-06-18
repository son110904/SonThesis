"""
weighted_matcher.py – Weighted Skill Matching.

Bước 8 của Online Pipeline.

Ý tưởng: mỗi skill trong Occupation Profile có trọng số (core_skills +
optional_skills, weight ∈ [0,1] = mức quan trọng). Điểm = tổng trọng số các
skill mà ứng viên CÓ, chia tổng trọng số toàn bộ skill của nghề.

    weighted_skill_score = Σ weight(skill ứng viên có) / Σ weight(mọi skill nghề)

Kết quả ∈ [0, 1]: 1 = ứng viên có mọi skill quan trọng của nghề.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _normalize(skill: str) -> str:
    """Chuẩn hóa skill để so khớp (case-insensitive, bỏ khoảng trắng thừa)."""
    return skill.strip().lower()


def _occupation_skill_weights(occupation_profile: dict) -> dict[str, float]:
    """Gộp core_skills + optional_skills thành dict[skill -> weight]."""
    weights: dict[str, float] = {}
    weights.update(occupation_profile.get("core_skills", {}))
    # optional không ghi đè core nếu trùng tên (core quan trọng hơn)
    for skill, w in occupation_profile.get("optional_skills", {}).items():
        weights.setdefault(skill, w)
    return weights


def compute_weighted_skill_score(
    candidate_skills: list[str],
    occupation_profile: dict,
) -> float:
    """
    Tính weighted_skill_score.

    Args:
        candidate_skills:   Danh sách kỹ năng ứng viên.
        occupation_profile: Occupation Profile (có core_skills, optional_skills).

    Returns:
        Điểm ∈ [0, 1]. Trả 0.0 nếu nghề không có skill nào.
    """
    occ_weights = _occupation_skill_weights(occupation_profile)
    if not occ_weights:
        logger.warning("Occupation profile không có skill nào → weighted_skill_score=0")
        return 0.0

    candidate_set = {_normalize(s) for s in candidate_skills}

    total_weight = sum(occ_weights.values())
    matched_weight = sum(
        w for skill, w in occ_weights.items() if _normalize(skill) in candidate_set
    )

    score = matched_weight / total_weight if total_weight > 0 else 0.0
    score = max(0.0, min(1.0, score))
    logger.debug(
        f"weighted_skill_score={score:.4f} "
        f"(matched_weight={matched_weight:.2f}/{total_weight:.2f})"
    )
    return score
