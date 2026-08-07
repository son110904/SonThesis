"""
db.py – Kết nối & khởi tạo schema SQLite.

Dùng sqlite3 chuẩn thư viện (không thêm dependency). Mỗi kết nối bật
row_factory=Row để truy cập cột theo tên.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from src.config import DB_PATH

logger = logging.getLogger(__name__)

# ── Schema ──────────────────────────────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name      TEXT NOT NULL,
    email          TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Authentication: mỗi user lưu ĐÚNG 1 CV (UNIQUE user_id) — upload CV mới sẽ
-- ghi đè (ON CONFLICT DO UPDATE trong repository.save_user_cv), KHÔNG giữ lịch
-- sử nhiều CV. Chỉ lưu file gốc; candidate_profile/embedding tính lại mỗi lần
-- phân tích (không cache) để giữ pipeline hiện có không đổi.
CREATE TABLE IF NOT EXISTS user_cv (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL UNIQUE,
    original_filename   TEXT NOT NULL,
    file_path           TEXT NOT NULL,
    uploaded_at         TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS occupations (
    key               TEXT PRIMARY KEY,
    display           TEXT NOT NULL,
    core_skill_count  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS evaluation_history (
    id                         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at                 TEXT NOT NULL DEFAULT (datetime('now')),
    user_id                    INTEGER,
    cv_filename                TEXT,
    occupation_key             TEXT,
    occupation_display         TEXT,
    -- match_score: giữ cột cho backward-compat (dữ liệu lịch sử). Từ 2026-08 hệ
    -- thống đã BỎ match_score tổng hợp; INSERT mới sẽ ghi NULL ở cột này.
    match_score                REAL,
    semantic_similarity_score  REAL,
    weighted_skill_score       REAL,
    matched_skills             TEXT,   -- JSON array
    missing_skills             TEXT,   -- JSON array
    candidate_profile          TEXT,   -- JSON object
    ai_recommendation          TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (occupation_key) REFERENCES occupations(key)
);

CREATE INDEX IF NOT EXISTS idx_eval_created   ON evaluation_history(created_at);
CREATE INDEX IF NOT EXISTS idx_eval_occupation ON evaluation_history(occupation_key);
"""


# App có 2 entrypoint riêng process (FastAPI, Streamlit EMBEDDED) nên không có
# 1 chỗ "startup" chung để gọi init_db() — tự khởi tạo schema (idempotent, CREATE
# TABLE IF NOT EXISTS) ở lần mở kết nối ĐẦU TIÊN của mỗi process thay vì bắt các
# entrypoint tự nhớ gọi.
_initialized = False


def get_connection() -> sqlite3.Connection:
    """Mở kết nối SQLite mới (row_factory=Row, foreign_keys ON)."""
    global _initialized
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    if not _initialized:
        conn.executescript(_SCHEMA)
        conn.commit()
        _initialized = True
    return conn


@contextmanager
def connection_scope() -> Iterator[sqlite3.Connection]:
    """Context manager: tự commit khi thành công, rollback khi lỗi, luôn đóng."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Tạo các bảng nếu chưa có."""
    with connection_scope() as conn:
        conn.executescript(_SCHEMA)
    logger.info(f"SQLite khởi tạo tại: {DB_PATH}")
