"""src.frontend.pages – Các trang của ứng dụng."""

from src.frontend.pages.home import render_home
from src.frontend.pages.landing import render_landing
from src.frontend.pages.recommend import render_recommend_page
from src.frontend.pages.result import render_result
from src.frontend.pages.scanning import render_scanning_page

__all__ = [
    "render_home",
    "render_landing",
    "render_recommend_page",
    "render_result",
    "render_scanning_page",
]
