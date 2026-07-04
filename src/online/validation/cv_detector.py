"""
cv_detector.py – Xác minh tài liệu tải lên có phải CV/Resume không.

Sau khi trích text (Bước 2), trước khi dựng Candidate Profile. Nếu tài liệu KHÔNG
phải CV (báo cáo, hợp đồng, hóa đơn, giáo trình…) → raise NotACVError, hệ thống dừng.

Chiến lược: LLM (GPT-4o) là quyết định cuối khi có API key; thiếu key → heuristic
từ khóa/section. Cả hai degrade graceful, không làm vỡ pipeline.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# ── Tín hiệu heuristic ──────────────────────────────────────────────────────
# Nhóm "section" điển hình của CV (song ngữ). Mỗi nhóm khớp → +1 điểm.
_SECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(kinh nghiệm|experience|work history|employment)\b", re.IGNORECASE),
    re.compile(r"\b(học vấn|education|trình độ học vấn|academic)\b", re.IGNORECASE),
    re.compile(r"\b(kỹ năng|skills|kĩ năng|competenc)\b", re.IGNORECASE),
    re.compile(r"\b(dự án|projects?|portfolio)\b", re.IGNORECASE),
    re.compile(r"\b(mục tiêu nghề nghiệp|career objective|summary|giới thiệu bản thân)\b", re.IGNORECASE),
    re.compile(r"\b(chứng chỉ|certificat|giải thưởng|award)\b", re.IGNORECASE),
]
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?:(?:\+?84)|0)\d{8,10}\b")
_YEAR = re.compile(r"\b(19|20)\d{2}\b")


def _heuristic_is_cv(text: str) -> tuple[bool, str]:
    section_hits = sum(1 for p in _SECTION_PATTERNS if p.search(text))
    has_contact = bool(_EMAIL.search(text) or _PHONE.search(text))
    has_year = bool(_YEAR.search(text))

    score = section_hits + (1 if has_contact else 0) + (1 if has_year else 0)
    is_cv = section_hits >= 1 and score >= 2
    reason = (
        f"heuristic: {section_hits} section, "
        f"contact={has_contact}, year={has_year}, score={score}"
    )
    return is_cv, reason


_LLM_SYSTEM = (
    "Bạn là bộ phân loại tài liệu. Xác định văn bản có phải CV/Resume xin việc của "
    "một CÁ NHÂN hay không (khác với báo cáo, hợp đồng, hóa đơn, giáo trình, bài báo, "
    "mô tả công việc của nhà tuyển dụng). Trả về JSON đúng schema, không giải thích thêm."
)
_LLM_USER = (
    'Trả về JSON: {{"is_cv": true/false, "reason": "ngắn gọn"}}.\n\n'
    "Văn bản (đầu tài liệu):\n\"\"\"\n{snippet}\n\"\"\""
)


def _llm_is_cv(text: str) -> tuple[bool, str] | None:
    """Phân loại bằng LLM. None nếu LLM không khả dụng hoặc lỗi → caller fallback."""
    try:
        from src.online.recommendation_step11.llm_client import get_llm_client
        client = get_llm_client()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"cv_detector: không lấy được LLM client ({e})")
        return None

    if not client.is_available():
        return None

    data = client.chat_json(
        _LLM_SYSTEM,
        _LLM_USER.format(snippet=text[:3000]),
        temperature=0.0,
        max_tokens=120,
    )
    if not data or "is_cv" not in data:
        return None
    return bool(data.get("is_cv")), f"llm: {data.get('reason', '')}"


def is_cv(text: str) -> tuple[bool, str]:
    """
    Kiểm tra text có phải CV không.

    Returns:
        (is_cv, reason). LLM quyết định khi khả dụng; ngược lại dùng heuristic.
    """
    if not text or len(text.strip()) < 40:
        return False, "văn bản quá ngắn / rỗng"

    llm_result = _llm_is_cv(text)
    if llm_result is not None:
        logger.info(f"cv_detector ({'CV' if llm_result[0] else 'NOT CV'}): {llm_result[1]}")
        return llm_result

    result = _heuristic_is_cv(text)
    logger.info(f"cv_detector ({'CV' if result[0] else 'NOT CV'}): {result[1]}")
    return result


class NotACVError(ValueError):
    """Xuất hiện khi tài liệu tải lên không phải CV/Resume."""
