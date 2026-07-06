"""
score_calculator.py – Tính Final Score (Bước 9).

    match_score = MATCH_ALPHA * semantic_similarity_score
                + MATCH_BETA  * weighted_skill_score

Tất cả điểm ∈ [0, 1].
"""

from __future__ import annotations

import logging

from src.config import MATCH_ALPHA, MATCH_BETA
from src.models import ScoreBreakdown

logger = logging.getLogger(__name__)


def compute_final_score(
    semantic_similarity_score: float,
    weighted_skill_score: float,
    alpha: float = MATCH_ALPHA,
    beta: float = MATCH_BETA,
) -> ScoreBreakdown:
    """
    Kết hợp semantic + weighted skill thành match_score.

    Args:
        semantic_similarity_score: ∈ [0, 1].
        weighted_skill_score:      ∈ [0, 1].
        alpha:                     Trọng số semantic (default MATCH_ALPHA).
        beta:                      Trọng số weighted skill (default MATCH_BETA).

    Returns:
        ScoreBreakdown chứa cả 3 điểm + trọng số đã dùng.
    """
    match_score = alpha * semantic_similarity_score + beta * weighted_skill_score
    match_score = max(0.0, min(1.0, match_score))

    logger.info(
        f"match_score={match_score:.4f} "
        f"(semantic={semantic_similarity_score:.4f}*{alpha} + "
        f"weighted={weighted_skill_score:.4f}*{beta})"
    )
    return ScoreBreakdown(
        semantic_similarity_score=round(semantic_similarity_score, 4),
        weighted_skill_score=round(weighted_skill_score, 4),
        match_score=round(match_score, 4),
        alpha=alpha,
        beta=beta,
    )
