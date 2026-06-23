"""
api_client.py – Lớp truy cập backend từ Streamlit.

Hai chế độ, chọn tự động theo biến môi trường API_BASE_URL:

  • EMBEDDED (mặc định, khi KHÔNG đặt API_BASE_URL):
        Gọi THẲNG service layer trong cùng tiến trình — không cần chạy uvicorn.
        Dùng cho Hugging Face Spaces / Streamlit Cloud (1 container, 1 process).

  • REMOTE (khi đặt API_BASE_URL, vd http://127.0.0.1:8000):
        Gọi REST API qua HTTP tới FastAPI backend (kiến trúc 2 service, dev local).

Cùng một bộ hàm (health/get_occupations/analyze_cv/get_history) cho cả hai chế độ
→ phần UI không cần biết đang chạy ở đâu.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Đặt API_BASE_URL (vd "http://127.0.0.1:8000") → chế độ REMOTE qua HTTP.
# Bỏ trống → chế độ EMBEDDED, gọi service trực tiếp trong tiến trình.
API_BASE_URL: Optional[str] = (os.getenv("API_BASE_URL") or "").rstrip("/") or None
_REMOTE: bool = API_BASE_URL is not None

# Giới hạn kích thước file CV (10 MB) — đồng bộ với routes.py.
_MAX_FILE_BYTES = 10 * 1024 * 1024


class APIError(Exception):
    """Lỗi khi truy cập backend (kết nối, HTTP 4xx/5xx, hoặc lỗi xử lý embedded)."""


# ══════════════════════════════════════════════════════════════════════════
# REMOTE (HTTP) — giữ nguyên hành vi cũ
# ══════════════════════════════════════════════════════════════════════════
_TIMEOUT = (5, 120)  # (connect, read) — read dài vì /analyze có thể gọi LLM


def _url(path: str) -> str:
    return f"{API_BASE_URL}{path}"


def _handle_response(resp) -> dict:
    if resp.ok:
        return resp.json()
    try:
        detail = resp.json().get("detail", resp.text)
    except Exception:  # noqa: BLE001
        detail = resp.text or f"HTTP {resp.status_code}"
    raise APIError(f"[{resp.status_code}] {detail}")


def _http_health() -> dict:
    import requests
    try:
        return _handle_response(requests.get(_url("/health"), timeout=_TIMEOUT))
    except requests.RequestException as e:
        raise APIError(f"Không kết nối được backend tại {API_BASE_URL}. ({e})")


def _http_get_occupations() -> list[dict]:
    import requests
    try:
        data = _handle_response(requests.get(_url("/occupations"), timeout=_TIMEOUT))
    except requests.RequestException as e:
        raise APIError(f"Không lấy được danh sách nghề: {e}")
    return data.get("occupations", [])


def _http_analyze_cv(file_bytes, filename, occupation_key, include_recommendation) -> dict:
    import requests
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


def _http_get_history(limit, occupation) -> list[dict]:
    import requests
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


# ══════════════════════════════════════════════════════════════════════════
# EMBEDDED — gọi service layer trực tiếp (import lazy để chế độ REMOTE không
# phải nạp torch/sentence-transformers)
# ══════════════════════════════════════════════════════════════════════════
def _embedded_health() -> dict:
    try:
        from src.online.recommendation_step11.llm_client import get_llm_client
        return {"status": "ok", "llm_available": get_llm_client().is_available()}
    except Exception as e:  # noqa: BLE001
        raise APIError(f"Backend embedded lỗi khởi tạo: {e}")


def _embedded_get_occupations() -> list[dict]:
    try:
        from src.online.services import list_occupations
        return list(list_occupations())
    except Exception as e:  # noqa: BLE001
        raise APIError(f"Không lấy được danh sách nghề (embedded): {e}")


def _embedded_analyze_cv(file_bytes, filename, occupation_key, include_recommendation) -> dict:
    if not file_bytes:
        raise APIError("File rỗng.")
    if len(file_bytes) > _MAX_FILE_BYTES:
        raise APIError("File quá lớn (tối đa 10MB).")

    from src.online.services import analyze_cv as _service_analyze
    from src.online.services.occupation_loader import OccupationNotFound
    from src.online.services.analysis_service import EmptyCVError
    from src.online.extraction_step2.text_extractor import UnsupportedFileType

    try:
        result = _service_analyze(
            file_bytes=file_bytes,
            filename=filename or "cv",
            occupation_key=occupation_key,
            include_recommendation=include_recommendation,
        )
    except OccupationNotFound as e:
        raise APIError(str(e))
    except UnsupportedFileType as e:
        raise APIError(str(e))
    except EmptyCVError as e:
        raise APIError(str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi phân tích CV (embedded)")
        raise APIError(f"Lỗi xử lý: {e}")
    return result.to_dict()


def _embedded_get_history(limit, occupation) -> list[dict]:
    try:
        from src.database import list_evaluations
        rows = list_evaluations(limit=limit, occupation_key=occupation)
    except Exception as e:  # noqa: BLE001
        raise APIError(f"Không lấy được lịch sử (embedded): {e}")
    return [
        {
            "id": r["id"],
            "created_at": r.get("created_at", ""),
            "cv_filename": r.get("cv_filename"),
            "occupation_key": r["occupation_key"],
            "occupation_display": r.get("occupation_display"),
            "match_score": r.get("match_score"),
            "semantic_similarity_score": r.get("semantic_similarity_score"),
            "weighted_skill_score": r.get("weighted_skill_score"),
            "matched_skills": r.get("matched_skills") or [],
            "missing_skills": r.get("missing_skills") or [],
            "candidate_profile": r.get("candidate_profile")
            if isinstance(r.get("candidate_profile"), dict) else None,
            "ai_recommendation": r.get("ai_recommendation"),
        }
        for r in rows
    ]


# ══════════════════════════════════════════════════════════════════════════
# API công khai — tự định tuyến theo chế độ
# ══════════════════════════════════════════════════════════════════════════
def health() -> dict:
    """Trạng thái backend + LLM."""
    return _http_health() if _REMOTE else _embedded_health()


def get_occupations() -> list[dict]:
    """Danh sách nghề cho dropdown."""
    return _http_get_occupations() if _REMOTE else _embedded_get_occupations()


def analyze_cv(
    file_bytes: bytes,
    filename: str,
    occupation_key: str,
    include_recommendation: bool = True,
) -> dict:
    """Phân tích CV với nghề mục tiêu (Bước 2-11)."""
    if _REMOTE:
        return _http_analyze_cv(file_bytes, filename, occupation_key, include_recommendation)
    return _embedded_analyze_cv(file_bytes, filename, occupation_key, include_recommendation)


def get_history(limit: int = 20, occupation: Optional[str] = None) -> list[dict]:
    """Lịch sử đánh giá."""
    return _http_get_history(limit, occupation) if _REMOTE else _embedded_get_history(limit, occupation)
