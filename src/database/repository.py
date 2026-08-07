"""
repository.py – Thao tác đọc/ghi dữ liệu (occupations, evaluation history).
"""

from __future__ import annotations

import json
import logging
import sqlite3
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


class EmailAlreadyExistsError(ValueError):
    """Raise khi đăng ký với email đã tồn tại."""


def create_user(full_name: str, email: str, password_hash: str) -> int:
    """
    Tạo user mới.

    Returns:
        id của user vừa tạo.

    Raises:
        EmailAlreadyExistsError: email đã được dùng.
    """
    try:
        with connection_scope() as conn:
            cur = conn.execute(
                "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
                (full_name, email, password_hash),
            )
            user_id = cur.lastrowid
    except sqlite3.IntegrityError as e:
        raise EmailAlreadyExistsError(f"Email đã được đăng ký: {email}") from e
    logger.info(f"Tạo user #{user_id} ({email}).")
    return user_id


def get_user_by_email(email: str) -> Optional[dict]:
    """Tra cứu user theo email (None nếu không có)."""
    with connection_scope() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
    return dict(row) if row else None


def save_user_cv(user_id: int, original_filename: str, file_path: str) -> None:
    """Lưu/ghi đè CV của user (mỗi user chỉ giữ đúng 1 CV — UNIQUE user_id)."""
    with connection_scope() as conn:
        conn.execute(
            """
            INSERT INTO user_cv (user_id, original_filename, file_path)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                original_filename = excluded.original_filename,
                file_path = excluded.file_path,
                uploaded_at = datetime('now')
            """,
            (user_id, original_filename, file_path),
        )
    logger.info(f"Lưu CV cho user #{user_id}: {original_filename}")


def get_user_cv(user_id: int) -> Optional[dict]:
    """Lấy thông tin CV đã lưu của user (None nếu chưa upload)."""
    with connection_scope() as conn:
        row = conn.execute(
            "SELECT * FROM user_cv WHERE user_id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def save_evaluation(
    cv_filename: str,
    result: AnalysisResult,
    user_id: Optional[int] = None,
) -> int:
    """
    Lưu 1 lần đánh giá vào evaluation_history.

    Lưu ý (2026-08): match_score đã BỎ khỏi ScoreBreakdown → cột match_score
    trong DB sẽ ghi NULL (giữ schema cho backward-compat với dữ liệu lịch sử).

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
            ) VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                cv_filename,
                result.occupation_key,
                result.occupation_display,
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
