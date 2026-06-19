"""
cards.py – Metric card và AI Recommendation card.
"""

from __future__ import annotations

import html

from src.frontend.utils.styling import COLORS, score_color


def render_metric_card(label: str, score_0_1: float) -> None:
    import streamlit as st

    pct = round(score_0_1 * 100, 1)
    color = score_color(score_0_1)
    icon = "🧠" if "Semantic" in label else "⭐"
    st.markdown(
        f"""
        <div class="metric-card-v2">
          <div class="mc-icon">{icon}</div>
          <div class="mc-label">{html.escape(label)}</div>
          <div class="mc-value" style="color:{color}">{pct:g}<span>/100</span></div>
          <div class="mc-track">
            <div class="mc-fill" style="width:{pct}%;background:{color}"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_recommendation_card(markdown_text: str | None) -> None:
    import streamlit as st

    if not markdown_text:
        st.markdown(
            """
            <div class="ai-rec-wrap">
              <div class="ai-rec-heading">Khuyến nghị từ Shiba AI</div>
              <strong>Chưa có khuyến nghị.</strong>
              <p class="hint" style="margin-top:.4rem">
                Đặt biến môi trường <code>OPENAI_API_KEY</code> trước khi chạy backend
                để bật phần đánh giá &amp; gợi ý học tập do GPT-4o Mini sinh.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown('<div class="ai-rec-wrap">', unsafe_allow_html=True)
    st.markdown(markdown_text)
    st.markdown("</div>", unsafe_allow_html=True)
