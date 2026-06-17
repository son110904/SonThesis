"""
home.py – Trang chủ: upload CV, chọn vị trí mong muốn, nút Analyze.
"""

from __future__ import annotations

import logging

from src.frontend.utils.api_client import APIError, analyze_cv, get_occupations

logger = logging.getLogger(__name__)


def _load_occupations() -> list[dict]:
    """Lấy danh sách nghề (cache để không gọi API mỗi lần rerun)."""
    import streamlit as st

    @st.cache_data(show_spinner=False, ttl=300)
    def _fetch() -> list[dict]:
        return get_occupations()

    return _fetch()


def render_home() -> None:
    """Render trang chủ."""
    import streamlit as st

    st.markdown(
        """
        <div class="app-header">
          <div class="title">Đánh giá độ phù hợp CV ↔ Nghề nghiệp</div>
          <div class="subtitle">Tải lên CV và chọn nhóm nghề mong muốn để nhận điểm phù hợp,
          phân tích kỹ năng còn thiếu và khuyến nghị phát triển.</div>
        </div>
        <hr class="app-divider"/>
        """,
        unsafe_allow_html=True,
    )

    # Lấy danh sách nghề
    try:
        occupations = _load_occupations()
    except APIError as e:
        st.error(f"Không tải được danh sách nghề. {e}")
        st.info("Hãy chắc chắn backend đang chạy: `uvicorn src.api.main:app`")
        return

    if not occupations:
        st.warning("Backend chưa có nghề nào. Hãy chạy offline pipeline trước.")
        return

    display_to_key = {o["display"]: o["key"] for o in occupations}

    with st.form("analyze_form", clear_on_submit=False):
        col1, col2 = st.columns([3, 2])
        with col1:
            uploaded = st.file_uploader(
                "CV của bạn (PDF hoặc DOCX)",
                type=["pdf", "docx"],
                accept_multiple_files=False,
            )
        with col2:
            occ_display = st.selectbox(
                "Vị trí / nhóm nghề mong muốn",
                options=list(display_to_key.keys()),
                index=0,
            )
            include_rec = st.toggle("Sinh khuyến nghị AI", value=True)

        submitted = st.form_submit_button("Phân tích", width="stretch")

    if submitted:
        if uploaded is None:
            st.warning("Vui lòng tải lên file CV trước.")
            return

        occ_key = display_to_key[occ_display]
        with st.spinner("Đang trích xuất CV, embed và đánh giá độ phù hợp…"):
            try:
                result = analyze_cv(
                    file_bytes=uploaded.getvalue(),
                    filename=uploaded.name,
                    occupation_key=occ_key,
                    include_recommendation=include_rec,
                )
            except APIError as e:
                st.error(f"Lỗi phân tích: {e}")
                return

        # Lưu kết quả và chuyển sang trang kết quả
        st.session_state["result"] = result
        st.session_state["view"] = "result"
        st.rerun()
