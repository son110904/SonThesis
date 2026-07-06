"""src.frontend.utils – Tiện ích cho frontend: gọi API, styling."""

from src.frontend.utils.api_client import (
    APIError,
    analyze_cv,
    get_occupations,
    health,
    recommend_occupations,
    review_occupation,
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
    "get_occupations",
    "health",
    "recommend_occupations",
    "review_occupation",
    "inject_css",
    "render_header",
    "COLORS",
    "get_embedding_model",
    "get_knowledge_base",
    "get_health",
    "is_model_ready",
    "start_background_warmup",
]
