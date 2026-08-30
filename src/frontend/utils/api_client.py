"""
api_client.py – Lớp truy cập backend từ Streamlit.

Hai chế độ, chọn tự động theo biến môi trường API_BASE_URL:

  • EMBEDDED (mặc định, khi KHÔNG đặt API_BASE_URL):
        Gọi THẲNG service layer trong cùng tiến trình — không cần chạy uvicorn.
        Dùng cho Hugging Face Spaces / Streamlit Cloud (1 container, 1 process).

  • REMOTE (khi đặt API_BASE_URL, vd http://127.0.0.1:8000):
        Gọi REST API qua HTTP tới FastAPI backend (kiến trúc 2 service, dev local).

Cùng một bộ hàm (health/get_occupations/analyze_cv/compare_cv_with_jd) cho cả hai
chế độ → phần UI không cần biết đang chạy ở đâu.
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


def _http_cv_improvement(
    candidate_profile, occupation_key, semantic_similarity_score,
    weighted_skill_score, matched_skills, missing_skills,
) -> Optional[dict]:
    import requests
    payload = {
        "candidate_profile": candidate_profile,
        "occupation": occupation_key,
        "semantic_similarity_score": semantic_similarity_score,
        "weighted_skill_score": weighted_skill_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
    }
    try:
        resp = requests.post(_url("/cv-improvement"), json=payload, timeout=_TIMEOUT)
    except requests.RequestException as e:
        raise APIError(f"Lỗi gọi /cv-improvement: {e}")
    return _handle_response(resp).get("cv_improvement")


def _http_application_email(
    candidate_profile, occupation_key, semantic_similarity_score,
    weighted_skill_score, matched_skills, missing_skills, cv_review,
) -> Optional[dict]:
    import requests
    payload = {
        "candidate_profile": candidate_profile,
        "occupation": occupation_key,
        "semantic_similarity_score": semantic_similarity_score,
        "weighted_skill_score": weighted_skill_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "cv_review": cv_review,
    }
    try:
        resp = requests.post(_url("/application-email"), json=payload, timeout=_TIMEOUT)
    except requests.RequestException as e:
        raise APIError(f"Lỗi gọi /application-email: {e}")
    return _handle_response(resp).get("application_email")


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


def _embedded_cv_improvement(
    candidate_profile, occupation_key, semantic_similarity_score,
    weighted_skill_score, matched_skills, missing_skills,
) -> Optional[dict]:
    from src.online.services import generate_cv_improvement_for_occupation as _svc_improve
    from src.online.services.occupation_loader import OccupationNotFound

    try:
        return _svc_improve(
            candidate_profile=candidate_profile,
            occupation_key=occupation_key,
            semantic_similarity_score=semantic_similarity_score,
            weighted_skill_score=weighted_skill_score,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
        )
    except OccupationNotFound as e:
        raise APIError(str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi sinh AI CV Improvement (embedded)")
        raise APIError(f"Lỗi xử lý: {e}")


def _embedded_application_email(
    candidate_profile, occupation_key, semantic_similarity_score,
    weighted_skill_score, matched_skills, missing_skills, cv_review,
) -> Optional[dict]:
    from src.online.services import generate_application_email_for_occupation as _svc_email
    from src.online.services.occupation_loader import OccupationNotFound

    try:
        return _svc_email(
            candidate_profile=candidate_profile,
            occupation_key=occupation_key,
            semantic_similarity_score=semantic_similarity_score,
            weighted_skill_score=weighted_skill_score,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            cv_review=cv_review,
        )
    except OccupationNotFound as e:
        raise APIError(str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi sinh Application Email (embedded)")
        raise APIError(f"Lỗi xử lý: {e}")


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


def generate_cv_improvement(
    candidate_profile: dict,
    occupation_key: str,
    semantic_similarity_score: float,
    weighted_skill_score: float,
    matched_skills: list,
    missing_skills: list,
) -> Optional[dict]:
    """Sinh AI CV Improvement — tiếp nối AI CV Review (tái dùng profile + điểm số)."""
    args = (candidate_profile, occupation_key, semantic_similarity_score,
            weighted_skill_score, matched_skills, missing_skills)
    if _REMOTE:
        return _http_cv_improvement(*args)
    return _embedded_cv_improvement(*args)


def generate_application_email(
    candidate_profile: dict,
    occupation_key: str,
    semantic_similarity_score: float,
    weighted_skill_score: float,
    matched_skills: list,
    missing_skills: list,
    cv_review: Optional[dict] = None,
) -> Optional[dict]:
    """Sinh Application Email — CHỈ gọi khi người dùng chủ động bấm nút."""
    args = (candidate_profile, occupation_key, semantic_similarity_score,
            weighted_skill_score, matched_skills, missing_skills, cv_review)
    if _REMOTE:
        return _http_application_email(*args)
    return _embedded_application_email(*args)


# ─── JD Comparison (Chế độ 2) ────────────────────────────────────────────────
def _http_compare_cv_with_jd(cv_bytes, cv_filename, jd_bytes, jd_filename, jd_text) -> dict:
    import requests
    files = {"cv_file": (cv_filename, cv_bytes)}
    if jd_bytes:
        files["jd_file"] = (jd_filename or "jd", jd_bytes)
    try:
        resp = requests.post(
            _url("/compare-jd"), files=files, data={"jd_text": jd_text or ""}, timeout=_TIMEOUT
        )
    except requests.RequestException as e:
        raise APIError(f"Lỗi gọi /compare-jd: {e}")
    return _handle_response(resp)


def _embedded_compare_cv_with_jd(cv_bytes, cv_filename, jd_bytes, jd_filename, jd_text) -> dict:
    from src.online.services import compare_cv_with_jd as _svc_jd
    from src.online.extraction_step2.text_extractor import UnsupportedFileType
    from src.online.services.analysis_service import EmptyCVError
    from src.online.validation import NotACVError

    try:
        result = _svc_jd(
            cv_file_bytes=cv_bytes,
            cv_filename=cv_filename or "cv",
            jd_file_bytes=jd_bytes,
            jd_filename=jd_filename or "",
            jd_text=jd_text,
        )
    except (EmptyCVError, NotACVError, UnsupportedFileType, ValueError) as e:
        raise APIError(str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi so sánh CV ↔ JD (embedded)")
        raise APIError(f"Lỗi xử lý: {e}")

    # Normalize: candidate_profile là CandidateProfile dataclass → convert sang dict
    # để UI xử lý đồng nhất với REMOTE mode (JSON dict).
    cp = result.get("candidate_profile")
    if cp is not None and not isinstance(cp, dict):
        result["candidate_profile"] = cp.to_dict() if hasattr(cp, "to_dict") else dict(cp)
    return result


def compare_cv_with_jd(
    cv_bytes: bytes,
    cv_filename: str,
    jd_bytes: Optional[bytes] = None,
    jd_filename: str = "",
    jd_text: str = "",
) -> dict:
    """
    So sánh trực tiếp CV ↔ JD cụ thể (chế độ 2, không dùng Occupation KB).

    JD truyền qua `jd_bytes` (file) HOẶC `jd_text` (dán trực tiếp).
    """
    args = (cv_bytes, cv_filename, jd_bytes, jd_filename, jd_text)
    if _REMOTE:
        return _http_compare_cv_with_jd(*args)
    return _embedded_compare_cv_with_jd(*args)


def _http_jd_cv_improvement(
    candidate_profile, jd_position, jd_skills, semantic_similarity_score,
    coverage_pct, matched_skills, missing_skills,
) -> Optional[dict]:
    import requests
    payload = {
        "candidate_profile": candidate_profile,
        "jd_position": jd_position,
        "jd_skills": jd_skills,
        "semantic_similarity_score": semantic_similarity_score,
        "coverage_pct": coverage_pct,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
    }
    try:
        resp = requests.post(_url("/jd/cv-improvement"), json=payload, timeout=_TIMEOUT)
    except requests.RequestException as e:
        raise APIError(f"Lỗi gọi /jd/cv-improvement: {e}")
    return _handle_response(resp).get("cv_improvement")


def _http_jd_application_email(
    candidate_profile, jd_skills, jd_text_preview,
    semantic_similarity_score, coverage_pct, matched_skills,
    missing_skills, cv_review,
) -> Optional[dict]:
    import requests
    payload = {
        "candidate_profile": candidate_profile,
        "jd_skills": jd_skills,
        "jd_text_preview": jd_text_preview,
        "semantic_similarity_score": semantic_similarity_score,
        "coverage_pct": coverage_pct,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "cv_review": cv_review,
    }
    try:
        resp = requests.post(_url("/jd/application-email"), json=payload, timeout=_TIMEOUT)
    except requests.RequestException as e:
        raise APIError(f"Lỗi gọi /jd/application-email: {e}")
    return _handle_response(resp).get("application_email")


def _embedded_jd_cv_improvement(
    candidate_profile, jd_position, jd_skills, semantic_similarity_score,
    coverage_pct, matched_skills, missing_skills,
) -> Optional[dict]:
    from src.online.services import generate_cv_improvement_for_jd as _svc_improve

    try:
        return _svc_improve(
            candidate_profile=candidate_profile,
            jd_position=jd_position,
            jd_skills=jd_skills,
            semantic_similarity_score=semantic_similarity_score,
            coverage_pct=coverage_pct,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi sinh AI CV Improvement cho JD (embedded)")
        raise APIError(f"Lỗi xử lý: {e}")


def _embedded_jd_application_email(
    candidate_profile, jd_skills, jd_text_preview,
    semantic_similarity_score, coverage_pct, matched_skills,
    missing_skills, cv_review,
) -> Optional[dict]:
    from src.online.services import generate_application_email_for_jd as _svc_email

    try:
        return _svc_email(
            candidate_profile=candidate_profile,
            jd_skills=jd_skills,
            jd_text_preview=jd_text_preview,
            semantic_similarity_score=semantic_similarity_score,
            coverage_pct=coverage_pct,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            cv_review=cv_review,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi sinh Application Email cho JD (embedded)")
        raise APIError(f"Lỗi xử lý: {e}")


def generate_cv_improvement_for_jd(
    candidate_profile: dict,
    jd_position: str,
    jd_skills: list,
    semantic_similarity_score: float,
    coverage_pct: float,
    matched_skills: list,
    missing_skills: list,
) -> Optional[dict]:
    """Sinh AI CV Improvement cho JD Comparison — tiếp nối AI CV Review (tự động, không cần bấm nút)."""
    args = (candidate_profile, jd_position, jd_skills, semantic_similarity_score,
            coverage_pct, matched_skills, missing_skills)
    if _REMOTE:
        return _http_jd_cv_improvement(*args)
    return _embedded_jd_cv_improvement(*args)


def generate_application_email_for_jd(
    candidate_profile: dict,
    jd_skills: list,
    jd_text_preview: str,
    semantic_similarity_score: float,
    coverage_pct: float,
    matched_skills: list,
    missing_skills: list,
    cv_review: Optional[dict] = None,
) -> Optional[dict]:
    """Sinh Application Email cho JD Comparison — CHỈ gọi khi người dùng chủ động bấm nút.

    KHÔNG nhận jd_position (tên vị trí đoán bằng heuristic có thể sai, mà đây là thư
    gửi thật cho nhà tuyển dụng) — LLM tự đọc jd_text_preview.
    """
    args = (candidate_profile, jd_skills, jd_text_preview,
            semantic_similarity_score, coverage_pct, matched_skills,
            missing_skills, cv_review)
    if _REMOTE:
        return _http_jd_application_email(*args)
    return _embedded_jd_application_email(*args)


# ══════════════════════════════════════════════════════════════════════════
# Authentication (đăng ký/đăng nhập + lưu CV tái sử dụng)
# ══════════════════════════════════════════════════════════════════════════
def _http_register(full_name, email, password) -> dict:
    import requests
    try:
        resp = requests.post(
            _url("/auth/register"),
            json={"full_name": full_name, "email": email, "password": password},
            timeout=_TIMEOUT,
        )
    except requests.RequestException as e:
        raise APIError(f"Lỗi gọi /auth/register: {e}")
    return _handle_response(resp)


def _http_login(email, password) -> dict:
    import requests
    try:
        resp = requests.post(
            _url("/auth/login"), json={"email": email, "password": password}, timeout=_TIMEOUT
        )
    except requests.RequestException as e:
        raise APIError(f"Lỗi gọi /auth/login: {e}")
    return _handle_response(resp)


def _http_save_cv(user_id, file_bytes, filename) -> dict:
    import requests
    files = {"file": (filename, file_bytes)}
    form = {"user_id": str(user_id)}
    try:
        resp = requests.post(_url("/auth/cv"), files=files, data=form, timeout=_TIMEOUT)
    except requests.RequestException as e:
        raise APIError(f"Lỗi gọi /auth/cv: {e}")
    return _handle_response(resp)


def _http_get_cv_info(user_id) -> Optional[dict]:
    import requests
    try:
        resp = requests.get(_url(f"/auth/cv/{user_id}"), timeout=_TIMEOUT)
    except requests.RequestException as e:
        raise APIError(f"Lỗi gọi /auth/cv/{{id}}: {e}")
    if resp.status_code == 404:
        return None
    return _handle_response(resp)


def _http_get_cv_history(user_id) -> list[dict]:
    import requests
    try:
        resp = requests.get(_url(f"/auth/cv/{user_id}/history"), timeout=_TIMEOUT)
    except requests.RequestException as e:
        raise APIError(f"Lỗi gọi /auth/cv/{{id}}/history: {e}")
    return _handle_response(resp).get("items", [])


def _http_download_cv(user_id, cv_id) -> tuple[bytes, str]:
    import re as _re
    import requests
    from urllib.parse import unquote
    try:
        resp = requests.get(_url(f"/auth/cv/{user_id}/file/{cv_id}"), timeout=_TIMEOUT)
    except requests.RequestException as e:
        raise APIError(f"Lỗi tải CV: {e}")
    if resp.status_code != 200:
        raise APIError("Không tải được tệp CV này.")
    cd = resp.headers.get("content-disposition", "")
    m = _re.search(r"filename\*=UTF-8''([^;]+)", cd)
    return resp.content, unquote(m.group(1)) if m else "cv"


def _http_activate_cv(user_id, cv_id) -> dict:
    import requests
    try:
        resp = requests.post(
            _url("/auth/cv/activate"),
            json={"user_id": user_id, "cv_id": cv_id},
            timeout=_TIMEOUT,
        )
    except requests.RequestException as e:
        raise APIError(f"Lỗi gọi /auth/cv/activate: {e}")
    return _handle_response(resp)


def _http_delete_cv(user_id, cv_id) -> None:
    import requests
    try:
        resp = requests.delete(_url(f"/auth/cv/{user_id}/{cv_id}"), timeout=_TIMEOUT)
    except requests.RequestException as e:
        raise APIError(f"Lỗi gọi DELETE /auth/cv: {e}")
    _handle_response(resp)


def _http_analyze_cv_saved(user_id, occupation_key, include_recommendation) -> dict:
    import requests
    payload = {
        "user_id": user_id,
        "occupation": occupation_key,
        "include_recommendation": include_recommendation,
    }
    try:
        resp = requests.post(_url("/analyze-saved"), json=payload, timeout=_TIMEOUT)
    except requests.RequestException as e:
        raise APIError(f"Lỗi gọi /analyze-saved: {e}")
    return _handle_response(resp)


def _http_compare_cv_with_jd_saved(user_id, jd_bytes, jd_filename, jd_text) -> dict:
    import requests
    files = {"jd_file": (jd_filename or "jd", jd_bytes)} if jd_bytes else None
    form = {"user_id": str(user_id), "jd_text": jd_text or ""}
    try:
        resp = requests.post(_url("/compare-jd-saved"), files=files, data=form, timeout=_TIMEOUT)
    except requests.RequestException as e:
        raise APIError(f"Lỗi gọi /compare-jd-saved: {e}")
    return _handle_response(resp)


def _embedded_register(full_name, email, password) -> dict:
    from src.online.services import register_user as _svc
    from src.database.repository import EmailAlreadyExistsError

    try:
        return _svc(full_name, email, password)
    except EmailAlreadyExistsError as e:
        raise APIError(str(e))
    except ValueError as e:
        raise APIError(str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi đăng ký (embedded)")
        raise APIError(f"Lỗi xử lý: {e}")


def _embedded_login(email, password) -> dict:
    from src.online.services import login_user as _svc
    from src.online.services import InvalidCredentialsError

    try:
        return _svc(email, password)
    except InvalidCredentialsError as e:
        raise APIError(str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi đăng nhập (embedded)")
        raise APIError(f"Lỗi xử lý: {e}")


def _embedded_save_cv(user_id, file_bytes, filename) -> dict:
    if not file_bytes:
        raise APIError("File rỗng.")
    if len(file_bytes) > _MAX_FILE_BYTES:
        raise APIError("File quá lớn (tối đa 10MB).")

    from src.online.services import save_cv_for_user as _svc

    try:
        return _svc(user_id, file_bytes, filename or "cv")
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi lưu CV (embedded)")
        raise APIError(f"Lỗi xử lý: {e}")


def _embedded_get_cv_info(user_id) -> Optional[dict]:
    from src.online.services import get_cv_info_for_user as _svc

    try:
        return _svc(user_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi lấy thông tin CV (embedded)")
        raise APIError(f"Lỗi xử lý: {e}")


def _embedded_get_cv_history(user_id) -> list[dict]:
    from src.online.services import list_cv_history_for_user as _svc

    try:
        return _svc(user_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi lấy lịch sử CV (embedded)")
        raise APIError(f"Lỗi xử lý: {e}")


def _embedded_download_cv(user_id, cv_id) -> tuple[bytes, str]:
    from src.online.services import read_cv_file_for_user as _svc
    from src.online.services import NoSavedCVError

    try:
        return _svc(user_id, cv_id)
    except NoSavedCVError as e:
        raise APIError(str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi đọc tệp CV (embedded)")
        raise APIError(f"Lỗi xử lý: {e}")


def _embedded_activate_cv(user_id, cv_id) -> dict:
    from src.online.services import activate_cv_for_user as _svc
    from src.online.services import NoSavedCVError

    try:
        return _svc(user_id, cv_id)
    except NoSavedCVError as e:
        raise APIError(str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi chọn CV (embedded)")
        raise APIError(f"Lỗi xử lý: {e}")


def _embedded_delete_cv(user_id, cv_id) -> None:
    from src.online.services import delete_cv_for_user as _svc
    from src.online.services import NoSavedCVError

    try:
        _svc(user_id, cv_id)
    except NoSavedCVError as e:
        raise APIError(str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi xóa CV (embedded)")
        raise APIError(f"Lỗi xử lý: {e}")


def _embedded_analyze_cv_saved(user_id, occupation_key, include_recommendation) -> dict:
    from src.online.services import analyze_cv_for_saved_user as _svc
    from src.online.services import NoSavedCVError
    from src.online.services.occupation_loader import OccupationNotFound
    from src.online.services.analysis_service import EmptyCVError

    try:
        result = _svc(
            user_id=user_id,
            occupation_key=occupation_key,
            include_recommendation=include_recommendation,
        )
    except (OccupationNotFound, NoSavedCVError, EmptyCVError) as e:
        raise APIError(str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi phân tích CV đã lưu (embedded)")
        raise APIError(f"Lỗi xử lý: {e}")
    return result.to_dict()


def _embedded_compare_cv_with_jd_saved(user_id, jd_bytes, jd_filename, jd_text) -> dict:
    from src.online.services import compare_saved_cv_with_jd as _svc
    from src.online.services import NoSavedCVError
    from src.online.extraction_step2.text_extractor import UnsupportedFileType
    from src.online.services.analysis_service import EmptyCVError
    from src.online.validation import NotACVError

    try:
        result = _svc(
            user_id=user_id,
            jd_file_bytes=jd_bytes,
            jd_filename=jd_filename or "",
            jd_text=jd_text,
        )
    except (NoSavedCVError, EmptyCVError, NotACVError, UnsupportedFileType, ValueError) as e:
        raise APIError(str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi so sánh CV đã lưu với JD (embedded)")
        raise APIError(f"Lỗi xử lý: {e}")

    cp = result.get("candidate_profile")
    if cp is not None and not isinstance(cp, dict):
        result["candidate_profile"] = cp.to_dict() if hasattr(cp, "to_dict") else dict(cp)
    return result


def register(full_name: str, email: str, password: str) -> dict:
    """Đăng ký tài khoản mới. Trả {id, full_name, email}."""
    if _REMOTE:
        return _http_register(full_name, email, password)
    return _embedded_register(full_name, email, password)


def login(email: str, password: str) -> dict:
    """Đăng nhập bằng email + mật khẩu. Trả {id, full_name, email}."""
    if _REMOTE:
        return _http_login(email, password)
    return _embedded_login(email, password)


def save_cv(user_id: int, file_bytes: bytes, filename: str) -> dict:
    """Lưu/ghi đè CV đã lưu của tài khoản."""
    if _REMOTE:
        return _http_save_cv(user_id, file_bytes, filename)
    return _embedded_save_cv(user_id, file_bytes, filename)


def get_cv_info(user_id: int) -> Optional[dict]:
    """Thông tin CV ĐANG DÙNG của tài khoản (None nếu chưa upload)."""
    if _REMOTE:
        return _http_get_cv_info(user_id)
    return _embedded_get_cv_info(user_id)


def get_cv_history(user_id: int) -> list[dict]:
    """Lịch sử CV đã tải của tài khoản, mới nhất trước."""
    if _REMOTE:
        return _http_get_cv_history(user_id)
    return _embedded_get_cv_history(user_id)


def download_cv(user_id: int, cv_id: int) -> tuple[bytes, str]:
    """Đọc nội dung 1 CV trong lịch sử → (bytes, tên tệp gốc)."""
    if _REMOTE:
        return _http_download_cv(user_id, cv_id)
    return _embedded_download_cv(user_id, cv_id)


def activate_cv(user_id: int, cv_id: int) -> dict:
    """Chọn 1 CV trong lịch sử làm CV dùng cho các lần phân tích sau."""
    if _REMOTE:
        return _http_activate_cv(user_id, cv_id)
    return _embedded_activate_cv(user_id, cv_id)


def delete_cv(user_id: int, cv_id: int) -> None:
    """Xóa 1 CV khỏi lịch sử. Raise APIError nếu đang là CV active hoặc không thuộc user."""
    if _REMOTE:
        return _http_delete_cv(user_id, cv_id)
    return _embedded_delete_cv(user_id, cv_id)


def analyze_cv_saved(user_id: int, occupation_key: str, include_recommendation: bool = True) -> dict:
    """Phân tích CV ĐÃ LƯU của tài khoản với 1 nghề (không cần upload lại)."""
    if _REMOTE:
        return _http_analyze_cv_saved(user_id, occupation_key, include_recommendation)
    return _embedded_analyze_cv_saved(user_id, occupation_key, include_recommendation)


def compare_cv_with_jd_saved(
    user_id: int,
    jd_bytes: Optional[bytes] = None,
    jd_filename: str = "",
    jd_text: str = "",
) -> dict:
    """So sánh CV ĐÃ LƯU của tài khoản với 1 JD (không cần upload lại CV).

    JD truyền qua `jd_bytes` (file) HOẶC `jd_text` (dán trực tiếp).
    """
    args = (user_id, jd_bytes, jd_filename, jd_text)
    if _REMOTE:
        return _http_compare_cv_with_jd_saved(*args)
    return _embedded_compare_cv_with_jd_saved(*args)
