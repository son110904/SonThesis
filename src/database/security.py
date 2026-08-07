"""
security.py – Hash & verify mật khẩu (PBKDF2-HMAC-SHA256, chỉ dùng stdlib).

Chọn PBKDF2 qua hashlib thay vì bcrypt/argon2 để tránh thêm C-extension
dependency (rủi ro cài đặt trên Windows) — phù hợp yêu cầu "hash mật khẩu cơ
bản", không cần các cơ chế bảo mật nâng cao (OTP, refresh token, phân quyền...).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

_ALGORITHM = "sha256"
_ITERATIONS = 260_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Hash mật khẩu, trả về chuỗi "<salt_hex>$<digest_hex>" để lưu vào DB."""
    salt = secrets.token_hex(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        _ALGORITHM, password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS
    )
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """So khớp mật khẩu với hash đã lưu (timing-safe qua hmac.compare_digest)."""
    try:
        salt, digest_hex = stored_hash.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac(
        _ALGORITHM, password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS
    )
    return hmac.compare_digest(digest.hex(), digest_hex)
