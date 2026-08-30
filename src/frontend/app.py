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

from src.frontend.utils import (
    APIError,
    get_health,
    inject_css,
    render_header,
    start_background_warmup,
)
from src.frontend.pages import (
    render_auth_page,
    render_home,
    render_jd_comparison_page,
    render_jd_result,
    render_landing,
    render_result,
    render_scanning_page,
)


def main() -> None:
    st.set_page_config(
        page_title="ShibaCV – AI Career Intelligence",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_css()

    # Nạp model + KB ở luồng nền NGAY khi app khởi động (không chặn UI). Tới lúc
    # người dùng bấm "Phân tích" thì model thường đã sẵn sàng → không khựng.
    start_background_warmup()

    st.session_state.setdefault("view", "landing")

    try:
        status = get_health()
        # Banner kỹ thuật chỉ hiện ở trang làm việc — không đè lên landing.
        if not status.get("llm_available") and st.session_state["view"] not in ("landing", "scanning"):
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
    if view == "jd_result":
        render_header()
        render_jd_result()
    elif view == "jd_comparison":
        render_jd_comparison_page()
    elif view == "result":
        render_header()
        render_result()
    elif view == "scanning":
        render_scanning_page()
    elif view == "auth":
        render_header()
        render_auth_page()
    elif view == "home":
        render_header()
        render_home()
    else:
        render_landing()


if __name__ == "__main__":
    main()
