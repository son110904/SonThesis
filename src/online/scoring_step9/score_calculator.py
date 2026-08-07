"""
score_calculator.py – Đóng gói 2 điểm số độc lập (Bước 9).

    LƯU Ý (2026-08): Hệ thống đã BỎ match_score tổng hợp.
    Trước đây:
        match_score = MATCH_ALPHA * semantic_similarity_score
                    + MATCH_BETA  * weighted_skill_score

    Bây giờ:
        - Top-3 occupation: sort theo weighted_skill_score thuần.
        - UI hiển thị 2 chỉ số độc lập (semantic + weighted).
        - LLM không bị ép theo công thức tổng → tự cân nhắc theo context.

Hàm `compute_final_score` giữ tên để không phải sửa nhiều call sites,
giờ chỉ wrap 2 chỉ số vào ScoreBreakdown (không tính tổng).
"""

from __future__ import annotations

import logging

from src.models import ScoreBreakdown

logger = logging.getLogger(__name__)


def compute_final_score(
    semantic_similarity_score: float,
    weighted_skill_score: float,
) -> ScoreBreakdown:
    """
    Đóng gói 2 điểm số độc lập (Bước 9).

    Args:
        semantic_similarity_score: ∈ [0, 1].
        weighted_skill_score:      ∈ [0, 1].

    Returns:
        ScoreBreakdown chứa 2 chỉ số (không còn match_score tổng).
    """
    semantic = max(0.0, min(1.0, semantic_similarity_score))
    weighted = max(0.0, min(1.0, weighted_skill_score))

    logger.info(
        f"score_breakdown: semantic={semantic:.4f}, weighted={weighted:.4f} "
        "(đã bỏ match_score tổng hợp — Top-3 sort theo weighted thuần)"
    )
    return ScoreBreakdown(
        semantic_similarity_score=round(semantic, 4),
        weighted_skill_score=round(weighted, 4),
    )
