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
    created_at     TEXT NOT NULL DEFAULT (datetime('now', '+7 hours'))
);

-- Authentication: mỗi lần upload CV tạo MỘT bản ghi mới (không còn UNIQUE
-- user_id như bản đầu) để giữ được lịch sử CV đã tải.
-- "CV đang dùng" = bản ghi có is_active = 1; người dùng chọn lại CV cũ trong
-- lịch sử thì chỉ đổi cờ này, KHÔNG tạo bản ghi mới (giữ đúng mốc tải lên gốc).
-- Với dữ liệu cũ chưa có bản nào is_active, get_user_cv() lùi về bản mới nhất.
-- Chỉ lưu file gốc; candidate_profile/embedding tính lại mỗi lần phân tích
-- (không cache) để giữ pipeline hiện có không đổi.
CREATE TABLE IF NOT EXISTS user_cv (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL,
    original_filename   TEXT NOT NULL,
    file_path           TEXT NOT NULL,
    file_hash           TEXT,   -- SHA-256 nội dung file, để phát hiện trùng lặp
    uploaded_at         TEXT NOT NULL DEFAULT (datetime('now', '+7 hours')),
    is_active           INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_user_cv_user ON user_cv(user_id, uploaded_at DESC);
-- KHÔNG tạo index cho file_hash ở đây: trên DB cũ (bảng đã tồn tại từ trước,
-- CREATE TABLE IF NOT EXISTS ở trên thành no-op) cột này chưa có, CREATE INDEX
-- sẽ lỗi "no such column" vì chạy TRƯỚC migration bên dưới. Index được tạo
-- trong _migrate_user_cv_add_file_hash(), luôn chạy SAU khi cột chắc chắn tồn tại.

CREATE TABLE IF NOT EXISTS occupations (
    key               TEXT PRIMARY KEY,
    display           TEXT NOT NULL,
    core_skill_count  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS evaluation_history (
    id                         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at                 TEXT NOT NULL DEFAULT (datetime('now', '+7 hours')),
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


def _migrate_user_cv_drop_unique(conn: sqlite3.Connection) -> None:
    """
    Gỡ ràng buộc UNIQUE(user_id) trên user_cv ở các DB tạo bằng schema bản đầu.

    Bản đầu cho mỗi tài khoản đúng 1 CV nên đặt UNIQUE(user_id); từ khi có tính
    năng "Lịch sử CV đã tải" thì mỗi lần upload là một bản ghi mới. SQLite không
    ALTER bỏ được ràng buộc → phải dựng lại bảng và chép dữ liệu sang.
    Idempotent: chạy lại trên DB đã migrate thì không làm gì.
    """
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='user_cv'"
    ).fetchone()
    if not row or "UNIQUE" not in (row[0] or "").upper():
        return

    logger.info("Migrate user_cv: gỡ UNIQUE(user_id) để giữ lịch sử CV…")
    # Tắt FK trong lúc dựng lại bảng, nếu không thao tác RENAME/DROP có thể vướng
    # ràng buộc tham chiếu. PRAGMA này không có tác dụng bên trong transaction.
    conn.execute("PRAGMA foreign_keys = OFF;")
    conn.executescript(
        """
        ALTER TABLE user_cv RENAME TO _user_cv_old;

        CREATE TABLE user_cv (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id             INTEGER NOT NULL,
            original_filename   TEXT NOT NULL,
            file_path           TEXT NOT NULL,
            uploaded_at         TEXT NOT NULL DEFAULT (datetime('now', '+7 hours')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        INSERT INTO user_cv (id, user_id, original_filename, file_path, uploaded_at)
            SELECT id, user_id, original_filename, file_path, uploaded_at
            FROM _user_cv_old;

        DROP TABLE _user_cv_old;
        CREATE INDEX IF NOT EXISTS idx_user_cv_user ON user_cv(user_id, uploaded_at DESC);
        """
    )
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON;")
    n = conn.execute("SELECT COUNT(*) FROM user_cv").fetchone()[0]
    logger.info(f"Migrate user_cv xong — giữ nguyên {n} bản ghi.")


def _migrate_user_cv_add_is_active(conn: sqlite3.Connection) -> None:
    """
    Thêm cột is_active cho DB tạo trước khi có tính năng "chọn lại CV trong lịch sử".

    Khác với việc gỡ ràng buộc, SQLite ADD COLUMN được nên không cần dựng lại bảng.
    Bản ghi cũ để is_active = 0; get_user_cv() có nhánh lùi về bản mới nhất nên
    hành vi không đổi cho tới khi người dùng chọn CV lần đầu.
    """
    cols = {r[1] for r in conn.execute("PRAGMA table_info(user_cv)")}
    if "is_active" in cols:
        return
    logger.info("Migrate user_cv: thêm cột is_active…")
    conn.execute("ALTER TABLE user_cv ADD COLUMN is_active INTEGER NOT NULL DEFAULT 0")
    # Đánh dấu CV mới nhất của mỗi user là đang dùng — giữ nguyên hành vi cũ
    # (trước đây "CV hiện tại" chính là bản mới nhất).
    conn.execute(
        """
        UPDATE user_cv SET is_active = 1
        WHERE id IN (
            SELECT id FROM user_cv u
            WHERE u.id = (
                SELECT id FROM user_cv x WHERE x.user_id = u.user_id
                ORDER BY x.uploaded_at DESC, x.id DESC LIMIT 1
            )
        )
        """
    )
    conn.commit()


def _migrate_user_cv_add_file_hash(conn: sqlite3.Connection) -> None:
    """
    Thêm cột file_hash cho DB tạo trước khi có tính năng chống trùng CV.

    Bản ghi cũ để NULL — không tính hash hồi tố cho file đã lưu trước đó (không
    cần thiết: chỉ ảnh hưởng việc phát hiện trùng lặp CHO LẦN TẢI LÊN TIẾP THEO,
    không ảnh hưởng tải về hay chọn dùng CV cũ).

    Luôn đảm bảo cả cột lẫn index, kể cả khi cột đã có sẵn (DB mới tạo từ
    _SCHEMA) — vì _SCHEMA cố tình KHÔNG tạo index này (xem comment ở đó).
    """
    cols = {r[1] for r in conn.execute("PRAGMA table_info(user_cv)")}
    if "file_hash" not in cols:
        logger.info("Migrate user_cv: thêm cột file_hash…")
        conn.execute("ALTER TABLE user_cv ADD COLUMN file_hash TEXT")
        conn.commit()
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_cv_hash ON user_cv(user_id, file_hash)")
    conn.commit()


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
        _migrate_user_cv_drop_unique(conn)
        _migrate_user_cv_add_is_active(conn)
        _migrate_user_cv_add_file_hash(conn)
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
