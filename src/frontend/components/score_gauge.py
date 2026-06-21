"""
score_gauge.py – Vòng tròn Match Score bằng SVG (gradient stroke, không cần Plotly).
"""

from __future__ import annotations

import math

from src.frontend.utils.styling import COLORS


def render_match_gauge(match_score_0_1: float) -> None:
    import streamlit as st

    pct = round(min(max(match_score_0_1, 0.0), 1.0) * 100, 1)
    r = 84
    cx = cy = 110
    circumference = 2 * math.pi * r

    # gradient endpoints theo mức điểm
    if pct >= 70:
        c0, c1 = "#D4741A", "#8A3F22"
    elif pct >= 40:
        c0, c1 = "#E0902F", "#B85427"
    else:
        c0, c1 = "#C9603A", COLORS["bad"]

    dash_len = circumference * (pct / 100)
    dash_gap = circumference - dash_len

    svg = f"""
<svg viewBox="0 0 220 220" xmlns="http://www.w3.org/2000/svg" class="score-ring">
  <defs>
    <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{c0}"/>
      <stop offset="100%" stop-color="{c1}"/>
    </linearGradient>
  </defs>
  <!-- track -->
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none"
          stroke="#EFE6DA" stroke-width="16" stroke-linecap="round"/>
  <!-- arc -->
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none"
          stroke="url(#gaugeGrad)" stroke-width="16" stroke-linecap="round"
          stroke-dasharray="{dash_len:.2f} {dash_gap:.2f}"
          stroke-dashoffset="0"
          transform="rotate(-90 {cx} {cy})"/>
  <!-- percent text -->
  <text x="{cx}" y="{cy - 6}" text-anchor="middle" dominant-baseline="middle"
        font-family="'Crimson Pro', Georgia, serif" font-size="46" font-weight="700"
        letter-spacing="-1" fill="{COLORS['text']}">{pct:g}%</text>
  <!-- label -->
  <text x="{cx}" y="{cy + 26}" text-anchor="middle" dominant-baseline="middle"
        font-family="'Inter', sans-serif" font-size="11" font-weight="700"
        fill="{COLORS['muted']}" letter-spacing="2.5">MATCH SCORE</text>
</svg>
"""
    st.markdown(f'<div class="score-area">{svg}</div>', unsafe_allow_html=True)
