"""
resp_summarizer.py – Tóm tắt danh sách responsibilities thô thành list gọn bằng LLM.

Chỉ dùng trong Offline Pipeline (Step 3). Mỗi nghề gọi 1 lần → tổng ~16 API calls.
Graceful degradation: nếu không có OPENAI_API_KEY → trả None, caller dùng raw list.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Bạn là chuyên gia nhân sự. Nhiệm vụ: tổng hợp danh sách mô tả công việc thô "
    "từ nhiều job description của cùng một nghề, trả về danh sách ngắn gọn, không trùng lặp.\n\n"
    "Yêu cầu:\n"
    "- Chỉ giữ nhiệm vụ CỐT LÕI, đặc trưng cho nghề; loại bỏ mục trùng ý\n"
    "- Mỗi mục 1 câu ngắn, rõ ràng, bắt đầu bằng động từ (Phát triển, Thiết kế, Quản lý…)\n"
    "- Trả về JSON: {\"responsibilities\": [\"...\", \"...\"]}\n"
    "- Số lượng: 10–15 mục\n"
    "- Giữ nguyên ngôn ngữ chính của nguồn (tiếng Việt ưu tiên)"
)


def summarize_responsibilities(
    occupation: str,
    raw_responsibilities: list[str],
    max_items: int = 15,
) -> Optional[list[str]]:
    """
    Dùng LLM tóm tắt pool responsibilities thô → list sạch, không trùng.

    Args:
        occupation:           Tên nghề (để LLM có context).
        raw_responsibilities: Danh sách thô từ regex extraction (có thể lên đến 50+).
        max_items:            Số mục tối đa trả về.

    Returns:
        List responsibilities đã tóm tắt, hoặc None nếu LLM không khả dụng.
        Caller nên fallback về raw list khi nhận None.
    """
    if not raw_responsibilities:
        return []

    try:
        from src.online.recommendation_step11.llm_client import get_llm_client
        client = get_llm_client()
    except Exception as e:
        logger.warning(f"Không lấy được LLM client: {e}")
        return None

    if not client.is_available():
        return None

    # Giới hạn input để tránh vượt context window (~4K token)
    sample = raw_responsibilities[:60]
    bullet_list = "\n".join(f"- {r}" for r in sample)

    user_prompt = (
        f"Nghề: {occupation}\n\n"
        f"Danh sách responsibilities thô ({len(sample)} mục):\n{bullet_list}\n\n"
        f"Tóm tắt thành {max_items} responsibilities cốt lõi, không trùng lặp."
    )

    result = client.chat_json(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.0,
        max_tokens=1000,
    )

    if not result:
        logger.warning(f"[{occupation}] LLM trả rỗng, fallback raw list.")
        return None

    items = result.get("responsibilities", [])
    if not isinstance(items, list):
        return None

    cleaned = [str(r).strip() for r in items if r and len(str(r).strip()) >= 10]
    logger.info(
        f"[{occupation}] LLM tóm tắt responsibilities: "
        f"{len(raw_responsibilities)} thô → {len(cleaned)} gọn"
    )
    return cleaned[:max_items]
