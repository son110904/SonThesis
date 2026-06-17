"""
src.frontend.pages – Các trang của ứng dụng (render bằng hàm, điều hướng qua
session_state trong app.py). Sidebar nav tự sinh của Streamlit được ẩn bằng CSS.
"""

from src.frontend.pages.home import render_home
from src.frontend.pages.result import render_result

__all__ = ["render_home", "render_result"]
