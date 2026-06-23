"""
app.py – Điểm vào ứng dụng ShibaCV.

Chạy:
    streamlit run src/frontend/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from src.frontend.utils import APIError, health, inject_css, render_header
from src.frontend.pages import (
    render_home,
    render_landing,
    render_result,
    render_scanning_page,
)


def main() -> None:
    st.set_page_config(
        page_title="ShibaCV – AI Career Intelligence",
        page_icon="🐾",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_css()

    st.session_state.setdefault("view", "landing")

    try:
        status = health()
        if not status.get("llm_available"):
            st.info(
                "Backend đang chạy nhưng **chưa cấu hình OPENAI_API_KEY** — điểm số "
                "vẫn tính đầy đủ, riêng phần khuyến nghị AI sẽ trống.",
                icon="ℹ️",
            )
    except APIError as e:
        st.error(f"Không kết nối được backend. {e}")
        st.caption("Khởi động backend: `uvicorn src.api.main:app --reload`")
        st.stop()

    view = st.session_state["view"]
    if view == "result":
        render_header()
        render_result()
    elif view == "scanning":
        render_scanning_page()
    elif view == "home":
        render_header()
        render_home()
    else:
        render_landing()


if __name__ == "__main__":
    main()
