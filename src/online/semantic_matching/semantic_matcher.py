"""
semantic_matcher.py – Semantic Matching bằng Cosine Similarity.

Bước 7 của Online Pipeline.

Input:  candidate_embedding, occupation_embedding (đều đã L2-normalized)
Output: semantic_similarity_score ∈ [0, 1]
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


def _cosine(v1: np.ndarray, v2: np.ndarray) -> float:
    """Cosine similarity. An toàn khi vector chưa normalize."""
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    return float(np.dot(v1, v2) / (n1 * n2))


def compute_semantic_score(
    candidate_embedding: list[float],
    occupation_embedding: list[float],
) -> float:
    """
    Tính semantic similarity score.

    Cosine ∈ [-1, 1] được clamp về [0, 1] (giá trị âm = không liên quan → 0)
    để kết hợp với weighted_skill_score trong Final Score.

    Args:
        candidate_embedding:  Vector ứng viên.
        occupation_embedding: Vector nghề nghiệp.

    Returns:
        Điểm ∈ [0, 1].
    """
    v1 = np.asarray(candidate_embedding, dtype=np.float32)
    v2 = np.asarray(occupation_embedding, dtype=np.float32)
    cos = _cosine(v1, v2)
    score = max(0.0, min(1.0, cos))
    logger.debug(f"cosine={cos:.4f} → semantic_score={score:.4f}")
    return score
