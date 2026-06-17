"""
api_client.py – Lớp gọi REST API (FastAPI backend) từ Streamlit.

Base URL đọc từ biến môi trường API_BASE_URL (mặc định http://127.0.0.1:8000).
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
_TIMEOUT = (5, 120)  # (connect, read) — read dài vì /analyze có thể gọi LLM


class APIError(Exception):
    """Lỗi khi gọi backend (kết nối, HTTP 4xx/5xx)."""


def _url(path: str) -> str:
    return f"{API_BASE_URL}{path}"


def _handle_response(resp: requests.Response) -> dict:
    """Parse response, raise APIError với thông điệp thân thiện nếu lỗi."""
    if resp.ok:
        return resp.json()
    # Cố lấy 'detail' từ FastAPI HTTPException
    try:
        detail = resp.json().get("detail", resp.text)
    except Exception:  # noqa: BLE001
        detail = resp.text or f"HTTP {resp.status_code}"
    raise APIError(f"[{resp.status_code}] {detail}")


def health() -> dict:
    """GET /health — trạng thái backend + LLM."""
    try:
        return _handle_response(requests.get(_url("/health"), timeout=_TIMEOUT))
    except requests.RequestException as e:
        raise APIError(f"Không kết nối được backend tại {API_BASE_URL}. ({e})")


def get_occupations() -> list[dict]:
    """GET /occupations — danh sách nghề cho dropdown."""
    try:
        data = _handle_response(requests.get(_url("/occupations"), timeout=_TIMEOUT))
    except requests.RequestException as e:
        raise APIError(f"Không lấy được danh sách nghề: {e}")
    return data.get("occupations", [])


def analyze_cv(
    file_bytes: bytes,
    filename: str,
    occupation_key: str,
    include_recommendation: bool = True,
) -> dict:
    """POST /analyze — phân tích CV với nghề mục tiêu."""
    files = {"file": (filename, file_bytes)}
    form = {
        "occupation": occupation_key,
        "include_recommendation": str(include_recommendation).lower(),
    }
    try:
        resp = requests.post(_url("/analyze"), files=files, data=form, timeout=_TIMEOUT)
    except requests.RequestException as e:
        raise APIError(f"Lỗi gọi /analyze: {e}")
    return _handle_response(resp)


def get_history(limit: int = 20, occupation: Optional[str] = None) -> list[dict]:
    """GET /history — lịch sử đánh giá."""
    params: dict = {"limit": limit}
    if occupation:
        params["occupation"] = occupation
    try:
        data = _handle_response(
            requests.get(_url("/history"), params=params, timeout=_TIMEOUT)
        )
    except requests.RequestException as e:
        raise APIError(f"Không lấy được lịch sử: {e}")
    return data.get("items", [])
