"""
repository.py – Thao tác đọc/ghi dữ liệu (occupations, evaluation history).
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from typing import Optional

from src.config import VIETNAM_TZ
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
                """
                INSERT INTO users (full_name, email, password_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    full_name,
                    email,
                    password_hash,
                    datetime.now(VIETNAM_TZ).strftime("%Y-%m-%d %H:%M:%S"),
                ),
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


def save_user_cv(
    user_id: int, original_filename: str, file_path: str, file_hash: Optional[str] = None
) -> None:
    """
    Ghi nhận một lần upload CV và đặt nó làm CV đang dùng.

    Mỗi lần gọi tạo MỘT bản ghi mới (không ghi đè) để giữ lịch sử.
    """
    with connection_scope() as conn:
        conn.execute("UPDATE user_cv SET is_active = 0 WHERE user_id = ?", (user_id,))
        conn.execute(
            """
            INSERT INTO user_cv (
                user_id, original_filename, file_path, file_hash, uploaded_at, is_active
            ) VALUES (?, ?, ?, ?, ?, 1)
            """,
            (
                user_id,
                original_filename,
                file_path,
                file_hash,
                datetime.now(VIETNAM_TZ).strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
    logger.info(f"Lưu CV cho user #{user_id}: {original_filename}")


def find_user_cv_by_hash(user_id: int, file_hash: str) -> Optional[dict]:
    """Tìm CV đã lưu của user có cùng nội dung (theo hash) — dùng để chống trùng."""
    with connection_scope() as conn:
        row = conn.execute(
            """
            SELECT * FROM user_cv WHERE user_id = ? AND file_hash = ?
            ORDER BY uploaded_at DESC, id DESC LIMIT 1
            """,
            (user_id, file_hash),
        ).fetchone()
    return dict(row) if row else None


def delete_user_cv(user_id: int, cv_id: int) -> Optional[dict]:
    """
    Xóa 1 bản ghi CV khỏi lịch sử, RÀNG BUỘC đúng chủ sở hữu.

    Không tự xóa nếu đây là CV đang dùng (is_active=1) — caller (service layer)
    phải kiểm tra và chặn trước khi gọi hàm này, để tránh tài khoản rơi vào
    trạng thái không có CV nào đang dùng một cách ngoài ý muốn.

    Returns:
        dict bản ghi vừa xóa (để caller xóa file vật lý tương ứng), hoặc None
        nếu cv_id không thuộc user này.
    """
    with connection_scope() as conn:
        row = conn.execute(
            "SELECT * FROM user_cv WHERE id = ? AND user_id = ?", (cv_id, user_id)
        ).fetchone()
        if not row:
            return None
        conn.execute("DELETE FROM user_cv WHERE id = ?", (cv_id,))
    logger.info(f"Xóa CV #{cv_id} của user #{user_id}")
    return dict(row)


def get_user_cv(user_id: int) -> Optional[dict]:
    """
    CV ĐANG DÙNG của user (None nếu chưa upload lần nào).

    Ưu tiên bản có is_active = 1; nếu chưa bản nào được đánh dấu (dữ liệu tạo
    trước khi có cột này) thì lùi về bản mới nhất — giữ nguyên hành vi cũ.
    """
    with connection_scope() as conn:
        row = conn.execute(
            "SELECT * FROM user_cv WHERE user_id = ? AND is_active = 1 LIMIT 1",
            (user_id,),
        ).fetchone()
        if row is None:
            row = conn.execute(
                """
                SELECT * FROM user_cv WHERE user_id = ?
                ORDER BY uploaded_at DESC, id DESC LIMIT 1
                """,
                (user_id,),
            ).fetchone()
    return dict(row) if row else None


def get_user_cv_by_id(user_id: int, cv_id: int) -> Optional[dict]:
    """
    Lấy 1 bản ghi CV theo id, RÀNG BUỘC đúng chủ sở hữu.

    Luôn lọc kèm user_id để không cho đọc CV của tài khoản khác chỉ bằng cách
    đoán id — mọi endpoint tải file đều phải đi qua hàm này.
    """
    with connection_scope() as conn:
        row = conn.execute(
            "SELECT * FROM user_cv WHERE id = ? AND user_id = ?", (cv_id, user_id)
        ).fetchone()
    return dict(row) if row else None


def set_active_user_cv(user_id: int, cv_id: int) -> bool:
    """
    Đặt một CV trong lịch sử làm CV đang dùng.

    Returns:
        True nếu đổi được; False nếu cv_id không thuộc user này.
    """
    with connection_scope() as conn:
        owned = conn.execute(
            "SELECT 1 FROM user_cv WHERE id = ? AND user_id = ?", (cv_id, user_id)
        ).fetchone()
        if not owned:
            return False
        conn.execute("UPDATE user_cv SET is_active = 0 WHERE user_id = ?", (user_id,))
        conn.execute("UPDATE user_cv SET is_active = 1 WHERE id = ?", (cv_id,))
    logger.info(f"User #{user_id} chuyển sang dùng CV #{cv_id}")
    return True


def list_user_cvs(user_id: int, limit: int = 50) -> list[dict]:
    """Lịch sử CV đã tải của user, mới nhất trước."""
    with connection_scope() as conn:
        rows = conn.execute(
            """
            SELECT * FROM user_cv WHERE user_id = ?
            ORDER BY uploaded_at DESC, id DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


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
                matched_skills, missing_skills, candidate_profile, ai_recommendation,
                created_at
            ) VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)
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
                datetime.now(VIETNAM_TZ).strftime("%Y-%m-%d %H:%M:%S"),
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
