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
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
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
    occupation_key             TEXT NOT NULL,
    occupation_display         TEXT,
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


def get_connection() -> sqlite3.Connection:
    """Mở kết nối SQLite mới (row_factory=Row, foreign_keys ON)."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
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
