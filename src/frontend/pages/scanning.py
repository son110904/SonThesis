"""scanning.py – Trang quét CV (loading).

Hiển thị sau khi người dùng bấm "Phân tích bằng AI" ở trang home. Trang này
render hiệu ứng quét + thoại Shiba + skeleton, đồng thời gọi backend analyze_cv;
xong thì chuyển sang trang kết quả.
"""

from __future__ import annotations

from src.frontend.utils.api_client import APIError, analyze_cv
from src.frontend.utils.styling import render_scanning


def render_scanning_page() -> None:
    import streamlit as st

    job = st.session_state.get("cv_job")
    if not job:
        # Vào thẳng trang này mà không có job -> quay về home.
        st.session_state["view"] = "home"
        st.rerun()
        return

    # Vẽ màn hình quét trước (animation chạy ở trình duyệt) rồi gọi backend.
    render_scanning()

    try:
        result = analyze_cv(**job)
    except APIError as e:
        st.session_state.pop("cv_job", None)
        st.error(f"Lỗi phân tích: {e}")
        if st.button("← Quay lại"):
            st.session_state["view"] = "home"
            st.rerun()
        return

    st.session_state["result"] = result
    st.session_state.pop("cv_job", None)
    st.session_state["view"] = "result"
    st.rerun()
