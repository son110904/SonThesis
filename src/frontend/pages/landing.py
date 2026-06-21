"""landing.py – Trang chủ hero."""

from __future__ import annotations

from src.frontend.utils.styling import img_tag, render_footer


def render_landing() -> None:
    import streamlit as st

    col_l, col_r = st.columns([1, 1], gap="large")

    with col_l:
        st.markdown(
            """
            <div style="padding: 3rem 0 2rem; min-height: 320px; display:flex; flex-direction:column; justify-content:center">
              <div class="hero-eyebrow"></div>
              <div class="hero-title">
                Nâng tầm sự nghiệp cùng<br>
                <span class="accent">Shiba Intelligence</span>
              </div>
              <div class="hero-subtitle">
                AI đánh giá CV, phân tích kỹ năng và đưa ra lộ trình nghề nghiệp
                hoàn hảo cho bạn. Khám phá tiềm năng thực sự của bản thân ngay hôm nay.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Bắt đầu ngay →", key="cta_hero"):
            st.session_state["view"] = "home"
            st.rerun()

    with col_r:
        st.markdown(
            f'<div class="hero-img-card">{img_tag("shiba_desk.png")}</div>',
            unsafe_allow_html=True,
        )

    render_footer()
