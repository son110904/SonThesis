"""
cards.py – Thẻ metric (Semantic / Weighted) và thẻ AI Recommendation.
"""

from __future__ import annotations

import html

from src.frontend.utils.styling import COLORS, score_color


def render_metric_card(label: str, score_0_1: float) -> None:
    """
    Thẻ hiển thị 1 điểm thành phần (Semantic / Weighted) với thanh tiến độ.

    Args:
        label:     Nhãn (vd 'Semantic Similarity').
        score_0_1: Điểm ∈ [0, 1].
    """
    import streamlit as st

    pct = round(score_0_1 * 100, 1)
    color = score_color(score_0_1)
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="label">{html.escape(label)}</div>
          <div class="value" style="color:{color}">{pct:g}<span style="font-size:1rem;color:{COLORS['muted']}">/100</span></div>
          <div class="bar"><span style="width:{pct}%;background:{color}"></span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_recommendation_card(markdown_text: str | None) -> None:
    """
    Thẻ lớn hiển thị khuyến nghị AI (markdown). None → trạng thái rỗng có hướng dẫn.
    """
    import streamlit as st

    if not markdown_text:
        st.markdown(
            """
            <div class="rec-card">
              <strong>Chưa có khuyến nghị AI.</strong>
              <p class="hint" style="margin-top:.4rem">
                Đặt biến môi trường <code>OPENAI_API_KEY</code> trước khi chạy backend
                để bật phần đánh giá &amp; gợi ý học tập do GPT-4o Mini sinh.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Bọc markdown trong thẻ; Streamlit render markdown bên trong container HTML
    st.markdown('<div class="rec-card">', unsafe_allow_html=True)
    st.markdown(markdown_text)
    st.markdown("</div>", unsafe_allow_html=True)
