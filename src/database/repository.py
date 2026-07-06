"""
repository.py – Thao tác đọc/ghi dữ liệu (occupations, evaluation history).
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from src.database.db import connection_scope
from src.models import AnalysisResult

logger = logging.getLogger(__name__)


def seed_occupations(occupations: list[dict]) -> None:
    """
    Nạp/đồng bộ danh sách nghề vào bảng occupations.

    Args:
        occupations: List[{"key","display","core_skill_count"}] (từ list_occupations).
    """
    with connection_scope() as conn:
        conn.executemany(
            """
            INSERT INTO occupations (key, display, core_skill_count)
            VALUES (:key, :display, :core_skill_count)
            ON CONFLICT(key) DO UPDATE SET
                display = excluded.display,
                core_skill_count = excluded.core_skill_count
            """,
            occupations,
        )
    logger.info(f"Seed {len(occupations)} occupations vào DB.")


def save_evaluation(
    cv_filename: str,
    result: AnalysisResult,
    user_id: Optional[int] = None,
) -> int:
    """
    Lưu 1 lần đánh giá vào evaluation_history.

    Returns:
        id của bản ghi vừa tạo.
    """
    with connection_scope() as conn:
        cur = conn.execute(
            """
            INSERT INTO evaluation_history (
                user_id, cv_filename, occupation_key, occupation_display,
                match_score, semantic_similarity_score, weighted_skill_score,
                matched_skills, missing_skills, candidate_profile, ai_recommendation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                cv_filename,
                result.occupation_key,
                result.occupation_display,
                result.scores.match_score,
                result.scores.semantic_similarity_score,
                result.scores.weighted_skill_score,
                json.dumps(result.skill_gap.matched_skills, ensure_ascii=False),
                json.dumps(result.skill_gap.missing_skills, ensure_ascii=False),
                json.dumps(result.candidate_profile.to_dict(), ensure_ascii=False),
                result.ai_recommendation,
            ),
        )
        eval_id = cur.lastrowid
    logger.info(f"Lưu evaluation #{eval_id} ({result.occupation_key}).")
    return eval_id


def _row_to_dict(row) -> dict:
    """Chuyển sqlite Row → dict, parse các cột JSON."""
    d = dict(row)
    for col in ("matched_skills", "missing_skills", "candidate_profile"):
        if d.get(col):
            try:
                d[col] = json.loads(d[col])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


def list_evaluations(limit: int = 50, occupation_key: Optional[str] = None) -> list[dict]:
    """
    Liệt kê lịch sử đánh giá, mới nhất trước.

    Args:
        limit:          Số bản ghi tối đa.
        occupation_key: Lọc theo nghề (None = tất cả).
    """
    query = "SELECT * FROM evaluation_history"
    params: list = []
    if occupation_key:
        query += " WHERE occupation_key = ?"
        params.append(occupation_key)
    query += " ORDER BY created_at DESC, id DESC LIMIT ?"
    params.append(limit)

    with connection_scope() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_evaluation(eval_id: int) -> Optional[dict]:
    """Lấy 1 bản ghi đánh giá theo id (None nếu không có)."""
    with connection_scope() as conn:
        row = conn.execute(
            "SELECT * FROM evaluation_history WHERE id = ?", (eval_id,)
        ).fetchone()
    return _row_to_dict(row) if row else None
