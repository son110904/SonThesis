"""
score_gauge.py – Vòng tròn Match Score bằng SVG (không cần Plotly).
"""

from __future__ import annotations

import math

from src.frontend.utils.styling import COLORS


def render_match_gauge(match_score_0_1: float) -> None:
    import streamlit as st

    pct = round(min(max(match_score_0_1, 0.0), 1.0) * 100, 1)
    r = 82
    cx = cy = 110
    circumference = 2 * math.pi * r  # ≈ 515.22

    if pct >= 70:
        arc_color = "#D4741A"
        glow_color = "rgba(212,116,26,0.18)"
    elif pct >= 40:
        arc_color = "#D4741A"
        glow_color = "rgba(212,116,26,0.15)"
    else:
        arc_color = COLORS["bad"]
        glow_color = "rgba(160,48,32,0.15)"

    dash_len = circumference * (pct / 100)
    dash_gap = circumference - dash_len

    svg = f"""
<svg viewBox="0 0 220 220" xmlns="http://www.w3.org/2000/svg" class="score-ring">
  <!-- soft outer glow -->
  <circle cx="{cx}" cy="{cy}" r="{r + 6}" fill="{glow_color}"/>
  <!-- track -->
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none"
          stroke="#EDE4D8" stroke-width="18" stroke-linecap="round"/>
  <!-- arc -->
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none"
          stroke="{arc_color}" stroke-width="18" stroke-linecap="round"
          stroke-dasharray="{dash_len:.2f} {dash_gap:.2f}"
          stroke-dashoffset="0"
          transform="rotate(-90 {cx} {cy})"/>
  <!-- percent text -->
  <text x="{cx}" y="{cy - 8}" text-anchor="middle" dominant-baseline="middle"
        font-family="'Crimson Pro', Georgia, serif" font-size="42" font-weight="700"
        fill="{COLORS['text']}">{pct:g}%</text>
  <!-- label -->
  <text x="{cx}" y="{cy + 24}" text-anchor="middle" dominant-baseline="middle"
        font-family="'Inter', sans-serif" font-size="11" font-weight="600"
        fill="{COLORS['muted']}" letter-spacing="2">MATCH SCORE</text>
</svg>
"""
    st.markdown(f'<div class="score-area">{svg}</div>', unsafe_allow_html=True)
