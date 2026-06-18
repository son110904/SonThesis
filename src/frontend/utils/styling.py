"""
styling.py – Giao diện ấm, có chủ đích (rose beige + mascot shiba + motion).

Design Read: tool đánh giá nghề nghiệp mang cá tính thân thiện/ấm áp — nền
rose-beige, một accent terracotta (ăn với màu lông shiba), font serif Crimson Pro
(có subset tiếng Việt → hiển thị dấu chuẩn) thay font "AI" mặc định, chuyển động
nhẹ ở section/card + một chú shiba chạy ngang background.

Nguyên tắc taste-skill vẫn giữ:
  - 1 accent duy nhất cho chrome; xanh/đỏ chỉ cho semantic (badge, score).
  - Palette warm harmonised (rose beige + terracotta + warm neutrals), không trộn
    warm/cool. Đây là brand choice của user nên override "anti-beige" mặc định.
  - Shape lock: card 16px, button 12px, badge pill.
  - Contrast AA cho text/badge.
  - Motion có chủ đích: entrance fade-up + hover lift; shiba là điểm nhấn vui.
"""

from __future__ import annotations

import base64

# Token màu — export để plotly gauge & components dùng đồng bộ
COLORS: dict[str, str] = {
    "bg": "#f3ddd4",        # rose beige
    "bg2": "#ecd0c5",       # rose beige đậm hơn (gradient)
    "surface": "#fff8f3",   # warm white
    "text": "#3c2b25",      # warm dark brown
    "muted": "#8c7064",     # warm taupe
    "border": "#e6cdc1",
    "accent": "#c2562f",    # terracotta
    "accent_hover": "#a5441f",
    # Semantic (warm-toned để hợp palette)
    "good": "#2f7d50",
    "good_bg": "#e7f1e8",
    "warn": "#c07d18",
    "bad": "#b23a2a",
    "bad_bg": "#f7e3df",
}

# ── SVG shiba (nhìn nghiêng, hướng phải) — chân trước/sau animate để như đang chạy ──
_SHIBA_SVG = """
<svg class="shiba-svg" viewBox="0 0 120 88" xmlns="http://www.w3.org/2000/svg">
  <!-- đuôi cuộn -->
  <path d="M16 44 C2 40 4 22 18 26 C10 30 12 40 22 42 Z" fill="#e8a45c" stroke="#5a3d2b" stroke-width="2.5" stroke-linejoin="round"/>
  <!-- chân sau -->
  <g class="leg leg-back">
    <rect x="30" y="54" width="9" height="22" rx="4" fill="#d98a3f" stroke="#5a3d2b" stroke-width="2.5"/>
  </g>
  <g class="leg leg-back2">
    <rect x="44" y="54" width="9" height="22" rx="4" fill="#e8a45c" stroke="#5a3d2b" stroke-width="2.5"/>
  </g>
  <!-- chân trước -->
  <g class="leg leg-front2">
    <rect x="74" y="54" width="9" height="22" rx="4" fill="#d98a3f" stroke="#5a3d2b" stroke-width="2.5"/>
  </g>
  <g class="leg leg-front">
    <rect x="86" y="54" width="9" height="22" rx="4" fill="#e8a45c" stroke="#5a3d2b" stroke-width="2.5"/>
  </g>
  <!-- thân -->
  <ellipse cx="56" cy="46" rx="38" ry="20" fill="#e8a45c" stroke="#5a3d2b" stroke-width="2.5"/>
  <path d="M30 52 Q56 64 84 52 Q56 60 30 52 Z" fill="#f6e7d4"/>
  <!-- đầu -->
  <circle cx="92" cy="36" r="20" fill="#e8a45c" stroke="#5a3d2b" stroke-width="2.5"/>
  <!-- tai -->
  <path d="M80 20 L86 6 L94 22 Z" fill="#e8a45c" stroke="#5a3d2b" stroke-width="2.5" stroke-linejoin="round"/>
  <path d="M100 22 L106 6 L112 22 Z" fill="#e8a45c" stroke="#5a3d2b" stroke-width="2.5" stroke-linejoin="round"/>
  <!-- mặt cream -->
  <path d="M92 30 Q104 34 104 44 Q98 52 92 52 Q88 44 88 38 Z" fill="#f6e7d4"/>
  <!-- mõm + mũi -->
  <circle cx="110" cy="42" r="4.5" fill="#5a3d2b"/>
  <!-- mắt -->
  <circle cx="96" cy="34" r="3" fill="#3a2620"/>
  <!-- má -->
  <ellipse cx="90" cy="44" rx="4" ry="3" fill="#e58b6b" opacity="0.55"/>
</svg>
"""

# Nhúng dạng base64 background-image để KHÔNG bị sanitizer của st.markdown lọc mất.
_SHIBA_B64 = base64.b64encode(_SHIBA_SVG.strip().encode("utf-8")).decode("ascii")

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,500;0,600;0,700;1,400;1,600&display=swap');

:root {{
  --bg: {COLORS['bg']};
  --bg2: {COLORS['bg2']};
  --surface: {COLORS['surface']};
  --text: {COLORS['text']};
  --muted: {COLORS['muted']};
  --border: {COLORS['border']};
  --accent: {COLORS['accent']};
  --accent-hover: {COLORS['accent_hover']};
  --good: {COLORS['good']};
  --good-bg: {COLORS['good_bg']};
  --bad: {COLORS['bad']};
  --bad-bg: {COLORS['bad_bg']};
  --radius-card: 16px;
  --radius-btn: 12px;
}}

#MainMenu, footer, [data-testid="stDecoration"], [data-testid="stSidebarNav"] {{ display: none !important; }}

html, body, .stApp, [class*="css"] {{ font-family: 'Crimson Pro', Georgia, 'Times New Roman', serif; }}

/* Nền rose beige ấm, gradient mềm */
.stApp {{
  color: var(--text);
  background:
    radial-gradient(1200px 600px at 85% -5%, #f7e6dd 0%, transparent 55%),
    radial-gradient(900px 500px at 0% 110%, #f0d3c7 0%, transparent 50%),
    linear-gradient(160deg, var(--bg) 0%, var(--bg2) 100%);
  background-attachment: fixed;
}}

.block-container {{ max-width: 940px; padding-top: 2.2rem; padding-bottom: 6rem; position: relative; z-index: 2; }}

/* Typography: heading serif Crimson Pro */
h1, h2, h3, .app-header .title {{ font-family: 'Crimson Pro', Georgia, serif; color: var(--text); letter-spacing: -0.01em; }}
h1 {{ font-size: 2.1rem; }}
p, label, .stMarkdown {{ color: var(--text); }}

/* Header */
.app-header {{ margin-bottom: 0.3rem; animation: fadeUp .5s ease both; }}
.app-header .title {{ font-size: 2.1rem; font-weight: 700; }}
.app-header .subtitle {{ color: var(--muted); font-size: 1.02rem; margin-top: 0.2rem; max-width: 60ch; }}
.app-divider {{ height: 1px; background: var(--border); border: 0; margin: 1.3rem 0 1.7rem; }}

/* Nút accent terracotta, bo tròn, có phản hồi nhấn */
.stButton > button, .stFormSubmitButton > button {{
  background: var(--accent); color: #fff; border: 0; border-radius: var(--radius-btn);
  font-family: 'Crimson Pro', Georgia, serif; font-weight: 600; padding: 0.6rem 1.3rem;
  box-shadow: 0 6px 16px -8px rgba(162,68,31,.7);
  transition: transform .08s ease, background .15s ease, box-shadow .15s ease;
}}
.stButton > button:hover, .stFormSubmitButton > button:hover {{
  background: var(--accent-hover); color:#fff; transform: translateY(-1px);
  box-shadow: 0 10px 22px -8px rgba(162,68,31,.75);
}}
.stButton > button:active, .stFormSubmitButton > button:active {{ transform: translateY(1px); }}

[data-testid="stFileUploaderDropzone"] {{ border-radius: var(--radius-card); border: 1.5px dashed var(--border); background: rgba(255,255,255,.45); }}
div[data-baseweb="select"] > div {{ border-radius: var(--radius-btn); background: var(--surface); }}

/* Thẻ — kính mờ ấm, hover nhấc nhẹ */
.metric-card {{
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-card);
  padding: 1.1rem 1.2rem; height: 100%;
  box-shadow: 0 10px 30px -22px rgba(90,61,43,.5);
  animation: fadeUp .55s ease both;
  transition: transform .18s ease, box-shadow .18s ease;
}}
.metric-card:hover {{ transform: translateY(-3px); box-shadow: 0 18px 38px -22px rgba(90,61,43,.55); }}
.metric-card .label {{ color: var(--muted); font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }}
.metric-card .value {{ font-family: 'Crimson Pro', Georgia, serif; font-size: 2.1rem; font-weight: 700; margin-top: 0.15rem; }}
.metric-card .bar {{ height: 7px; border-radius: 999px; background: #ecdcd3; margin-top: 0.7rem; overflow: hidden; }}
.metric-card .bar > span {{ display: block; height: 100%; border-radius: 999px; animation: growBar .8s cubic-bezier(.16,1,.3,1) both; }}

/* Badge pill */
.badge-wrap {{ display: flex; flex-wrap: wrap; gap: 0.45rem; margin-top: 0.2rem; }}
.badge {{ display: inline-flex; align-items: center; font-size: 0.86rem; font-weight: 700;
  padding: 0.32rem 0.75rem; border-radius: 999px; border: 1px solid transparent;
  animation: pop .4s ease both; transition: transform .12s ease; }}
.badge:hover {{ transform: translateY(-2px) scale(1.03); }}
.badge-matched {{ background: var(--good-bg); color: var(--good); border-color: #b9ddc1; }}
.badge-missing {{ background: var(--bad-bg);  color: var(--bad);  border-color: #efc4bc; }}
.badge-muted   {{ background: #f3e6de; color: var(--muted); border-color: var(--border); }}

/* Thẻ AI Recommendation */
.rec-card {{
  background: var(--surface); border: 1px solid var(--border); border-left: 5px solid var(--accent);
  border-radius: var(--radius-card); padding: 1.3rem 1.5rem; margin-top: 0.4rem;
  box-shadow: 0 12px 32px -22px rgba(90,61,43,.5); animation: fadeUp .6s ease both;
}}
.rec-card h3 {{ margin-top: 1.1rem; font-size: 1.08rem; font-weight: 600; }}
.rec-card h3:first-child {{ margin-top: 0; }}

/* Heading section (thân thiện, không phải eyebrow micro-label kiểu AI) */
.section-label {{ font-family: 'Crimson Pro', Georgia, serif; color: var(--text); font-size: 1.05rem;
  font-weight: 600; margin: 1.7rem 0 0.6rem; }}
.hint {{ color: var(--muted); font-size: 0.92rem; }}

/* Banner info ấm */
[data-testid="stAlert"] {{ border-radius: 12px; }}

/* ── Animations ───────────────────────────────────────────── */
@keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(14px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes pop {{ from {{ opacity: 0; transform: scale(.85); }} to {{ opacity: 1; transform: none; }} }}
@keyframes growBar {{ from {{ width: 0 !important; }} }}

/* ── Shiba chạy ngang background ───────────────────────────── */
.shiba {{
  position: fixed; bottom: 16px; left: 0; width: 92px; height: 70px; z-index: 1;
  pointer-events: none; will-change: transform;
  animation: shibaRun 14s linear infinite;
}}
.shiba .shiba-inner {{
  width: 100%; height: 100%;
  background: url("data:image/svg+xml;base64,{_SHIBA_B64}") no-repeat center / contain;
  filter: drop-shadow(0 8px 6px rgba(90,61,43,.25));
  animation: shibaBob .34s ease-in-out infinite;
}}

@keyframes shibaRun {{
  0%   {{ transform: translateX(-140px); }}
  100% {{ transform: translateX(calc(100vw + 60px)); }}
}}
@keyframes shibaBob {{ 0%,100% {{ transform: translateY(0) rotate(-1deg); }} 50% {{ transform: translateY(-6px) rotate(1deg); }} }}

@media (prefers-reduced-motion: reduce) {{
  .shiba, .shiba .shiba-inner {{ animation: none; }}
  .metric-card, .rec-card, .app-header, .badge {{ animation: none; }}
  .shiba {{ left: 24px; }}
}}
</style>

<div class="shiba"><div class="shiba-inner"></div></div>
"""


def inject_css() -> None:
    """Chèn CSS toàn cục + mascot shiba. Gọi 1 lần đầu mỗi lần render."""
    import streamlit as st

    st.markdown(_CSS, unsafe_allow_html=True)


def score_color(score_0_1: float) -> str:
    """Màu semantic theo điểm: <40 đỏ, 40-70 amber, >70 xanh."""
    pct = score_0_1 * 100
    if pct < 40:
        return COLORS["bad"]
    if pct < 70:
        return COLORS["warn"]
    return COLORS["good"]
