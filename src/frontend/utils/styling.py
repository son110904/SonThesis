"""
styling.py – ShibaCV design system.

Hệ thống ấm (rose-beige / terracotta) thể hiện ở mức premium: depth nhiều lớp,
highlight inset trên bề mặt, glow nền mềm, typography dùng DUY NHẤT Crimson Pro,
micro-motion tôn trọng prefers-reduced-motion.
"""

from __future__ import annotations

import base64
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

COLORS: dict[str, str] = {
    "bg": "#F8F2E9",
    "surface": "#FFFFFF",
    "surface_warm": "#FBF5EC",
    "text": "#241710",
    "muted": "#7A6658",
    "border": "#E7D9CB",
    "accent": "#8A3F22",
    "accent_mid": "#D4741A",
    "accent_hover": "#6E3019",
    "accent_light": "#F6E9DF",
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
@import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,500;0,600;0,700;1,400;1,600&display=swap');

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

  --accent-grad: linear-gradient(135deg, {COLORS['accent']} 0%, #B85427 55%, {COLORS['accent_mid']} 130%);
  --radius-card: 20px;
  --radius-sm: 12px;

  /* layered, hue-tinted depth */
  --shadow-card:
    0 1px 2px rgba(74,38,18,0.04),
    0 6px 16px -6px rgba(74,38,18,0.10),
    0 20px 44px -28px rgba(74,38,18,0.18);
  --shadow-hover:
    0 2px 4px rgba(74,38,18,0.06),
    0 14px 30px -8px rgba(74,38,18,0.16),
    0 32px 64px -32px rgba(74,38,18,0.26);
  --inset-hi: inset 0 1px 0 rgba(255,255,255,0.75);
  --cta-shadow: 0 6px 18px -4px rgba(138,63,34,0.45), 0 2px 6px rgba(138,63,34,0.25);
}}

/* ─── Hide Streamlit chrome ─────────────────────────── */
#MainMenu, footer, [data-testid="stDecoration"],
[data-testid="stToolbar"], header, [data-testid="stSidebarNav"]
{{ display: none !important; }}

/* ─── Streamlit layout normalization ────────────────── */
[data-testid="stHorizontalBlock"],
[data-testid="stColumns"] {{ align-items: flex-start !important; }}
[data-testid="stColumn"] > div > [data-testid="stVerticalBlock"] {{ row-gap: 0.65rem !important; }}
[data-testid="stForm"] > [data-testid="stVerticalBlock"] {{ row-gap: 0.5rem !important; }}
[data-testid="stMarkdownContainer"]:has(.score-area) {{ display: flex; justify-content: center; }}
[data-testid="element-container"]:has(div:empty) + [data-testid="element-container"] {{ margin-top: 0 !important; }}

/* ─── Base + warm ambient background ────────────────── */
/* Toàn bộ frontend dùng DUY NHẤT Crimson Pro (gồm cả widget Streamlit). */
html, body, .stApp, .stApp *,
button, input, select, textarea,
[data-baseweb], [data-baseweb] * {{
  font-family: 'Crimson Pro', Georgia, 'Times New Roman', serif !important;
}}
/* NHƯNG chừa lại font icon Material của Streamlit — nếu không, ligature
   ("upload", "arrow_right"...) sẽ hiện ra dưới dạng chữ thô. */
[data-testid="stIconMaterial"],
span[data-testid="stIconMaterial"],
.material-icons, .material-icons-outlined,
.material-symbols-rounded, .material-symbols-outlined,
span[class*="material-symbols"], i[class*="material"] {{
  font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
}}
html, body {{
  background: var(--bg);
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}}
.stApp {{
  color: var(--text);
  background:
    radial-gradient(1100px 560px at 18% 0%, #FFFBF4 0%, rgba(255,251,244,0) 60%),
    radial-gradient(900px 520px at 100% 0%, #FCEFE2 0%, rgba(252,239,226,0) 55%),
    var(--bg) !important;
  background-repeat: no-repeat;
}}
.block-container {{
  padding-top: 2.2rem !important;
  padding-bottom: 5rem !important;
  padding-left: 2.6rem !important;
  padding-right: 2.6rem !important;
  max-width: 1240px !important;
  margin-left: auto !important;
  margin-right: auto !important;
}}
h1, h2, h3 {{ font-family: 'Crimson Pro', Georgia, serif; color: var(--text); letter-spacing: -0.015em; }}
p, .stMarkdown p {{ color: var(--text); }}
::selection {{ background: rgba(212,116,26,0.22); }}

/* ─── Buttons (gradient CTA) ────────────────────────── */
.stButton > button, .stFormSubmitButton > button {{
  background: var(--accent-grad) !important; color: #fff !important;
  border: none !important; border-radius: 999px !important;
  font-family: 'Crimson Pro', Georgia, serif !important; font-size: 1.02rem !important;
  font-weight: 600 !important; letter-spacing: 0.005em !important;
  padding: 0.72rem 2rem !important;
  box-shadow: var(--cta-shadow) !important;
  transition: transform 0.16s cubic-bezier(0.16,1,0.3,1), box-shadow 0.18s ease, filter 0.18s ease !important;
}}
.stButton > button:hover, .stFormSubmitButton > button:hover {{
  color: #fff !important; filter: saturate(1.08) brightness(1.04) !important;
  transform: translateY(-2px) scale(1.02) !important;
  box-shadow: 0 14px 32px -6px rgba(138,63,34,0.5), 0 4px 10px rgba(138,63,34,0.3) !important;
}}
.stButton > button:active, .stFormSubmitButton > button:active {{ transform: translateY(0) scale(0.99) !important; }}
.stButton > button:focus-visible, .stFormSubmitButton > button:focus-visible {{
  outline: none !important; box-shadow: var(--cta-shadow), 0 0 0 3px rgba(212,116,26,0.35) !important;
}}

/* ─── File uploader ─────────────────────────────────── */
[data-testid="stFileUploaderDropzone"] {{
  border: 1.5px dashed var(--border) !important; border-radius: 16px !important;
  background: linear-gradient(180deg, #FFFDFA, #FBF4EC) !important;
  min-height: 142px; transition: border-color 0.18s ease, background 0.18s ease;
}}
[data-testid="stFileUploaderDropzone"]:hover {{
  border-color: var(--accent-mid) !important;
  background: linear-gradient(180deg, #FFFDFA, #FBEFE3) !important;
}}

/* ─── Input / Select / Toggle ───────────────────────── */
[data-testid="stTextInput"] input, .stTextInput input {{
  border: 1.5px solid var(--border) !important; border-radius: var(--radius-sm) !important;
  background: var(--surface) !important; color: var(--text) !important;
}}
[data-testid="stTextInput"] input:focus {{
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px rgba(138,63,34,0.12) !important;
}}
div[data-baseweb="select"] > div {{
  border: 1.5px solid var(--border) !important; border-radius: var(--radius-sm) !important;
  background: var(--surface) !important; transition: border-color 0.18s ease, box-shadow 0.18s ease;
  min-height: 46px;
}}
div[data-baseweb="select"] > div:hover {{ border-color: var(--accent-mid) !important; }}
div[data-baseweb="select"] > div:focus-within {{
  border-color: var(--accent) !important; box-shadow: 0 0 0 3px rgba(138,63,34,0.12) !important;
}}

/* ─── Brand header (bấm để về trang chủ) ────────────── */
.st-key-brand_home {{ margin: -0.4rem 0 0; width: max-content; }}
.st-key-brand_home button {{
  background: transparent !important; color: var(--accent) !important;
  border: none !important; box-shadow: none !important;
  padding: 0.15rem 0.5rem 0.15rem 0 !important;
  font-size: 1.55rem !important; font-weight: 700 !important;
  letter-spacing: -0.012em !important; border-radius: 10px !important;
  transition: color 0.16s ease, transform 0.16s ease !important;
}}
.st-key-brand_home button:hover {{
  color: var(--accent-hover) !important; background: transparent !important;
  filter: none !important; transform: translateY(-1px) !important; box-shadow: none !important;
}}
.st-key-brand_home button:active {{ transform: none !important; }}
.st-key-brand_home button:focus-visible {{
  outline: none !important; box-shadow: 0 0 0 3px rgba(212,116,26,0.28) !important;
}}
.shiba-nav-divider {{
  height: 1px; background: linear-gradient(90deg, var(--border), transparent);
  margin: 0.35rem 0 1.2rem;
}}

/* ─── Landing hero ──────────────────────────────────── */
.hero-eyebrow {{
  display: inline-flex; align-items: center; gap: 0.5rem;
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase;
  color: var(--accent); margin-bottom: 1.2rem;
}}
.hero-eyebrow::before {{
  content: ""; width: 30px; height: 3px; border-radius: 3px; background: var(--accent-grad);
}}
.hero-title {{
  font-family: 'Crimson Pro', Georgia, serif;
  font-size: clamp(2.6rem, 4.2vw, 3.5rem); font-weight: 700; line-height: 1.08;
  color: var(--text); margin: 0; letter-spacing: -0.02em;
}}
.hero-title .accent {{
  background: var(--accent-grad); -webkit-background-clip: text;
  background-clip: text; -webkit-text-fill-color: transparent;
}}
.hero-subtitle {{
  font-size: 1.05rem; color: var(--muted); line-height: 1.7;
  margin: 1.1rem 0 2rem; max-width: 46ch;
}}
.hero-img-card {{
  position: relative; border-radius: 26px; overflow: hidden;
  padding: 2rem 2.2rem; display: flex; align-items: center; justify-content: center;
  min-height: 360px;
  background:
    radial-gradient(120% 80% at 50% 35%, #FCEEDF 0%, #F2E5D8 70%, #EEDFD0 100%);
  box-shadow: var(--shadow-card), var(--inset-hi);
  border: 1px solid rgba(231,217,203,0.8);
}}
.hero-img-card::after {{
  content: ""; position: absolute; inset: 0; pointer-events: none;
  background: radial-gradient(62% 50% at 50% 45%, rgba(212,116,26,0.12), transparent 70%);
}}
.hero-img-card img {{
  position: relative; z-index: 1;
  width: 100%; height: auto; display: block; max-width: 100%;
  filter: drop-shadow(0 22px 30px rgba(74,38,18,0.24));
}}
/* Ảnh shiba (đã tách nền) thả trôi — drop-shadow theo viền alpha */
.shiba-float {{
  filter: drop-shadow(0 16px 26px rgba(74,38,18,0.20));
}}

/* ─── Upload page ───────────────────────────────────── */
.page-h1 {{
  font-family: 'Crimson Pro', Georgia, serif;
  font-size: clamp(1.9rem, 3vw, 2.4rem); font-weight: 700; color: var(--text);
  margin: 0 0 0.3rem; letter-spacing: -0.018em; line-height: 1.12;
}}
.page-h1-sub {{ font-size: 1rem; color: var(--muted); margin: 0 0 1.7rem; line-height: 1.6; max-width: 52ch; }}
.shiba-ready-card {{
  background: linear-gradient(180deg, var(--surface), var(--surface-warm));
  border: 1px solid var(--border); border-radius: 18px;
  padding: 1.3rem 1.5rem; margin-top: 1rem; text-align: center;
  box-shadow: var(--shadow-card), var(--inset-hi);
}}
.shiba-ready-card .rct-label {{
  font-family: 'Crimson Pro', Georgia, serif; font-size: 1.18rem;
  font-weight: 700; color: var(--accent); margin: 0 0 0.5rem;
}}
.shiba-ready-card .rct-quote {{ font-size: 0.9rem; color: var(--muted); line-height: 1.62; font-style: italic; }}
.stats-row {{ display: flex; gap: 0.9rem; margin-top: 1rem; }}
.stat-chip {{
  flex: 1; background: var(--surface); border: 1px solid var(--border);
  border-radius: 14px; padding: 0.9rem 0.9rem; text-align: center;
  box-shadow: var(--shadow-card), var(--inset-hi);
  transition: transform 0.18s cubic-bezier(0.16,1,0.3,1), box-shadow 0.18s ease;
}}
.stat-chip:hover {{ transform: translateY(-3px); box-shadow: var(--shadow-hover), var(--inset-hi); }}
.stat-chip .s-icon {{ font-size: 1.25rem; }}
.stat-chip .s-main {{ font-weight: 700; color: var(--accent); font-size: 0.95rem; margin-top: 0.15rem; }}
.stat-chip .s-sub {{ font-size: 0.76rem; color: var(--muted); margin-top: 0.1rem; }}
.privacy-note {{
  font-size: 0.8rem; color: var(--muted); text-align: center; margin-top: 0.7rem;
}}
.field-label {{
  display: flex; align-items: center; gap: 0.5rem; margin: 1.1rem 0 0.4rem;
  font-size: 0.9rem; font-weight: 600; color: var(--text);
}}
.field-label .fl-icon {{ color: var(--accent-mid); font-size: 0.95rem; }}

/* ─── Results page ──────────────────────────────────── */
.results-title {{
  font-family: 'Crimson Pro', Georgia, serif;
  font-size: clamp(1.9rem, 3vw, 2.3rem); font-weight: 700; color: var(--text);
  margin: 0 0 0.25rem; letter-spacing: -0.018em;
}}
.results-sub {{ font-size: 0.92rem; color: var(--muted); }}
.score-area {{ display: flex; flex-direction: column; align-items: center; gap: 0.6rem; padding-top: 0.4rem; }}
.score-ring {{ width: 210px; height: 210px; filter: drop-shadow(0 10px 22px rgba(138,63,34,0.14)); }}
.score-verdict {{
  font-family: 'Crimson Pro', Georgia, serif; font-size: 1.75rem;
  font-weight: 700; color: var(--accent); text-align: center; letter-spacing: -0.01em;
}}
.score-desc {{ font-size: 0.92rem; color: var(--muted); text-align: center; max-width: 36ch; line-height: 1.6; }}
.shiba-rec-card {{
  background: linear-gradient(180deg, var(--surface), var(--surface-warm));
  border: 1px solid var(--border); border-radius: 18px;
  padding: 1.3rem 1.5rem; margin-top: 0.9rem; box-shadow: var(--shadow-card), var(--inset-hi);
}}
.shiba-rec-card .rec-badge {{
  display: inline-block; background: var(--accent-grad); color: #fff;
  font-size: 0.64rem; font-weight: 700; letter-spacing: 0.12em;
  padding: 0.24rem 0.7rem; border-radius: 999px; margin-bottom: 0.7rem;
}}
.shiba-rec-card .rec-quote {{ font-size: 0.92rem; color: var(--text); line-height: 1.62; font-style: italic; }}

.metric-card-v2 {{
  position: relative; overflow: hidden;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-card); padding: 1.4rem 1.55rem;
  box-shadow: var(--shadow-card), var(--inset-hi); height: auto;
  transition: transform 0.2s cubic-bezier(0.16,1,0.3,1), box-shadow 0.2s ease;
}}
.metric-card-v2::before {{
  content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: var(--accent-grad); opacity: 0.85;
}}
.metric-card-v2:hover {{ transform: translateY(-4px); box-shadow: var(--shadow-hover), var(--inset-hi); }}
.metric-card-v2 .mc-icon {{ font-size: 1.55rem; margin-bottom: 0.45rem; }}
.metric-card-v2 .mc-label {{
  font-size: 0.74rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.08em; color: var(--muted);
}}
.metric-card-v2 .mc-value {{
  font-family: 'Crimson Pro', Georgia, serif; font-size: 2.7rem;
  font-weight: 700; line-height: 1.05; margin: 0.2rem 0; letter-spacing: -0.02em;
}}
.metric-card-v2 .mc-value span {{ font-size: 1.1rem; color: var(--muted); font-weight: 500; }}
.metric-card-v2 .mc-track {{
  height: 9px; background: #EFE6DA; border-radius: 999px; margin-top: 1rem; overflow: hidden;
}}
.metric-card-v2 .mc-fill {{ height: 100%; border-radius: 999px; transition: width 0.6s cubic-bezier(0.16,1,0.3,1); }}

/* ─── Skill badges ──────────────────────────────────── */
.badge-wrap {{ display: flex; flex-wrap: wrap; gap: 0.45rem; }}
.badge {{
  display: inline-block; padding: 0.34rem 0.85rem; border-radius: 999px;
  font-size: 0.82rem; font-weight: 600; border: 1px solid transparent;
  animation: pop 0.38s cubic-bezier(0.16,1,0.3,1) both; transition: transform 0.14s ease, box-shadow 0.14s ease;
}}
.badge:hover {{ transform: translateY(-2px); box-shadow: 0 4px 10px -2px rgba(74,38,18,0.18); }}
.badge-matched {{ background: var(--good-bg); color: var(--good); border-color: var(--good-border); }}
.badge-missing {{ background: var(--warn-bg); color: var(--warn); border-color: var(--warn-border); }}
.badge-muted {{ background: #F2EBE2; color: var(--muted); border-color: var(--border); }}

/* "+N kỹ năng khác" — nút bấm xổ ra phần dư (native <details>) */
.badge-more {{ margin-top: 0.55rem; }}
.badge-more > summary {{
  list-style: none; cursor: pointer; user-select: none; width: max-content;
  background: var(--accent-light); color: var(--accent); border-color: rgba(138,63,34,0.25);
}}
.badge-more > summary::-webkit-details-marker {{ display: none; }}
.badge-more > summary::before {{ content: "▸ "; font-size: 0.8em; }}
.badge-more[open] > summary::before {{ content: "▾ "; }}
.badge-more > summary:hover {{ background: #F1DCCB; box-shadow: 0 4px 10px -2px rgba(74,38,18,0.18); }}

/* ─── Skill section card ────────────────────────────── */
.skill-card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-card); padding: 1.5rem 1.6rem;
  box-shadow: var(--shadow-card), var(--inset-hi); height: auto;
}}
.skill-card-title {{
  font-family: 'Crimson Pro', Georgia, serif;
  font-size: 1.15rem; font-weight: 700; color: var(--text); margin: 0 0 0.9rem;
}}
.skill-sub-label {{
  font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.08em; margin: 0.9rem 0 0.6rem;
}}
.skill-sub-label.green {{ color: var(--good); }}
.skill-sub-label.amber {{ color: var(--warn); }}

/* ─── AI Rec section ────────────────────────────────── */
.ai-rec-wrap {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-card); padding: 1.6rem 1.8rem;
  box-shadow: var(--shadow-card), var(--inset-hi);
}}
.ai-rec-heading {{
  font-family: 'Crimson Pro', Georgia, serif; font-size: 1.3rem;
  font-weight: 700; color: var(--accent); margin: 0 0 1rem;
}}
.ai-tip {{
  background: var(--accent-light); border-radius: 12px;
  padding: 0.7rem 1rem; font-size: 0.85rem; color: var(--muted); margin-top: 1rem;
}}
.ai-rec-wrap h2, .ai-rec-wrap h3, .ai-rec-wrap h4 {{
  font-family: 'Crimson Pro', Georgia, serif; color: var(--accent);
  font-size: 1.1rem; font-weight: 700; margin: 1rem 0 0.4rem;
}}
.ai-rec-wrap ul {{ margin: 0.3rem 0 0.6rem 1.1rem; padding: 0; }}
.ai-rec-wrap li {{ font-size: 0.9rem; line-height: 1.65; margin: 0.25rem 0; color: var(--text); }}
.ai-rec-wrap p {{ font-size: 0.9rem; line-height: 1.7; color: var(--text); margin: 0.45rem 0; }}

/* ─── AI CV Review (đầu ra trung tâm) ───────────────── */
.rv-overall {{
  position: relative; overflow: hidden;
  background: linear-gradient(135deg, #FBEEE2 0%, var(--accent-light) 100%);
  border: 1px solid rgba(138,63,34,0.28);
  border-radius: var(--radius-card); padding: 1.5rem 1.7rem; margin-bottom: 1.1rem;
  box-shadow: var(--shadow-card), var(--inset-hi);
}}
.rv-overall::before {{
  content: ""; position: absolute; top: 0; left: 0; bottom: 0; width: 4px; background: var(--accent-grad);
}}
.rv-overall-label {{
  font-family: 'Crimson Pro', Georgia, serif; font-size: 1.2rem; font-weight: 700;
  color: var(--accent); margin-bottom: 0.55rem;
}}
.rv-overall-body {{ font-size: 0.98rem; line-height: 1.65; color: var(--text); }}
.rv-card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-card); padding: 1.25rem 1.45rem; margin-bottom: 1rem;
  box-shadow: var(--shadow-card), var(--inset-hi);
  transition: transform 0.18s cubic-bezier(0.16,1,0.3,1), box-shadow 0.18s ease;
}}
.rv-card:hover {{ transform: translateY(-3px); box-shadow: var(--shadow-hover), var(--inset-hi); }}
.rv-card-title {{
  font-family: 'Crimson Pro', Georgia, serif; font-weight: 700; font-size: 1.08rem; margin-bottom: 0.65rem;
}}
.rv-list {{ margin: 0; padding-left: 1.15rem; }}
.rv-list li {{ font-size: 0.91rem; line-height: 1.6; color: var(--text); margin-bottom: 0.4rem; }}
.rv-road-step {{ border-left: 3px solid var(--accent-mid); padding-left: 0.95rem; margin: 0.7rem 0; }}
.rv-road-head {{ font-weight: 600; font-size: 0.94rem; color: var(--text); margin-bottom: 0.3rem; }}
/* Các khối nhận xét xếp DỌC 1 cột, full-width; khung ôm sát nội dung. */
.rv-stack {{ display: flex; flex-direction: column; }}
.rv-stack .rv-card {{ margin-bottom: 1rem; }}

/* ─── Section heading ───────────────────────────────── */
.section-h {{
  font-family: 'Crimson Pro', Georgia, serif; font-size: 1.45rem;
  font-weight: 700; color: var(--text); margin: 2rem 0 1.05rem 0; letter-spacing: -0.012em;
  display: flex; align-items: center; gap: 0.55rem;
}}
.hint {{ color: var(--muted); font-size: 0.9rem; }}

/* ─── Expander polish ───────────────────────────────── */
[data-testid="stExpander"] details {{
  border: 1px solid var(--border) !important; border-radius: 16px !important;
  background: var(--surface) !important; box-shadow: var(--shadow-card);
  overflow: hidden;
}}
[data-testid="stExpander"] summary {{ font-weight: 600 !important; }}
[data-testid="stExpander"] summary:hover {{ color: var(--accent) !important; }}

/* ─── Footer ────────────────────────────────────────── */
.shiba-footer {{
  border-top: 1px solid var(--border);
  padding: 2.4rem 0 0.5rem; margin-top: 3.5rem;
}}
.shiba-footer .f-logo {{ font-weight: 700; font-size: 1.1rem; color: var(--accent); }}
.shiba-footer .f-desc {{ font-size: 0.84rem; color: var(--muted); margin-top: 0.4rem; line-height: 1.55; }}
.shiba-footer .f-links {{ display: flex; gap: 1.6rem; font-size: 0.85rem; }}
.shiba-footer .f-links a {{ color: var(--muted); text-decoration: none; transition: color 0.15s ease; }}
.shiba-footer .f-links a:hover {{ color: var(--accent); }}
.shiba-footer .f-copy {{ font-size: 0.77rem; color: var(--muted); opacity: 0.6; margin-top: 1.1rem; }}

/* ─── Alert ─────────────────────────────────────────── */
[data-testid="stAlert"] {{ border-radius: 14px; }}

/* ─── CV scanning / loading state (overlay full màn hình) ─ */
.scan-wrap {{
  position: fixed; inset: 0; z-index: 99990;
  display: flex; align-items: center; justify-content: center; padding: 2rem;
  background:
    radial-gradient(1100px 560px at 18% 0%, #FFFBF4 0%, rgba(255,251,244,0) 60%),
    radial-gradient(900px 520px at 100% 0%, #FCEFE2 0%, rgba(252,239,226,0) 55%),
    var(--bg);
  animation: scanIn 0.35s ease both;
}}
.scan-stage {{
  display: flex; gap: 2.5rem; align-items: center; justify-content: center;
  flex-wrap: wrap;
}}
.scan-doc {{
  position: relative; width: 230px; height: 300px; flex: 0 0 auto;
  background: #fff; border-radius: 14px; padding: 1.5rem 1.4rem;
  box-shadow: var(--shadow-card), var(--inset-hi); overflow: hidden;
  border: 1px solid var(--border);
}}
.scan-doc-head {{ height: 16px; width: 55%; border-radius: 6px; background: var(--accent-light); margin-bottom: 1.1rem; }}
.scan-ln {{ height: 9px; border-radius: 5px; background: #ECE3D7; margin: 0.55rem 0; }}
.scan-ln.w90 {{ width: 90%; }} .scan-ln.w80 {{ width: 80%; }} .scan-ln.w70 {{ width: 70%; }}
.scan-ln.w60 {{ width: 60%; }} .scan-ln.w50 {{ width: 50%; }} .scan-ln.w85 {{ width: 85%; }}
.scan-laser {{
  position: absolute; left: 5%; right: 5%; height: 3px; top: 8%; border-radius: 3px;
  background: linear-gradient(90deg, transparent, var(--accent-mid) 35%, #F0A54E 50%, var(--accent-mid) 65%, transparent);
  box-shadow: 0 0 18px 4px rgba(212,116,26,0.5); animation: laserMove 2.3s ease-in-out infinite;
}}
.scan-side {{ flex: 0 1 360px; min-width: 280px; }}
.scan-title {{
  font-family: 'Crimson Pro', Georgia, serif; font-size: 1.5rem; font-weight: 700;
  color: var(--accent); margin-bottom: 0.5rem;
}}
.scan-quotes {{ position: relative; height: 1.6rem; margin-bottom: 1.3rem; }}
.scan-q {{
  position: absolute; left: 0; top: 0; font-size: 1rem; color: var(--muted);
  opacity: 0; animation: qfade 9s ease-in-out infinite;
}}
.scan-q.q2 {{ animation-delay: 3s; }} .scan-q.q3 {{ animation-delay: 6s; }}
.skel-row {{ display: flex; gap: 0.9rem; }}
.skel-card {{
  flex: 1; background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-card); padding: 1.2rem 1.3rem; box-shadow: var(--shadow-card);
}}
.skel-line {{
  border-radius: 6px; background: linear-gradient(100deg, #EEE5D9 30%, #FAF3EA 50%, #EEE5D9 70%);
  background-size: 200% 100%; animation: shimmer 1.5s linear infinite;
}}
.skel-line.sk-sm {{ height: 10px; width: 60%; margin-bottom: 0.7rem; }}
.skel-line.sk-lg {{ height: 30px; width: 45%; margin-bottom: 0.9rem; }}
.skel-bar {{
  height: 9px; border-radius: 999px; background: linear-gradient(100deg, #EEE5D9 30%, #FAF3EA 50%, #EEE5D9 70%);
  background-size: 200% 100%; animation: shimmer 1.5s linear infinite;
}}
@keyframes scanIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
@keyframes laserMove {{ 0% {{ top: 8%; }} 50% {{ top: 88%; }} 100% {{ top: 8%; }} }}
@keyframes shimmer {{ 0% {{ background-position: 200% 0; }} 100% {{ background-position: -200% 0; }} }}
@keyframes qfade {{
  0% {{ opacity: 0; transform: translateY(7px); }}
  5% {{ opacity: 1; transform: none; }}
  28% {{ opacity: 1; transform: none; }}
  34% {{ opacity: 0; transform: translateY(-7px); }}
  100% {{ opacity: 0; }}
}}
@media (prefers-reduced-motion: reduce) {{
  .scan-laser {{ animation: none; top: 48%; }}
  .scan-q {{ animation: none; }} .scan-q.q1 {{ opacity: 1; }}
  .skel-line, .skel-bar {{ animation: none; }}
}}

/* ─── Entrance motion ───────────────────────────────── */
@media (prefers-reduced-motion: no-preference) {{
  .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="element-container"],
  .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {{
    animation: fadeUp 0.5s cubic-bezier(0.16,1,0.3,1) both;
  }}
}}
@keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(16px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes pop {{ from {{ opacity: 0; transform: scale(0.85); }} to {{ opacity: 1; transform: none; }} }}

/* ─── Landing entrance (mượt, staggered) ────────────── */
@media (prefers-reduced-motion: no-preference) {{
  /* Tắt fadeUp mặc định trên hàng cột của landing để không animation chồng nhau,
     nhường cho hiệu ứng staggered tinh tế bên dưới. */
  .block-container:has(.land-hero) > div > [data-testid="stVerticalBlock"]
    > [data-testid="stHorizontalBlock"] {{ animation: none !important; }}

  .land-rise {{ opacity: 0; animation: landRise 0.7s cubic-bezier(0.16,1,0.3,1) forwards;
                animation-delay: var(--d, 0s); will-change: transform, opacity; }}
  .land-img-in {{ opacity: 0; animation: landImgIn 0.9s cubic-bezier(0.16,1,0.3,1) 0.18s forwards;
                  will-change: transform, opacity; }}
}}
@keyframes landRise {{
  from {{ opacity: 0; transform: translateY(22px); filter: blur(4px); }}
  to {{ opacity: 1; transform: none; filter: blur(0); }}
}}
@keyframes landImgIn {{
  from {{ opacity: 0; transform: translateY(26px) scale(0.94); }}
  to {{ opacity: 1; transform: none; }}
}}

@media (prefers-reduced-motion: reduce) {{
  .badge, .metric-card-v2, .rv-card, .stat-chip {{ animation: none !important; transition: none !important; }}
  .land-rise, .land-img-in {{ opacity: 1 !important; animation: none !important; }}
}}
</style>
"""


def inject_css() -> None:
    import streamlit as st
    st.markdown(_CSS, unsafe_allow_html=True)


def render_header() -> None:
    """Thanh header với thương hiệu ShibaCV — bấm để quay về trang chủ (landing)."""
    import streamlit as st

    if st.button("🐾 ShibaCV", key="brand_home", help="Về trang chủ"):
        st.session_state["view"] = "landing"
        st.rerun()
    st.markdown('<div class="shiba-nav-divider"></div>', unsafe_allow_html=True)


def render_footer() -> None:
    import streamlit as st
    st.markdown(
        """
        <div class="shiba-footer">
          <div style="background:linear-gradient(135deg,rgba(250,227,210,0.6),rgba(255,245,236,0.4));border:1.5px solid rgba(138,63,34,0.15);border-radius:12px;padding:0.9rem 1.2rem;margin-bottom:1.5rem;text-align:center">
            <div style="font-size:0.85rem;color:var(--accent);font-weight:600;margin-bottom:0.3rem">⚠️ Lưu ý quan trọng</div>
            <div style="font-size:0.82rem;color:var(--text);line-height:1.5">AI có thể mắc lỗi. Hãy kiểm tra các thông tin trước khi sử dụng.</div>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:1.5rem">
            <div>
              <div class="f-logo">🐾 ShibaCV</div>
              <div class="f-desc">Nền tảng AI đồng hành cùng bạn trên hành trình<br>tuyển dụng và phát triển sự nghiệp.</div>
              <div class="f-copy">© 2026 ShibaCV AI. Built with precision and treats.</div>
            </div>
            <div class="f-links" style="padding-top:0.3rem">
              <a href="#">Điều khoản</a><a href="#">Bảo mật</a><a href="#">Hỗ trợ</a><a href="#">Liên hệ</a>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_scanning() -> None:
    """Màn hình loading khi AI quét CV: laser scan + thoại Shiba fade + skeleton."""
    import streamlit as st
    st.markdown(
        """
        <div class="scan-wrap">
          <div class="scan-stage">
            <div class="scan-doc">
              <div class="scan-doc-head"></div>
              <div class="scan-ln w80"></div><div class="scan-ln w60"></div>
              <div class="scan-ln w90"></div><div class="scan-ln w70"></div>
              <div class="scan-ln w85"></div><div class="scan-ln w50"></div>
              <div class="scan-ln w70"></div><div class="scan-ln w85"></div>
              <div class="scan-laser"></div>
            </div>
            <div class="scan-side">
              <div class="scan-title">🐾 Shiba đang phân tích CV của bạn…</div>
              <div class="scan-quotes">
                <span class="scan-q q1">Shiba đang đọc kỹ năng của bạn…</span>
                <span class="scan-q q2">Đang đối chiếu với hàng ngàn tiêu chuẩn…</span>
                <span class="scan-q q3">Sắp xong rồi, gâu gâu! 🐶</span>
              </div>
              <div class="skel-row">
                <div class="skel-card">
                  <div class="skel-line sk-sm"></div>
                  <div class="skel-line sk-lg"></div>
                  <div class="skel-bar"></div>
                </div>
                <div class="skel-card">
                  <div class="skel-line sk-sm"></div>
                  <div class="skel-line sk-lg"></div>
                  <div class="skel-bar"></div>
                </div>
              </div>
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
