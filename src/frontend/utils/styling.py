"""
styling.py – ShibaCV design system.
"""

from __future__ import annotations

import base64
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

COLORS: dict[str, str] = {
    "bg": "#F8F2E9",
    "surface": "#FFFFFF",
    "surface_warm": "#F7F0E6",
    "text": "#1A1007",
    "muted": "#7A6658",
    "border": "#E5D8CC",
    "accent": "#7A3820",
    "accent_mid": "#D4741A",
    "accent_hover": "#622E18",
    "accent_light": "#F5E8DF",
    "good": "#2A7A50",
    "good_bg": "#E8F4ED",
    "good_border": "#B8D9C5",
    "warn": "#9A6020",
    "warn_bg": "#FDF3E0",
    "warn_border": "#E8CF9A",
    "bad": "#A03020",
    "bad_bg": "#FCEAE6",
}


def img_tag(filename: str, style: str = "width:100%;height:auto;display:block") -> str:
    """Trả về <img> base64 để nhúng trực tiếp vào st.markdown."""
    path = ASSETS_DIR / filename
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = path.suffix.lstrip(".")
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    return f'<img src="data:{mime};base64,{b64}" style="{style}">'


_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@400;500;600;700&display=swap');

:root {{
  --bg: {COLORS['bg']};
  --surface: {COLORS['surface']};
  --surface-warm: {COLORS['surface_warm']};
  --text: {COLORS['text']};
  --muted: {COLORS['muted']};
  --border: {COLORS['border']};
  --accent: {COLORS['accent']};
  --accent-mid: {COLORS['accent_mid']};
  --accent-hover: {COLORS['accent_hover']};
  --accent-light: {COLORS['accent_light']};
  --good: {COLORS['good']};
  --good-bg: {COLORS['good_bg']};
  --good-border: {COLORS['good_border']};
  --warn: {COLORS['warn']};
  --warn-bg: {COLORS['warn_bg']};
  --warn-border: {COLORS['warn_border']};
  --bad: {COLORS['bad']};
  --bad-bg: {COLORS['bad_bg']};
  --radius-card: 18px;
  --shadow-card: 0 4px 24px rgba(80,45,20,0.08);
  --shadow-hover: 0 8px 32px rgba(80,45,20,0.14);
}}

/* ─── Hide Streamlit chrome ─────────────────────────── */
#MainMenu, footer, [data-testid="stDecoration"],
[data-testid="stToolbar"], header, [data-testid="stSidebarNav"]
{{ display: none !important; }}

/* ─── Base ──────────────────────────────────────────── */
html, body {{ font-family: 'Inter', system-ui, sans-serif; background: var(--bg); }}
.stApp {{ background: var(--bg) !important; color: var(--text); }}
.block-container {{ padding-top: 1.8rem !important; padding-bottom: 5rem; max-width: 1200px; }}
h1, h2, h3 {{ font-family: 'Crimson Pro', Georgia, serif; color: var(--text); letter-spacing: -0.01em; }}
p, .stMarkdown p {{ color: var(--text); }}

/* ─── Buttons ───────────────────────────────────────── */
.stButton > button, .stFormSubmitButton > button {{
  background: var(--accent) !important; color: #fff !important;
  border: none !important; border-radius: 999px !important;
  font-family: 'Inter', sans-serif !important; font-size: 0.97rem !important;
  font-weight: 600 !important; padding: 0.68rem 1.9rem !important;
  box-shadow: 0 4px 16px rgba(122,56,32,0.3) !important;
  transition: background 0.15s ease, transform 0.1s ease, box-shadow 0.15s ease !important;
}}
.stButton > button:hover, .stFormSubmitButton > button:hover {{
  background: var(--accent-hover) !important; color: #fff !important;
  transform: translateY(-2px) !important; box-shadow: 0 8px 22px rgba(122,56,32,0.38) !important;
}}
.stButton > button:active {{ transform: translateY(0) !important; }}

/* ─── File uploader ─────────────────────────────────── */
[data-testid="stFileUploaderDropzone"] {{
  border: 2px dashed var(--border) !important; border-radius: 14px !important;
  background: #FAFAF8 !important; min-height: 130px;
}}

/* ─── Input / Select ────────────────────────────────── */
[data-testid="stTextInput"] input, .stTextInput input {{
  border: 1.5px solid var(--border) !important; border-radius: 12px !important;
  background: var(--surface) !important; color: var(--text) !important;
}}
[data-testid="stTextInput"] input:focus {{
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px rgba(122,56,32,0.1) !important;
}}
div[data-baseweb="select"] > div {{
  border: 1.5px solid var(--border) !important; border-radius: 12px !important;
  background: var(--surface) !important;
}}

/* ─── Landing hero ──────────────────────────────────── */
.hero-eyebrow {{
  width: 38px; height: 5px; background: var(--accent);
  border-radius: 3px; margin-bottom: 1.1rem;
}}
.hero-title {{
  font-family: 'Crimson Pro', Georgia, serif;
  font-size: 2.9rem; font-weight: 700; line-height: 1.15; color: var(--text); margin: 0;
}}
.hero-title .accent {{ color: var(--accent); }}
.hero-subtitle {{
  font-size: 1rem; color: var(--muted); line-height: 1.65;
  margin: 0.9rem 0 2rem; max-width: 46ch;
}}
.hero-img-card {{
  background: #F2EAE0; border-radius: 22px; overflow: hidden;
  padding: 1.2rem; display: flex; align-items: center; justify-content: center;
}}
.hero-img-card img {{ border-radius: 14px; width: 100%; height: auto; display: block; }}

/* ─── Upload page ───────────────────────────────────── */
.page-h1 {{
  font-family: 'Crimson Pro', Georgia, serif;
  font-size: 2rem; font-weight: 700; color: var(--text); margin: 0 0 0.25rem;
}}
.page-h1-sub {{ font-size: 0.95rem; color: var(--muted); margin: 0 0 1.6rem; }}
.quick-tags {{ display: flex; flex-wrap: wrap; gap: 0.45rem; margin: 0.5rem 0 0.2rem; }}
.qtag {{
  background: #F0EBE3; color: var(--muted);
  border: 1.5px solid var(--border); border-radius: 999px;
  padding: 0.3rem 0.85rem; font-size: 0.82rem; font-weight: 500;
}}
.shiba-ready-card {{
  background: var(--surface-warm); border: 1.5px solid var(--border);
  border-radius: 16px; padding: 1.2rem 1.4rem; margin-top: 0.8rem; text-align: center;
}}
.shiba-ready-card .rct-label {{
  font-family: 'Crimson Pro', Georgia, serif; font-size: 1.14rem;
  font-weight: 700; color: var(--accent); margin: 0 0 0.45rem;
}}
.shiba-ready-card .rct-quote {{ font-size: 0.88rem; color: var(--muted); line-height: 1.58; }}
.stats-row {{ display: flex; gap: 0.9rem; margin-top: 1rem; }}
.stat-chip {{
  flex: 1; background: var(--surface); border: 1.5px solid var(--border);
  border-radius: 12px; padding: 0.8rem 0.9rem; text-align: center;
}}
.stat-chip .s-icon {{ font-size: 1.1rem; }}
.stat-chip .s-main {{ font-weight: 700; color: var(--accent); font-size: 0.92rem; }}
.stat-chip .s-sub {{ font-size: 0.75rem; color: var(--muted); }}
.privacy-note {{ font-size: 0.78rem; color: var(--muted); text-align: center; margin-top: 0.6rem; }}

/* ─── Results page ──────────────────────────────────── */
.results-title {{
  font-family: 'Crimson Pro', Georgia, serif;
  font-size: 1.85rem; font-weight: 700; color: var(--text); margin: 0 0 0.2rem;
}}
.results-sub {{ font-size: 0.9rem; color: var(--muted); }}
.score-area {{ display: flex; flex-direction: column; align-items: center; gap: 0.7rem; padding-top: 0.5rem; }}
.score-ring {{ width: 200px; height: 200px; }}
.score-verdict {{
  font-family: 'Crimson Pro', Georgia, serif; font-size: 1.65rem;
  font-weight: 700; color: var(--accent); text-align: center;
}}
.score-desc {{ font-size: 0.9rem; color: var(--muted); text-align: center; max-width: 34ch; line-height: 1.55; }}
.shiba-rec-card {{
  background: var(--surface-warm); border: 1.5px solid var(--border);
  border-radius: 16px; padding: 1.2rem 1.4rem; margin-top: 0.9rem;
}}
.shiba-rec-card .rec-badge {{
  display: inline-block; background: var(--accent); color: #fff;
  font-size: 0.65rem; font-weight: 700; letter-spacing: 0.1em;
  padding: 0.2rem 0.65rem; border-radius: 999px; margin-bottom: 0.65rem;
}}
.shiba-rec-card .rec-quote {{ font-size: 0.89rem; color: var(--text); line-height: 1.6; font-style: italic; }}
.metric-card-v2 {{
  background: var(--surface); border: 1.5px solid var(--border);
  border-radius: var(--radius-card); padding: 1.3rem 1.5rem;
  box-shadow: var(--shadow-card); height: 100%;
  transition: transform 0.18s, box-shadow 0.18s;
}}
.metric-card-v2:hover {{ transform: translateY(-3px); box-shadow: var(--shadow-hover); }}
.metric-card-v2 .mc-icon {{ font-size: 1.5rem; margin-bottom: 0.4rem; }}
.metric-card-v2 .mc-label {{
  font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.07em; color: var(--muted);
}}
.metric-card-v2 .mc-value {{
  font-family: 'Crimson Pro', Georgia, serif; font-size: 2.5rem;
  font-weight: 700; line-height: 1.1; margin: 0.15rem 0;
}}
.metric-card-v2 .mc-value span {{ font-size: 1.1rem; color: var(--muted); }}
.metric-card-v2 .mc-track {{
  height: 8px; background: #EDE4D8; border-radius: 999px; margin-top: 0.9rem; overflow: hidden;
}}
.metric-card-v2 .mc-fill {{ height: 100%; border-radius: 999px; }}

/* ─── Skill badges ──────────────────────────────────── */
.badge-wrap {{ display: flex; flex-wrap: wrap; gap: 0.42rem; }}
.badge {{
  display: inline-block; padding: 0.3rem 0.82rem; border-radius: 999px;
  font-size: 0.82rem; font-weight: 500; border: 1px solid transparent;
  animation: pop 0.38s ease both; transition: transform 0.12s;
}}
.badge:hover {{ transform: translateY(-1px); }}
.badge-matched {{ background: var(--good-bg); color: var(--good); border-color: var(--good-border); }}
.badge-missing {{ background: var(--warn-bg); color: var(--warn); border-color: var(--warn-border); }}
.badge-muted {{ background: #F0EBE3; color: var(--muted); border-color: var(--border); }}

/* ─── Skill section card ────────────────────────────── */
.skill-card {{
  background: var(--surface); border: 1.5px solid var(--border);
  border-radius: var(--radius-card); padding: 1.4rem 1.5rem;
  box-shadow: var(--shadow-card); height: 100%;
}}
.skill-card-title {{
  font-size: 1rem; font-weight: 700; color: var(--text); margin: 0 0 1rem;
}}
.skill-sub-label {{
  font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.08em; margin: 0.9rem 0 0.55rem;
}}
.skill-sub-label.green {{ color: var(--good); }}
.skill-sub-label.amber {{ color: var(--warn); }}

/* ─── AI Rec section ────────────────────────────────── */
.ai-rec-wrap {{
  background: var(--surface); border: 1.5px solid var(--border);
  border-radius: var(--radius-card); padding: 1.5rem 1.7rem;
  box-shadow: var(--shadow-card);
}}
.ai-rec-heading {{
  font-family: 'Crimson Pro', Georgia, serif; font-size: 1.25rem;
  font-weight: 700; color: var(--accent); margin: 0 0 1rem;
}}
.ai-tip {{
  background: var(--accent-light); border-radius: 10px;
  padding: 0.65rem 0.95rem; font-size: 0.84rem; color: var(--muted); margin-top: 1rem;
}}

/* ─── Section heading ───────────────────────────────── */
.section-h {{
  font-family: 'Crimson Pro', Georgia, serif; font-size: 1.35rem;
  font-weight: 700; color: var(--text); margin: 1.8rem 0 1rem 0;
}}
.hint {{ color: var(--muted); font-size: 0.9rem; }}

/* ─── Footer ────────────────────────────────────────── */
.shiba-footer {{
  background: var(--bg); border-top: 1.5px solid var(--border);
  padding: 2.2rem 0; margin-top: 3.5rem;
}}
.shiba-footer .f-logo {{
  font-weight: 700; font-size: 1.05rem; color: var(--accent);
}}
.shiba-footer .f-desc {{ font-size: 0.82rem; color: var(--muted); margin-top: 0.35rem; }}
.shiba-footer .f-links {{ display: flex; gap: 1.6rem; font-size: 0.84rem; }}
.shiba-footer .f-links a {{ color: var(--muted); text-decoration: none; }}
.shiba-footer .f-copy {{ font-size: 0.76rem; color: var(--muted); opacity: 0.65; margin-top: 1rem; }}

/* ─── Alert ─────────────────────────────────────────── */
[data-testid="stAlert"] {{ border-radius: 12px; }}

/* ─── Animations ────────────────────────────────────── */
@keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(14px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes pop {{ from {{ opacity: 0; transform: scale(0.85); }} to {{ opacity: 1; transform: none; }} }}

@media (prefers-reduced-motion: reduce) {{
  .badge {{ animation: none !important; }}
}}
</style>
"""


def inject_css() -> None:
    import streamlit as st
    st.markdown(_CSS, unsafe_allow_html=True)


def render_footer() -> None:
    import streamlit as st
    st.markdown(
        """
        <div class="shiba-footer">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:1.5rem">
            <div>
              <div class="f-logo">🐾 ShibaCV</div>
              <div class="f-desc">Nền tảng AI hàng đầu trong lĩnh vực<br>tuyển dụng và phát triển nghề nghiệp.</div>
              <div class="f-copy">© 2024 ShibaCV AI. Built with precision and treats.</div>
            </div>
            <div class="f-links" style="padding-top:0.3rem">
              <a href="#">Terms</a><a href="#">Privacy</a><a href="#">Support</a><a href="#">Contact</a>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def score_color(score_0_1: float) -> str:
    pct = score_0_1 * 100
    if pct < 40:
        return COLORS["bad"]
    if pct < 70:
        return COLORS["warn"]
    return COLORS["good"]
