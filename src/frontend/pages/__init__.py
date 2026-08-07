"""src.frontend.pages – Các trang của ứng dụng."""

from src.frontend.pages.auth import render_auth_page
from src.frontend.pages.home import render_home
from src.frontend.pages.jd_comparison import (
    render_jd_comparison_page,
    render_jd_result,
)
from src.frontend.pages.landing import render_landing
from src.frontend.pages.result import render_result
from src.frontend.pages.scanning import render_scanning_page

__all__ = [
    "render_auth_page",
    "render_home",
    "render_jd_comparison_page",
    "render_jd_result",
    "render_landing",
    "render_result",
    "render_scanning_page",
]
