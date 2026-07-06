"""
llm_client.py – Wrapper mỏng quanh OpenAI Chat Completions (mặc định GPT-4o).

Dùng chung cho:
    - Trích experience/projects/education (candidate_profile)
    - Sinh AI Recommendation (recommender)

Thiết kế degrade graceful: nếu KHÔNG có OPENAI_API_KEY → is_available()=False,
các hàm gọi trả None. Pipeline lõi (matching/scoring) vẫn chạy bình thường.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from src.config import OPENAI_MODEL, LLM_TIMEOUT_SECONDS, LLM_MAX_RETRIES

logger = logging.getLogger(__name__)


class LLMClient:
    """Client gọi OpenAI Chat Completions, an toàn khi thiếu key."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = OPENAI_MODEL,
        timeout: float = LLM_TIMEOUT_SECONDS,
        max_retries: int = LLM_MAX_RETRIES,
    ) -> None:
        # Đọc key tại runtime (cho phép set OPENAI_API_KEY sau khi import config)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = None

        if self.api_key:
            try:
                from openai import OpenAI

                self._client = OpenAI(
                    api_key=self.api_key,
                    timeout=self.timeout,
                    max_retries=self.max_retries,
                )
                logger.info(f"LLMClient sẵn sàng (model={self.model})")
            except Exception as e:  # noqa: BLE001
                logger.error(f"Không khởi tạo được OpenAI client: {e}")
                self._client = None
        else:
            logger.warning(
                "OPENAI_API_KEY chưa được đặt — các tính năng LLM sẽ bị tắt "
                "(experience/projects/education + AI recommendation trả rỗng)."
            )

    def is_available(self) -> bool:
        """True nếu client gọi LLM được."""
        return self._client is not None

    def chat_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1200,
    ) -> Optional[str]:
        """
        Gọi LLM, trả về text. None nếu không khả dụng hoặc lỗi.
        """
        if not self.is_available():
            return None
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content
        except Exception as e:  # noqa: BLE001
            logger.error(f"Lỗi gọi LLM (chat_text): {e}")
            return None

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1500,
    ) -> Optional[dict]:
        """
        Gọi LLM ở chế độ JSON (response_format=json_object), parse ra dict.
        None nếu không khả dụng hoặc parse lỗi.
        """
        if not self.is_available():
            return None
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or "{}"
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"LLM trả JSON không hợp lệ: {e}")
            return None
        except Exception as e:  # noqa: BLE001
            logger.error(f"Lỗi gọi LLM (chat_json): {e}")
            return None


# ── Singleton tiện dùng ─────────────────────────────────────────────────────
_default_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Lấy LLMClient mặc định (khởi tạo 1 lần)."""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
