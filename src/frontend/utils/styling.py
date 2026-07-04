"""
styling.py – ShibaCV design system.

Hệ thống ấm (rose-beige / terracotta) thể hiện ở mức premium: depth nhiều lớp,
highlight inset trên bề mặt, glow nền mềm, typography dùng DUY NHẤT Fraunces,
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
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;0,9..144,700;1,9..144,400;1,9..144,600&display=swap');

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

/* ─── Bỏ "màn hình trắng mờ" khi rerun ──────────────────
   Streamlit làm mờ (giảm opacity) nội dung cũ trong lúc chạy lại script. Khi model
   đang nạp ở luồng nền (~vài chục giây), rerun chậm → nội dung mờ kéo dài gây khó
   chịu. Giữ nội dung luôn rõ; loading thực sự khi phân tích đã có overlay riêng
   (.scan-wrap) nên không mất tín hiệu trạng thái. */
[data-stale="true"], [data-stale="true"] * {{ opacity: 1 !important; }}
[data-testid="stAppViewContainer"] [data-stale="true"] {{
  opacity: 1 !important; filter: none !important;
}}
[data-testid="stStatusWidget"] {{ display: none !important; }}

/* ─── Streamlit layout normalization ────────────────── */
[data-testid="stHorizontalBlock"],
[data-testid="stColumns"] {{ align-items: flex-start !important; }}
[data-testid="stColumn"] > div > [data-testid="stVerticalBlock"] {{ row-gap: 0.65rem !important; }}
[data-testid="stForm"] > [data-testid="stVerticalBlock"] {{ row-gap: 0.5rem !important; }}
[data-testid="stMarkdownContainer"]:has(.score-area) {{ display: flex; justify-content: center; }}
[data-testid="element-container"]:has(div:empty) + [data-testid="element-container"] {{ margin-top: 0 !important; }}

/* ─── Base + warm ambient background ────────────────── */
/* Toàn bộ frontend dùng DUY NHẤT Fraunces (gồm cả widget Streamlit). */
html, body, .stApp, .stApp *,
button, input, select, textarea,
[data-baseweb], [data-baseweb] * {{
  font-family: 'Fraunces', Georgia, 'Times New Roman', serif !important;
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
h1, h2, h3 {{ font-family: 'Fraunces', Georgia, serif; color: var(--text); letter-spacing: -0.015em; }}
p, .stMarkdown p {{ color: var(--text); }}
::selection {{ background: rgba(212,116,26,0.22); }}

/* ─── Buttons (gradient CTA) ────────────────────────── */
.stButton > button, .stFormSubmitButton > button {{
  background: var(--accent-grad) !important; color: #fff !important;
  border: none !important; border-radius: 999px !important;
  font-family: 'Fraunces', Georgia, serif !important; font-size: 1.02rem !important;
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

/* ─── File uploader (dashed zone canh giữa, KHÔNG nút Browse) ─────────
   Cả vùng dropzone đã bấm được để mở hộp thoại (react-dropzone mở dialog
   khi click root) → ẩn nút, ẩn text mặc định, thay bằng nội dung canh giữa. */
[data-testid="stFileUploaderDropzone"] {{
  border: 1.6px dashed var(--border) !important; border-radius: 16px !important;
  background: linear-gradient(180deg, #FFFDFA, #FBF4EC) !important;
  min-height: 152px; padding: 1.7rem 1.4rem !important; cursor: pointer;
  display: flex !important; flex-direction: column !important;
  align-items: center !important; justify-content: center !important; gap: 0.4rem;
  text-align: center;
  transition: border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}}
[data-testid="stFileUploaderDropzone"]:hover {{
  border-color: var(--accent-mid) !important;
  background: linear-gradient(180deg, #FFFDFA, #FBEFE3) !important;
  box-shadow: 0 8px 20px -12px rgba(138,63,34,0.35);
}}
[data-testid="stFileUploaderDropzoneInstructions"] {{ display: none !important; }}
[data-testid="stFileUploaderDropzone"]::before {{
  content: "📄  Tải CV lên tại đây";
  font-family: 'Fraunces', Georgia, serif; font-weight: 700;
  font-size: 1.08rem; color: var(--accent); letter-spacing: -0.01em;
}}
[data-testid="stFileUploaderDropzone"]::after {{
  content: "Kéo thả tệp vào đây hoặc bấm để chọn — PDF · DOCX · MD";
  font-size: 0.85rem; color: var(--muted);
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
/* Chữ trong ô select (giá trị đã chọn + placeholder + input) — ép màu chữ tối */
div[data-baseweb="select"] div, div[data-baseweb="select"] input {{ color: var(--text) !important; }}

/* ─── Dropdown popover menu (BaseWeb render ở portal riêng) ──
   KHÔNG được style bởi rule select ở trên → mặc định theo theme tối của hệ
   điều hành ⇒ menu đen chữ trắng. Ép sáng độc lập với theme. */
[data-baseweb="popover"] [data-baseweb="menu"],
[data-baseweb="popover"] ul[role="listbox"],
ul[role="listbox"][data-baseweb="menu"], div[data-baseweb="menu"] {{
  background: var(--surface) !important; color: var(--text) !important;
  border: 1px solid var(--border) !important; border-radius: var(--radius-sm) !important;
  box-shadow: var(--shadow-card) !important;
}}
[data-baseweb="popover"] li[role="option"], ul[role="listbox"] li[role="option"] {{
  background: var(--surface) !important; color: var(--text) !important;
}}
[data-baseweb="popover"] li[role="option"]:hover,
[data-baseweb="popover"] li[role="option"][aria-selected="true"],
ul[role="listbox"] li[role="option"]:hover {{
  background: var(--accent-light) !important; color: var(--accent) !important;
}}

/* ─── Bỏ hẳn nút "Browse files" — vùng dropzone đã bấm được ──────────── */
[data-testid="stFileUploaderDropzone"] button,
[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {{ display: none !important; }}

/* ─── Chip file đã chọn (native của Streamlit) — bo tròn, viền, nền sáng ── */
[data-testid="stFileUploaderFile"] {{
  background: var(--surface) !important; border: 1px solid var(--border) !important;
  border-radius: 12px !important; padding: 0.55rem 0.85rem !important;
  margin-top: 0.65rem !important; box-shadow: var(--shadow-card) !important;
}}
[data-testid="stFileUploaderFile"] [data-testid="stFileUploaderFileName"] {{
  color: var(--text) !important; font-weight: 700 !important;
}}
[data-testid="stFileUploaderFile"] small {{ color: var(--muted) !important; }}
[data-testid="stFileUploaderFileData"] span {{ color: var(--text) !important; }}
[data-testid="stFileUploaderDeleteBtn"] button {{
  display: inline-flex !important; color: var(--muted) !important;
  background: transparent !important; border: none !important; box-shadow: none !important;
}}
[data-testid="stFileUploaderDeleteBtn"] button:hover {{ color: var(--bad) !important; background: transparent !important; }}

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
.hero-title {{
  font-family: 'Fraunces', Georgia, serif;
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
/* Ảnh shiba (đã tách nền) thả trôi — drop-shadow theo viền alpha */
.shiba-float {{
  filter: drop-shadow(0 16px 26px rgba(74,38,18,0.20));
}}

/* ─── Upload page ───────────────────────────────────── */
.page-h1 {{
  font-family: 'Fraunces', Georgia, serif;
  font-size: clamp(1.9rem, 3vw, 2.4rem); font-weight: 700; color: var(--text);
  margin: 0 0 0.3rem; letter-spacing: -0.018em; line-height: 1.12;
}}
.page-h1-sub {{ font-size: 1rem; color: var(--muted); margin: 0 0 1.7rem; line-height: 1.6; max-width: 52ch; }}
.privacy-note {{
  font-size: 0.8rem; color: var(--muted); text-align: center; margin-top: 0.7rem;
}}

/* ─── Results page ──────────────────────────────────── */
.results-title {{
  font-family: 'Fraunces', Georgia, serif;
  font-size: clamp(1.9rem, 3vw, 2.3rem); font-weight: 700; color: var(--text);
  margin: 0 0 0.25rem; letter-spacing: -0.018em;
}}
.results-sub {{ font-size: 0.92rem; color: var(--muted); }}
.score-area {{ display: flex; flex-direction: column; align-items: center; gap: 0.6rem; padding-top: 0.4rem; }}
.score-ring {{ width: 210px; height: 210px; filter: drop-shadow(0 10px 22px rgba(138,63,34,0.14)); }}
.score-verdict {{
  font-family: 'Fraunces', Georgia, serif; font-size: 1.75rem;
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
  font-family: 'Fraunces', Georgia, serif; font-size: 2.7rem;
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
  font-family: 'Fraunces', Georgia, serif;
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
  font-family: 'Fraunces', Georgia, serif; font-size: 1.3rem;
  font-weight: 700; color: var(--accent); margin: 0 0 1rem;
}}
.ai-rec-wrap h2, .ai-rec-wrap h3, .ai-rec-wrap h4 {{
  font-family: 'Fraunces', Georgia, serif; color: var(--accent);
  font-size: 1.1rem; font-weight: 700; margin: 1rem 0 0.4rem;
}}
.ai-rec-wrap ul {{ margin: 0.3rem 0 0.6rem 1.1rem; padding: 0; }}
.ai-rec-wrap li {{ font-size: 0.9rem; line-height: 1.65; margin: 0.25rem 0; color: var(--text); }}
.ai-rec-wrap p {{ font-size: 0.9rem; line-height: 1.7; color: var(--text); margin: 0.45rem 0; }}

/* ─── CV sơ sài: thẻ cảnh báo (thay cho AI Review) ──── */
.rv-warn {{
  position: relative; overflow: hidden;
  background: linear-gradient(135deg, var(--warn-bg) 0%, #FBEED2 100%);
  border: 1px solid var(--warn-border); border-radius: var(--radius-card);
  padding: 1.5rem 1.7rem; box-shadow: var(--shadow-card), var(--inset-hi);
}}
.rv-warn::before {{
  content: ""; position: absolute; top: 0; left: 0; bottom: 0; width: 4px; background: var(--warn);
}}
.rv-warn-label {{
  font-family: 'Fraunces', Georgia, serif; font-size: 1.2rem; font-weight: 700;
  color: var(--warn); margin-bottom: 0.55rem;
}}
.rv-warn-body {{ font-size: 0.98rem; line-height: 1.65; color: var(--text); }}
.rv-warn-title {{
  font-weight: 700; font-size: 0.95rem; color: var(--text); margin: 1rem 0 0.4rem;
}}

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
  font-family: 'Fraunces', Georgia, serif; font-size: 1.2rem; font-weight: 700;
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
  font-family: 'Fraunces', Georgia, serif; font-weight: 700; font-size: 1.08rem; margin-bottom: 0.65rem;
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
  font-family: 'Fraunces', Georgia, serif; font-size: 1.45rem;
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
  font-family: 'Fraunces', Georgia, serif; font-size: 1.5rem; font-weight: 700;
  color: var(--accent); margin-bottom: 0.5rem;
}}
.scan-quotes {{ position: relative; height: 1.6rem; margin-bottom: 1.3rem; }}
.scan-q {{
  position: absolute; left: 0; top: 0; font-size: 1rem; color: var(--muted);
  opacity: 0; animation: qfade 9s ease-in-out infinite;
}}
.scan-q.q2 {{ animation-delay: 3s; }} .scan-q.q3 {{ animation-delay: 6s; }}
@keyframes scanIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
@keyframes laserMove {{ 0% {{ top: 8%; }} 50% {{ top: 88%; }} 100% {{ top: 8%; }} }}
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
  /* Nút CTA landing (st.button không wrap được bằng div markdown) */
  .st-key-cta_hero {{ opacity: 0; animation: landRise 0.7s cubic-bezier(0.16,1,0.3,1) 0.32s forwards; }}
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
  .badge, .metric-card-v2, .rv-card {{ animation: none !important; transition: none !important; }}
  .land-rise, .land-img-in, .st-key-cta_hero {{ opacity: 1 !important; animation: none !important; }}
}}

/* ══════════════════════════════════════════════════════════════════════════
   2026 REDESIGN LAYER — premium hero, workspace, steps, assistant, AI console
   ════════════════════════════════════════════════════════════════════════ */

/* ─── Hero badge (✨ eyebrow pill) ───────────────────── */
.hero-badge {{
  display:inline-flex; align-items:center; gap:0.5rem;
  padding:0.42rem 0.95rem; border-radius:999px;
  background:linear-gradient(135deg, rgba(212,116,26,0.14), rgba(138,63,34,0.07));
  border:1px solid rgba(138,63,34,0.22);
  font-size:0.78rem; font-weight:700; letter-spacing:0.04em; color:var(--accent);
  margin-bottom:1.3rem; box-shadow:var(--inset-hi);
}}
.hero-badge .spark {{ display:inline-block; animation: sparkle 2.4s ease-in-out infinite; }}
@keyframes sparkle {{ 0%,100%{{opacity:.55;transform:scale(0.9) rotate(0)}} 50%{{opacity:1;transform:scale(1.18) rotate(8deg)}} }}

/* ─── Trust row (✓ chips under CTA) ─────────────────── */
.trust-row {{ display:flex; flex-wrap:wrap; gap:0.7rem 1.5rem; margin:1.7rem 0 0.2rem; }}
.trust-item {{ display:inline-flex; align-items:center; gap:0.5rem; font-size:0.9rem; color:var(--text); font-weight:500; }}
.trust-item .tick {{
  display:inline-flex; align-items:center; justify-content:center;
  width:20px; height:20px; border-radius:999px; background:var(--good-bg);
  color:var(--good); font-size:0.72rem; border:1px solid var(--good-border); flex:0 0 auto;
}}

/* ─── Social proof strip ────────────────────────────── */
.social-proof {{ margin-top:2.1rem; padding-top:1.5rem; border-top:1px solid var(--border); }}
.social-proof .sp-label {{
  font-size:0.72rem; text-transform:uppercase; letter-spacing:0.15em;
  color:var(--muted); font-weight:700; margin-bottom:0.8rem;
}}
.social-proof .sp-row {{ display:flex; gap:1.1rem 1.7rem; flex-wrap:wrap; align-items:center; }}
.sp-badge {{ display:inline-flex; align-items:center; gap:0.5rem; font-size:0.9rem; color:var(--muted); font-weight:600; }}
.sp-badge .spb-ico {{ font-size:1.05rem; opacity:0.85; }}

/* ─── Hero animated workspace (right side of landing) ── */
.hero-workspace {{
  position:relative; width:100%; aspect-ratio: 1 / 1; max-width:500px; margin:0 auto;
  display:flex; align-items:center; justify-content:center;
}}
.ws-glow {{
  position:absolute; inset:10%; border-radius:50%;
  background: radial-gradient(circle at 50% 42%, rgba(212,116,26,0.20), transparent 62%);
  filter:blur(8px);
}}
.ws-ring {{
  position:absolute; width:76%; height:76%; border-radius:50%;
  border:1.5px dashed rgba(138,63,34,0.24); animation: wsSpin 28s linear infinite;
}}
.ws-ring.r2 {{ width:97%; height:97%; border-color:rgba(212,116,26,0.15); animation-duration:44s; animation-direction:reverse; }}
@keyframes wsSpin {{ to {{ transform: rotate(360deg); }} }}
.ws-shiba {{ position:relative; z-index:3; width:58%; filter: drop-shadow(0 22px 36px rgba(74,38,18,0.28)); animation: wsBob 6s ease-in-out infinite; }}
@keyframes wsBob {{ 0%,100%{{transform:translateY(0)}} 50%{{transform:translateY(-8px)}} }}
.ws-chip {{
  position:absolute; z-index:4; background:var(--surface);
  border:1px solid var(--border); border-radius:14px; padding:0.6rem 0.85rem;
  box-shadow:var(--shadow-card), var(--inset-hi); display:flex; align-items:center; gap:0.6rem;
  animation: wsFloat 5s ease-in-out infinite; white-space:nowrap;
}}
.ws-chip .wc-ico {{ font-size:1.15rem; line-height:1; }}
.ws-chip .wc-k {{ font-size:0.62rem; text-transform:uppercase; letter-spacing:0.06em; color:var(--muted); font-weight:700; }}
.ws-chip .wc-v {{ font-size:0.98rem; font-weight:700; color:var(--text); line-height:1.05; }}
.ws-chip .wc-v.good {{ color:var(--good); }}
.ws-chip.c1 {{ top:4%;  left:-3%;  animation-delay:0s;   }}
.ws-chip.c2 {{ top:26%; right:-7%; animation-delay:0.9s; }}
.ws-chip.c3 {{ bottom:22%; left:-8%; animation-delay:1.8s; }}
.ws-chip.c4 {{ bottom:3%; right:-1%; animation-delay:2.7s; }}
@keyframes wsFloat {{ 0%,100%{{transform:translateY(0)}} 50%{{transform:translateY(-11px)}} }}
.ws-particle {{
  position:absolute; width:6px; height:6px; border-radius:50%;
  background:var(--accent-mid); opacity:0; animation: wsRise 5.5s ease-in infinite;
}}
.ws-particle.p1 {{ left:30%; bottom:18%; animation-delay:0s;   }}
.ws-particle.p2 {{ left:62%; bottom:24%; animation-delay:1.3s; background:#F0A54E; }}
.ws-particle.p3 {{ left:46%; bottom:14%; animation-delay:2.6s; }}
.ws-particle.p4 {{ left:70%; bottom:16%; animation-delay:3.6s; background:#F0A54E; }}
@keyframes wsRise {{
  0% {{ opacity:0; transform:translateY(0) scale(0.6); }}
  20% {{ opacity:0.75; }}
  100% {{ opacity:0; transform:translateY(-120px) scale(1); }}
}}

/* ─── Step indicator (upload flow) ──────────────────── */
.step-flow {{ display:flex; align-items:flex-start; margin:1.6rem 0 0.4rem; }}
.step-item {{ flex:1; position:relative; text-align:center; }}
.step-item::before {{
  content:""; position:absolute; top:18px; left:-50%; width:100%; height:2px;
  background:var(--border); z-index:0;
}}
.step-item:first-child::before {{ display:none; }}
.step-item.active::before, .step-item.done::before {{ background:var(--accent-mid); }}
.step-item .step-dot {{
  position:relative; z-index:1; width:38px; height:38px; margin:0 auto 0.55rem;
  border-radius:999px; background:var(--surface); border:2px solid var(--border);
  display:flex; align-items:center; justify-content:center; font-weight:700;
  color:var(--muted); font-size:0.92rem;
}}
.step-item.done .step-dot {{ background:var(--accent-light); color:var(--accent); border-color:rgba(138,63,34,0.3); }}
.step-item.active .step-dot {{
  background:var(--accent-grad); color:#fff; border-color:transparent;
  box-shadow:0 5px 14px -3px rgba(138,63,34,0.45); animation: stepPulse 2s ease-in-out infinite;
}}
@keyframes stepPulse {{ 0%,100%{{box-shadow:0 5px 14px -3px rgba(138,63,34,0.45)}} 50%{{box-shadow:0 5px 22px -2px rgba(212,116,26,0.6)}} }}
.step-item .step-label {{ font-size:0.8rem; color:var(--muted); font-weight:600; line-height:1.3; }}
.step-item.active .step-label {{ color:var(--accent); }}

/* ─── Sticky AI assistant panel (upload right col) ──── */
.assist-panel {{
  position:sticky; top:1.1rem;
  background:linear-gradient(180deg, var(--surface), var(--surface-warm));
  border:1px solid var(--border); border-radius:20px; padding:1.5rem 1.55rem;
  box-shadow:var(--shadow-card), var(--inset-hi);
}}
.assist-head {{ display:flex; align-items:center; gap:0.75rem; margin-bottom:1.1rem; }}
.assist-head .ah-avatar {{
  width:44px; height:44px; border-radius:12px; flex:0 0 auto; object-fit:cover;
  background:var(--accent-light); box-shadow:var(--inset-hi);
}}
.assist-head .ah-title {{ font-weight:700; color:var(--text); font-size:1.05rem; line-height:1.15; }}
.assist-head .ah-sub {{ font-size:0.78rem; color:var(--muted); display:inline-flex; align-items:center; gap:0.35rem; }}
.assist-head .ah-sub .live {{ width:7px;height:7px;border-radius:50%;background:var(--good); animation:pulse 1.4s ease-in-out infinite; }}
.assist-status {{ display:flex; flex-direction:column; gap:0.6rem; padding:0.3rem 0 0.2rem; }}
.assist-line {{ display:flex; align-items:center; gap:0.65rem; font-size:0.88rem; color:var(--muted); }}
.assist-line .al-dot {{ width:9px;height:9px;border-radius:50%;background:var(--border); flex:0 0 auto; }}
.assist-line.on {{ color:var(--text); font-weight:600; }}
.assist-line.on .al-dot {{ background:var(--accent-mid); box-shadow:0 0 0 4px rgba(212,116,26,0.16); animation:pulse 1.5s ease-in-out infinite; }}
@keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.35}} }}
.assist-divider {{ height:1px; background:var(--border); margin:1.1rem 0; }}

/* ─── Feature cards grid ────────────────────────────── */
.feature-grid {{ display:grid; grid-template-columns:repeat(2,1fr); gap:0.75rem; }}
.feature-card {{
  background:var(--surface); border:1px solid var(--border); border-radius:16px;
  padding:1.05rem 1.1rem; box-shadow:var(--shadow-card);
  transition:transform .18s cubic-bezier(0.16,1,0.3,1), box-shadow .18s ease;
}}
.feature-card:hover {{ transform:translateY(-3px); box-shadow:var(--shadow-hover); }}
.feature-card .fc-ico {{ font-size:1.45rem; margin-bottom:0.45rem; display:block; }}
.feature-card .fc-title {{ font-weight:700; font-size:0.94rem; color:var(--text); margin-bottom:0.2rem; }}
.feature-card .fc-desc {{ font-size:0.79rem; color:var(--muted); line-height:1.5; }}

/* ─── Section eyebrow + heading rhythm ──────────────── */
.eyebrow {{
  font-size:0.72rem; font-weight:700; text-transform:uppercase; letter-spacing:0.14em;
  color:var(--accent); margin-bottom:0.5rem;
}}
.soft-divider {{ height:1px; background:linear-gradient(90deg, var(--border), transparent); margin:1.6rem 0; }}

/* ─── AI console (scanning right side) ──────────────── */
.ai-console {{
  background:linear-gradient(165deg,#2A1B12,#241710); border-radius:18px;
  padding:1.3rem 1.45rem; box-shadow:var(--shadow-card);
  border:1px solid rgba(240,165,78,0.25); width:100%; box-sizing:border-box;
}}
.aic-head {{ display:flex; align-items:center; gap:0.4rem; margin-bottom:1.05rem; }}
.aic-dot {{ width:11px;height:11px;border-radius:50%; }}
.aic-dot.r{{background:#E0603A}} .aic-dot.y{{background:#E0A02F}} .aic-dot.g{{background:#4FA773}}
.aic-title {{ margin-left:0.55rem; color:#EADCCD; font-size:0.78rem; letter-spacing:0.06em; opacity:0.85; }}
.ai-log-line {{
  display:flex; align-items:center; gap:0.7rem; color:#CBB9A8; font-size:0.92rem;
  padding:0.34rem 0; opacity:0; transform:translateX(-8px);
  animation: logIn 0.45s ease forwards;
}}
.ai-log-line .alc {{
  color:#5BB682; font-weight:800; font-size:0.95rem; opacity:0; transform:scale(0);
  animation: tick 0.32s cubic-bezier(0.16,1,0.3,1) forwards;
}}
.ai-log-line .alx {{ color:#F0A54E; margin-left:auto; font-size:0.78rem; opacity:0.75; }}
.ai-log-line.l0 {{ animation-delay:0.15s; }} .ai-log-line.l0 .alc {{ animation-delay:1.1s; }}
.ai-log-line.l1 {{ animation-delay:0.55s; }} .ai-log-line.l1 .alc {{ animation-delay:2.0s; }}
.ai-log-line.l2 {{ animation-delay:0.95s; }} .ai-log-line.l2 .alc {{ animation-delay:3.0s; }}
.ai-log-line.l3 {{ animation-delay:1.35s; }} .ai-log-line.l3 .alc {{ animation-delay:4.1s; }}
.ai-log-line.l4 {{ animation-delay:1.75s; }} .ai-log-line.l4 .alc {{ animation-delay:5.3s; }}
.ai-log-line.l5 {{ animation-delay:2.15s; }} .ai-log-line.l5 .alc {{ animation-delay:6.6s; }}
@keyframes logIn {{ to {{ opacity:1; transform:none; }} }}
@keyframes tick {{ to {{ opacity:1; transform:scale(1); }} }}
.ai-progress {{ height:8px; background:rgba(255,255,255,0.13); border-radius:999px; margin-top:1.25rem; overflow:hidden; }}
.ai-progress .aip-fill {{
  height:100%; width:6%; border-radius:999px;
  background:linear-gradient(90deg,var(--accent-mid),#F0A54E);
  animation: aipGrow 8s cubic-bezier(0.3,0.8,0.4,1) forwards;
}}
@keyframes aipGrow {{ to {{ width:94%; }} }}
.ai-stage {{ margin-top:0.7rem; font-size:0.8rem; color:#B39C8A; display:flex; justify-content:space-between; }}

/* ─── Recommendation (Top 3) cards ──────────────────── */
.rec-card {{
  position:relative; overflow:hidden;
  background:var(--surface); border:1px solid var(--border);
  border-radius:var(--radius-card); padding:1.4rem 1.5rem 1.5rem;
  box-shadow:var(--shadow-card), var(--inset-hi); height:100%;
  transition:transform .2s cubic-bezier(0.16,1,0.3,1), box-shadow .2s ease;
}}
.rec-card::before {{
  content:""; position:absolute; top:0; left:0; right:0; height:3px;
  background:var(--accent-grad); opacity:0.85;
}}
.rec-card.top {{ border-color:rgba(138,63,34,0.35); box-shadow:var(--shadow-hover), var(--inset-hi); }}
.rec-card:hover {{ transform:translateY(-5px); box-shadow:var(--shadow-hover), var(--inset-hi); }}
.rec-rank {{
  display:flex; align-items:center; gap:0.45rem; font-size:1.35rem; margin-bottom:0.55rem;
}}
.rec-rank span {{
  font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em;
  color:var(--muted); background:var(--accent-light); padding:0.2rem 0.6rem; border-radius:999px;
}}
.rec-occ {{
  font-family:'Fraunces', Georgia, serif; font-weight:700; font-size:1.12rem;
  color:var(--text); line-height:1.25; min-height:2.7em; display:flex; align-items:center;
}}
.rec-score {{
  font-family:'Fraunces', Georgia, serif; font-size:2.9rem; font-weight:700;
  line-height:1; letter-spacing:-0.02em; margin:0.4rem 0 0.1rem;
}}
.rec-score span {{ font-size:1.05rem; color:var(--muted); font-weight:500; }}
.rec-conf {{
  display:inline-block; font-size:0.74rem; font-weight:700; letter-spacing:0.02em;
  padding:0.22rem 0.7rem; border-radius:999px; margin:0.35rem 0 1rem;
}}
.rec-metric .rm-row {{
  display:flex; justify-content:space-between; align-items:baseline;
  font-size:0.82rem; color:var(--muted);
}}
.rec-metric .rm-row b {{ color:var(--text); font-size:0.92rem; }}
.rec-metric .rm-track {{ height:7px; background:#EFE6DA; border-radius:999px; margin-top:0.35rem; overflow:hidden; }}
.rec-metric .rm-fill {{ height:100%; border-radius:999px; transition:width 0.7s cubic-bezier(0.16,1,0.3,1); }}

/* Reduced-motion: reveal all animated redesign elements statically */
@media (prefers-reduced-motion: reduce) {{
  .hero-badge .spark, .ws-shiba, .ws-chip, .ws-ring, .step-item.active .step-dot,
  .assist-line.on .al-dot {{ animation: none !important; }}
  .ws-particle {{ display:none !important; }}
  .ai-log-line, .ai-log-line .alc {{ opacity:1 !important; transform:none !important; animation:none !important; }}
  .ai-progress .aip-fill {{ width:94% !important; animation:none !important; }}
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


def render_scanning(
    title: str = "🐾 Shiba đang phân tích CV của bạn…",
    quotes: tuple[str, str, str] = (
        "Shiba đang đọc kỹ năng của bạn…",
        "Đang đối chiếu với hàng ngàn tiêu chuẩn…",
        "Sắp xong rồi, gâu gâu! 🐶",
    ),
    steps: tuple[str, ...] | None = None,
) -> None:
    """Màn hình loading khi AI quét CV: laser scan resume + console log AI chạy theo giai đoạn.

    title/quotes/steps tùy biến theo luồng (gợi ý nghề vs đánh giá chi tiết) để loading rõ ràng.
    steps là danh sách bước xử lý hiện dần trong console (mặc định: pipeline đầy đủ).
    """
    import html as _html
    import streamlit as st
    q1, q2, q3 = (_html.escape(q) for q in quotes)
    if steps is None:
        steps = (
            "Đọc & bóc tách văn bản CV",
            "Trích xuất kinh nghiệm & dự án",
            "Nhận diện kỹ năng",
            "Tính vector ngữ nghĩa (embedding)",
            "Đối chiếu với toàn bộ nhóm nghề",
            "Xếp hạng & tổng hợp kết quả",
        )
    log_html = "".join(
        f'<div class="ai-log-line l{i}"><span class="alc">✓</span>'
        f"<span>{_html.escape(s)}</span></div>"
        for i, s in enumerate(steps)
    )
    st.markdown(
        f"""
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
              <div class="scan-title">{_html.escape(title)}</div>
              <div class="scan-quotes">
                <span class="scan-q q1">{q1}</span>
                <span class="scan-q q2">{q2}</span>
                <span class="scan-q q3">{q3}</span>
              </div>
              <div class="ai-console">
                <div class="aic-head">
                  <span class="aic-dot r"></span><span class="aic-dot y"></span><span class="aic-dot g"></span>
                  <span class="aic-title">shiba-ai · analysis engine</span>
                </div>
                {log_html}
                <div class="ai-progress"><div class="aip-fill"></div></div>
                <div class="ai-stage"><span>🐾 Đang xử lý…</span><span>ShibaCV Engine v2</span></div>
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
