"""src.frontend.utils – Tiện ích cho frontend: gọi API, styling."""

from src.frontend.utils.api_client import (
    APIError,
    analyze_cv,
    get_history,
    get_occupations,
    health,
)
from src.frontend.utils.styling import inject_css, COLORS

__all__ = [
    "APIError",
    "analyze_cv",
    "get_history",
    "get_occupations",
    "health",
    "inject_css",
    "COLORS",
]
