"""
app.py – Điểm vào ứng dụng Streamlit.

Chạy:
    streamlit run src/frontend/app.py

Điều hướng giữa trang chủ (home) và trang kết quả (result) qua session_state,
sidebar nav tự sinh của Streamlit được ẩn bằng CSS (xem styling.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Cho phép import 'src.*' khi chạy bằng `streamlit run`
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from src.frontend.utils import APIError, health, inject_css
from src.frontend.pages import render_home, render_result


def main() -> None:
    st.set_page_config(
        page_title="CV ↔ Occupation Matching",
        page_icon="•",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    inject_css()

    st.session_state.setdefault("view", "home")

    # Banner cảnh báo nếu backend chưa sẵn sàng / chưa có LLM
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

    if st.session_state["view"] == "result":
        render_result()
    else:
        render_home()


if __name__ == "__main__":
    main()
