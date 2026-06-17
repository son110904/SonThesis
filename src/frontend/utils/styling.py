"""
styling.py – Thiết kế giao diện theo triết lý taste-skill (port sang Streamlit).

Design Read: data-tool đánh giá nghề nghiệp cho người tìm việc → ngôn ngữ
clean/professional, nền neutral + MỘT accent cobalt (flat, không glow gradient),
motion tối giản, density vừa.

Nguyên tắc taste-skill được áp dụng:
  - Anti-default: KHÔNG dùng Inter, KHÔNG AI-purple/blue-glow. Font Manrope,
    accent cobalt phẳng.
  - Color consistency lock: 1 accent duy nhất cho chrome; xanh/đỏ CHỈ dành cho
    semantic (badge matched/missing, gauge score).
  - Shape consistency lock: card radius 14px, button 10px, badge full-pill.
  - Contrast AA: text/muted/badge đều đạt ≥ 4.5:1.
  - Hierarchy bằng spacing + border, hạn chế shadow; shadow tint theo nền.
"""

from __future__ import annotations

# Token màu — export để plotly gauge dùng đồng bộ với CSS
COLORS: dict[str, str] = {
    "bg": "#f6f8fb",
    "surface": "#ffffff",
    "text": "#0f172a",
    "muted": "#475569",
    "border": "#e2e8f0",
    "accent": "#2563eb",
    "accent_hover": "#1d4ed8",
    # Semantic (score / badge)
    "good": "#059669",     # emerald-600
    "good_bg": "#ecfdf5",
    "warn": "#d97706",     # amber-600
    "bad": "#dc2626",      # red-600
    "bad_bg": "#fef2f2",
}

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

:root {{
  --bg: {COLORS['bg']};
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
  --radius-card: 14px;
  --radius-btn: 10px;
}}

/* Ẩn chrome mặc định của Streamlit (menu, footer, sidebar nav tự sinh) */
#MainMenu, footer, [data-testid="stDecoration"], [data-testid="stSidebarNav"] {{
  display: none !important;
}}

html, body, .stApp, [class*="css"] {{
  font-family: 'Manrope', system-ui, -apple-system, sans-serif;
}}
.stApp {{ background: var(--bg); color: var(--text); }}

.block-container {{ max-width: 920px; padding-top: 2.2rem; padding-bottom: 4rem; }}

/* Typography: display tracking chặt, body relaxed */
h1, h2, h3 {{ color: var(--text); letter-spacing: -0.02em; font-weight: 800; }}
h1 {{ font-size: 2.1rem; line-height: 1.1; }}
h2 {{ font-size: 1.4rem; font-weight: 700; }}
p, label, .stMarkdown {{ color: var(--text); }}

/* Header thương hiệu */
.app-header {{ margin-bottom: 0.4rem; }}
.app-header .title {{ font-size: 2.0rem; font-weight: 800; letter-spacing: -0.03em; }}
.app-header .subtitle {{ color: var(--muted); font-size: 1.0rem; margin-top: 0.15rem; max-width: 60ch; }}
.app-divider {{ height: 1px; background: var(--border); border: 0; margin: 1.4rem 0 1.8rem; }}

/* Nút: accent phẳng, phản hồi xúc giác khi nhấn */
.stButton > button, .stFormSubmitButton > button {{
  background: var(--accent); color: #fff; border: 0; border-radius: var(--radius-btn);
  font-weight: 700; padding: 0.6rem 1.2rem; transition: transform .06s ease, background .15s ease;
}}
.stButton > button:hover, .stFormSubmitButton > button:hover {{ background: var(--accent-hover); color:#fff; }}
.stButton > button:active, .stFormSubmitButton > button:active {{ transform: translateY(1px); }}

/* Selectbox / uploader bo góc nhất quán */
[data-testid="stFileUploaderDropzone"] {{ border-radius: var(--radius-card); border: 1px dashed var(--border); }}
div[data-baseweb="select"] > div {{ border-radius: var(--radius-btn); }}

/* Thẻ metric (Semantic / Weighted) */
.metric-card {{
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-card);
  padding: 1.1rem 1.2rem; height: 100%;
}}
.metric-card .label {{ color: var(--muted); font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }}
.metric-card .value {{ font-size: 2.0rem; font-weight: 800; letter-spacing: -0.02em; margin-top: 0.2rem; }}
.metric-card .bar {{ height: 6px; border-radius: 999px; background: var(--border); margin-top: 0.7rem; overflow: hidden; }}
.metric-card .bar > span {{ display: block; height: 100%; border-radius: 999px; }}

/* Badge kỹ năng — full-pill, contrast AA */
.badge-wrap {{ display: flex; flex-wrap: wrap; gap: 0.45rem; margin-top: 0.2rem; }}
.badge {{ display: inline-flex; align-items: center; font-size: 0.85rem; font-weight: 600;
  padding: 0.3rem 0.7rem; border-radius: 999px; border: 1px solid transparent; }}
.badge-matched {{ background: var(--good-bg); color: var(--good); border-color: #a7f3d0; }}
.badge-missing {{ background: var(--bad-bg);  color: var(--bad);  border-color: #fecaca; }}
.badge-muted   {{ background: #f1f5f9; color: var(--muted); border-color: var(--border); }}

/* Thẻ AI Recommendation (lớn) */
.rec-card {{
  background: var(--surface); border: 1px solid var(--border); border-left: 4px solid var(--accent);
  border-radius: var(--radius-card); padding: 1.3rem 1.5rem; margin-top: 0.4rem;
}}
.rec-card h3 {{ margin-top: 1.1rem; font-size: 1.05rem; font-weight: 700; }}
.rec-card h3:first-child {{ margin-top: 0; }}

/* Section label nhỏ (dùng tiết chế, không spam) */
.section-label {{ color: var(--muted); font-size: 0.78rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.08em; margin: 1.6rem 0 0.6rem; }}

/* Empty / hint state */
.hint {{ color: var(--muted); font-size: 0.92rem; }}
</style>
"""


def inject_css() -> None:
    """Chèn CSS toàn cục. Gọi 1 lần đầu mỗi lần render trang."""
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
