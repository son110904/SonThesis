"""
score_gauge.py – Gauge chart cho Match Score (Plotly).

Hiển thị điểm 0-100 với màu semantic (đỏ/amber/xanh). Nền trong suốt, font
Manrope để khớp phần còn lại của giao diện.
"""

from __future__ import annotations

from src.frontend.utils.styling import COLORS, score_color


def render_match_gauge(match_score_0_1: float, height: int = 260) -> None:
    """
    Vẽ gauge Match Score.

    Args:
        match_score_0_1: Điểm ∈ [0, 1].
        height:          Chiều cao chart (px).
    """
    import plotly.graph_objects as go
    import streamlit as st

    pct = round(match_score_0_1 * 100, 1)
    color = score_color(match_score_0_1)

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=pct,
            number={"suffix": "", "font": {"size": 44, "color": COLORS["text"]}},
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickwidth": 1,
                    "tickcolor": COLORS["border"],
                    "tickfont": {"size": 11, "color": COLORS["muted"]},
                },
                "bar": {"color": color, "thickness": 0.28},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 40], "color": "#f6ddd5"},
                    {"range": [40, 70], "color": "#f6e7cf"},
                    {"range": [70, 100], "color": "#e3efe1"},
                ],
                "threshold": {
                    "line": {"color": color, "width": 3},
                    "thickness": 0.8,
                    "value": pct,
                },
            },
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Manrope, sans-serif", "color": COLORS["text"]},
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
