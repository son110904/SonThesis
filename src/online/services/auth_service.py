"""
auth_service.py – Đăng ký / đăng nhập + lưu & tái sử dụng CV theo tài khoản.

Authentication ở đây CHỈ hỗ trợ trải nghiệm: lưu 1 CV/tài khoản để người dùng
không phải upload lại ở mỗi lần phân tích. KHÔNG lưu candidate_profile/embedding
— mỗi lần phân tích vẫn chạy lại toàn bộ pipeline trích xuất (Bước 2-5) từ file
đã lưu, tái dùng nguyên vẹn analyze_cv()/compare_cv_with_jd() đã có.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from src.config import USER_CV_DIR
from src.database import repository
from src.database.repository import EmailAlreadyExistsError
from src.database.security import hash_password, verify_password
from src.models import AnalysisResult
from src.online.services.analysis_service import analyze_cv
from src.online.services.jd_comparison_service import compare_cv_with_jd

logger = logging.getLogger(__name__)


# Regex email: bắt buộc có phần tên trước @, tên miền, và đuôi ≥2 chữ cái.
# Trước đây chỉ kiểm tra `"@" in email` nên các chuỗi thiếu phần tên như
# "@gmail.com" hay thiếu đuôi như "a@gmail" vẫn đăng ký được.
_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$"
)


class InvalidCredentialsError(ValueError):
    """Raise khi email không tồn tại hoặc mật khẩu sai."""


def _validate_email(email: str) -> str:
    """Chuẩn hóa + kiểm tra định dạng email. Raise ValueError nếu sai."""
    email = email.strip().lower()
    if not email:
        raise ValueError("Vui lòng nhập email.")
    if len(email) > 254 or not _EMAIL_RE.match(email):
        raise ValueError("Email không hợp lệ. Ví dụ đúng: ten.ban@gmail.com")
    return email


class NoSavedCVError(ValueError):
    """Raise khi user chưa upload CV nào."""


def _public_user(user_row: dict) -> dict:
    """Bỏ password_hash trước khi trả ra ngoài (API/frontend)."""
    return {
        "id": user_row["id"],
        "full_name": user_row["full_name"],
        "email": user_row["email"],
    }


def register_user(full_name: str, email: str, password: str) -> dict:
    """
    Đăng ký tài khoản mới.

    Raises:
        ValueError: thiếu thông tin hoặc mật khẩu quá ngắn.
        EmailAlreadyExistsError: email đã tồn tại.
    """
    full_name = full_name.strip()
    if not full_name:
        raise ValueError("Vui lòng nhập họ và tên.")
    email = _validate_email(email)
    if len(password) < 6:
        raise ValueError("Mật khẩu cần ít nhất 6 ký tự.")

    user_id = repository.create_user(full_name, email, hash_password(password))
    logger.info(f"Đăng ký thành công: user #{user_id} ({email})")
    return {"id": user_id, "full_name": full_name, "email": email}


def login_user(email: str, password: str) -> dict:
    """
    Đăng nhập bằng email + mật khẩu.

    Raises:
        InvalidCredentialsError: email không tồn tại hoặc sai mật khẩu.
    """
    email = email.strip().lower()
    user = repository.get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        raise InvalidCredentialsError("Email hoặc mật khẩu không đúng.")
    logger.info(f"Đăng nhập: user #{user['id']} ({email})")
    return _public_user(user)


def save_cv_for_user(user_id: int, file_bytes: bytes, filename: str) -> dict:
    """
    Lưu CV cho user (ghi đè CV cũ nếu có).

    Returns:
        {"original_filename", "uploaded_at"}
    """
    USER_CV_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix.lower() or ".pdf"

    # Dọn mọi file cũ của user (đề phòng đổi định dạng, vd .pdf -> .docx)
    # trước khi ghi file mới — tránh để rác đuôi cũ trên đĩa.
    for old in USER_CV_DIR.glob(f"{user_id}.*"):
        old.unlink(missing_ok=True)

    dest = USER_CV_DIR / f"{user_id}{ext}"
    dest.write_bytes(file_bytes)

    repository.save_user_cv(user_id, filename, str(dest))
    logger.info(f"Đã lưu CV cho user #{user_id}: {filename} -> {dest}")
    return get_cv_info_for_user(user_id)


def get_cv_info_for_user(user_id: int) -> Optional[dict]:
    """Thông tin CV đã lưu của user (None nếu chưa upload) — không đọc bytes."""
    cv = repository.get_user_cv(user_id)
    if not cv:
        return None
    return {"original_filename": cv["original_filename"], "uploaded_at": cv["uploaded_at"]}


def _load_saved_cv_bytes(user_id: int) -> tuple[bytes, str]:
    cv = repository.get_user_cv(user_id)
    if not cv:
        raise NoSavedCVError("Bạn chưa upload CV nào. Vui lòng tải CV lên trước.")
    path = Path(cv["file_path"])
    if not path.exists():
        raise NoSavedCVError("Không tìm thấy file CV đã lưu. Vui lòng tải CV lên lại.")
    return path.read_bytes(), cv["original_filename"]


def analyze_cv_for_saved_user(
    user_id: int,
    occupation_key: str,
    include_recommendation: bool = True,
) -> AnalysisResult:
    """Phân tích CV đã lưu của user với 1 nghề — tái dùng analyze_cv() nguyên vẹn."""
    file_bytes, filename = _load_saved_cv_bytes(user_id)
    return analyze_cv(
        file_bytes=file_bytes,
        filename=filename,
        occupation_key=occupation_key,
        include_recommendation=include_recommendation,
    )


def compare_saved_cv_with_jd(
    user_id: int,
    jd_file_bytes: Optional[bytes] = None,
    jd_filename: str = "",
    jd_text: Optional[str] = None,
) -> dict:
    """
    So sánh CV đã lưu của user với 1 JD — tái dùng compare_cv_with_jd() nguyên vẹn.

    JD nhận qua file (`jd_file_bytes`) hoặc văn bản dán trực tiếp (`jd_text`).
    """
    cv_file_bytes, cv_filename = _load_saved_cv_bytes(user_id)
    return compare_cv_with_jd(
        cv_file_bytes=cv_file_bytes,
        cv_filename=cv_filename,
        jd_file_bytes=jd_file_bytes,
        jd_filename=jd_filename,
        jd_text=jd_text,
    )
