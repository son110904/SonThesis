"""
weighted_matcher.py – Weighted Skill Matching.

Bước 8 của Online Pipeline.

Ý tưởng: mỗi skill trong Occupation Profile có trọng số (core_skills +
optional_skills, weight ∈ [0,1] = mức quan trọng). Điểm = tổng trọng số các
skill mà ứng viên CÓ, chia tổng trọng số toàn bộ skill của nghề.

    weighted_skill_score = Σ weight(skill ứng viên có) / Σ weight(mọi skill nghề)

Kết quả ∈ [0, 1]: 1 = ứng viên có mọi skill quan trọng của nghề.

So khớp "ứng viên CÓ skill nghề" dùng semantic_skill_match (mặc định semantic,
bắt được đồng nghĩa; tự fallback exact nếu không có model). Có thể truyền sẵn
`match_result` đã tính ở nơi khác để tránh embed lại (analysis_service làm vậy).
"""

from __future__ import annotations

import logging
from typing import Optional

from src.online.semantic_skill_match import SkillMatchResult, match_skills

logger = logging.getLogger(__name__)


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
    match_result: Optional[SkillMatchResult] = None,
) -> float:
    """
    Tính weighted_skill_score.

    Args:
        candidate_skills:   Danh sách kỹ năng ứng viên.
        occupation_profile: Occupation Profile (có core_skills, optional_skills).
        match_result:       Kết quả so khớp skill đã tính sẵn (tùy chọn).
                            Nếu None → tự gọi match_skills (theo config mode).

    Returns:
        Điểm ∈ [0, 1]. Trả 0.0 nếu nghề không có skill nào.
    """
    occ_weights = _occupation_skill_weights(occupation_profile)
    if not occ_weights:
        logger.warning("Occupation profile không có skill nào → weighted_skill_score=0")
        return 0.0

    if match_result is None:
        match_result = match_skills(candidate_skills, list(occ_weights.keys()))

    total_weight = sum(occ_weights.values())
    matched_weight = sum(
        occ_weights[skill] for skill in match_result.matched if skill in occ_weights
    )

    score = matched_weight / total_weight if total_weight > 0 else 0.0
    score = max(0.0, min(1.0, score))
    logger.debug(
        f"weighted_skill_score={score:.4f} "
        f"(matched_weight={matched_weight:.2f}/{total_weight:.2f}, "
        f"mode={match_result.mode_used})"
    )
    return score
