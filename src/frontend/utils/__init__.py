"""src.frontend.utils – Tiện ích cho frontend: gọi API, styling."""

from src.frontend.utils.api_client import (
    APIError,
    analyze_cv,
    analyze_cv_saved,
    compare_cv_with_jd_saved,
    get_cv_info,
    get_cv_history,
    download_cv,
    activate_cv,
    delete_cv,
    get_occupations,
    health,
    login,
    register,
    save_cv,
)
from src.frontend.utils.styling import inject_css, render_header, COLORS
from src.frontend.utils.resources import (
    get_embedding_model,
    get_knowledge_base,
    get_health,
    is_model_ready,
    start_background_warmup,
)

__all__ = [
    "APIError",
    "analyze_cv",
    "analyze_cv_saved",
    "compare_cv_with_jd_saved",
    "get_cv_info",
    "get_cv_history",
    "download_cv",
    "activate_cv",
    "delete_cv",
    "get_occupations",
    "health",
    "login",
    "register",
    "save_cv",
    "inject_css",
    "render_header",
    "COLORS",
    "get_embedding_model",
    "get_knowledge_base",
    "get_health",
    "is_model_ready",
    "start_background_warmup",
]
