"""home.py – Trang upload CV."""

from __future__ import annotations

import logging

from src.frontend.utils.api_client import APIError, analyze_cv, get_occupations
from src.frontend.utils.styling import img_tag, render_footer

logger = logging.getLogger(__name__)


def _load_occupations() -> list[dict]:
    import streamlit as st

    @st.cache_data(show_spinner=False, ttl=300)
    def _fetch() -> list[dict]:
        return get_occupations()

    return _fetch()


def render_home() -> None:
    import streamlit as st

    st.markdown(
        """
        <div style="padding-top:0.5rem">
          <div class="page-h1">Cùng nâng cấp CV của bạn</div>
          <div class="page-h1-sub">
            Hãy tải CV của bạn lên và chọn lĩnh vực nghề nghiệp của mình.
            Shiba AI sẽ lo phần còn lại.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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

    col_form, col_shiba = st.columns([1.15, 0.85], gap="large")

    # ── Left: form ───────────────────────────────────────────────────────────
    with col_form:
        with st.form("analyze_form", clear_on_submit=False):
            uploaded = st.file_uploader(
                "Tải lên hồ sơ (PDF, DOCX)",
                type=["pdf", "docx"],
                accept_multiple_files=False,
                help="Kéo thả hoặc nhấn để chọn tệp",
            )

            st.markdown(
                """
                <div style="display:flex;align-items:center;gap:0.5rem;margin-top:1rem;margin-bottom:0.3rem">
                  <span style="font-size:0.82rem;color:var(--muted)">📁</span>
                  <span style="font-size:0.88rem;font-weight:600;color:var(--text)">Lĩnh vực nghề nghiệp của bạn</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            occ_display = st.selectbox(
                "Lĩnh vực nghề nghiệp",
                options=list(display_to_key.keys()),
                index=0,
                label_visibility="collapsed",
            )
            include_rec = st.toggle("Sinh khuyến nghị AI", value=True)
            st.markdown("<div style='margin-top:0.6rem'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("✦  Phân tích bằng AI", use_container_width=True)
            st.markdown(
                '<div class="privacy-note">🔒 Dữ liệu của bạn được bảo mật tuyệt đối bởi ShibaCV Guard.</div>',
                unsafe_allow_html=True,
            )

    # ── Right: shiba + cards ─────────────────────────────────────────────────
    with col_shiba:
        st.markdown(
            img_tag("shiba_ai.png", style="width:100%;max-width:320px;height:auto;display:block;margin:0 auto"),
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="shiba-ready-card">
              <div class="rct-label">🐾 Shiba đang sẵn sàng giúp bạn!</div>
              <div class="rct-quote">
                "Tôi sẽ quét qua hàng ngàn tiêu chuẩn tuyển dụng để đảm bảo
                CV của bạn luôn dẫn đầu xu hướng thị trường."
              </div>
            </div>
            <div class="stats-row">
              <div class="stat-chip">
                <div class="s-icon">✅</div>
                <div class="s-main">Chính xác 99%</div>
                <div class="s-sub">Phân tích sâu ATS</div>
              </div>
              <div class="stat-chip">
                <div class="s-icon">⚡</div>
                <div class="s-main">Tốc độ Shiba</div>
                <div class="s-sub">Xong trong 15s</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Submit ───────────────────────────────────────────────────────────────
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
        st.session_state["result"] = result
        st.session_state["view"] = "result"
        st.rerun()

    render_footer()
