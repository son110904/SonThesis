"""design_preview.py – Sinh preview.html tĩnh dùng đúng design system để xem nhanh
giao diện mà không cần chạy backend/model. Chỉ dùng để review thiết kế."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.frontend.utils.styling import _CSS, img_tag
from src.frontend.components.score_gauge import render_match_gauge  # noqa: F401

OUT = Path(__file__).resolve().parent / "preview_build" / "index.html"
OUT.parent.mkdir(parents=True, exist_ok=True)


def gauge_svg(pct: float) -> str:
    import math
    r, cx = 84, 110
    circ = 2 * math.pi * r
    dash = circ * (pct / 100)
    return f"""
<svg viewBox="0 0 220 220" class="score-ring" xmlns="http://www.w3.org/2000/svg">
  <defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="#D4741A"/><stop offset="100%" stop-color="#8A3F22"/>
  </linearGradient></defs>
  <circle cx="{cx}" cy="{cx}" r="{r}" fill="none" stroke="#EFE6DA" stroke-width="16" stroke-linecap="round"/>
  <circle cx="{cx}" cy="{cx}" r="{r}" fill="none" stroke="url(#g)" stroke-width="16" stroke-linecap="round"
    stroke-dasharray="{dash:.2f} {circ - dash:.2f}" transform="rotate(-90 {cx} {cx})"/>
  <text x="{cx}" y="104" text-anchor="middle" font-family="'Crimson Pro',serif" font-size="46" font-weight="700" fill="#241710">{pct:g}%</text>
  <text x="{cx}" y="136" text-anchor="middle" font-family="Inter,sans-serif" font-size="11" font-weight="700" fill="#7A6658" letter-spacing="2.5">MATCH SCORE</text>
</svg>"""


def badges(items, cls):
    return '<div class="badge-wrap">' + "".join(
        f'<span class="badge {cls}">{x}</span>' for x in items
    ) + "</div>"


HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
{_CSS}
<style>body{{margin:0}} .stApp{{min-height:100vh}} .wrap{{max-width:1240px;margin:0 auto;padding:2.2rem 2.6rem 5rem}}
.demo-sep{{margin:3rem 0 1rem;font:700 0.75rem Inter;letter-spacing:.15em;text-transform:uppercase;color:#B85427;border-top:1px dashed #E7D9CB;padding-top:1rem}}
.cols{{display:flex;gap:2rem}} .col{{flex:1}}</style></head>
<body><div class="stApp"><div class="wrap">

<div class="demo-sep">1 · Landing</div>
<div class="cols">
  <div class="col" style="display:flex;flex-direction:column;justify-content:center">
    <div class="hero-eyebrow">AI Career Intelligence</div>
    <div class="hero-title">Nâng tầm sự nghiệp cùng<br><span class="accent">Shiba Intelligence</span></div>
    <div class="hero-subtitle">AI đánh giá CV, phân tích kỹ năng và đưa ra lộ trình nghề nghiệp hoàn hảo cho bạn.</div>
    <div><button style="background:var(--accent-grad);color:#fff;border:none;border-radius:999px;font:600 0.97rem Inter;padding:0.72rem 2rem;box-shadow:var(--cta-shadow);cursor:pointer">Bắt đầu ngay →</button></div>
  </div>
  <div class="col"><div class="hero-img-card">{img_tag("shiba_desk.png")}</div></div>
</div>

<div class="demo-sep">2 · Upload</div>
<div class="page-h1">Cùng nâng cấp CV của bạn</div>
<div class="page-h1-sub">Hãy tải CV lên và chọn lĩnh vực nghề nghiệp. Shiba AI sẽ lo phần còn lại.</div>
<div class="cols">
  <div class="col">
    <div style="border:1.5px dashed #E7D9CB;border-radius:16px;background:linear-gradient(180deg,#FFFDFA,#FBF4EC);min-height:142px;display:flex;align-items:center;justify-content:center;color:#7A6658">📄 Kéo thả CV (PDF, DOCX)</div>
    <div class="field-label"><span class="fl-icon">📁</span><span>Lĩnh vực nghề nghiệp của bạn</span></div>
    <div style="border:1.5px solid #E7D9CB;border-radius:12px;background:#fff;min-height:46px;padding:0.7rem 1rem;color:#241710">Công nghệ thông tin</div>
  </div>
  <div class="col">
    <div class="hero-img-card" style="min-height:auto;padding-bottom:1.4rem">{img_tag("shiba_ai.png", style="max-width:240px;border-radius:16px")}</div>
    <div class="stats-row">
      <div class="stat-chip"><div class="s-icon">✅</div><div class="s-main">Chính xác 99%</div><div class="s-sub">Phân tích sâu ATS</div></div>
      <div class="stat-chip"><div class="s-icon">⚡</div><div class="s-main">Tốc độ Shiba</div><div class="s-sub">Xong trong 15s</div></div>
    </div>
  </div>
</div>

<div class="demo-sep">3 · Results</div>
<div class="results-title">AI CV Review</div>
<div class="results-sub">Vị trí: <strong style="color:var(--accent)">Backend Developer</strong> • Phân tích lúc 10:24</div>
<div style="height:1.2rem"></div>
<div class="cols">
  <div class="col"><div class="score-area">{gauge_svg(78)}</div>
    <div style="text-align:center;margin-top:.5rem"><div class="score-verdict">Rất phù hợp!</div>
    <div class="score-desc">Hồ sơ của bạn có sự tương đồng cao với yêu cầu tuyển dụng.</div></div></div>
  <div class="col" style="display:flex;align-items:center;justify-content:center">{img_tag("shiba_win.png", style="max-width:240px")}</div>
</div>
<div style="height:.8rem"></div>
<div class="cols">
  <div class="col"><div class="metric-card-v2"><div class="mc-icon">🧠</div><div class="mc-label">Semantic Similarity</div>
    <div class="mc-value" style="color:#2A7A50">81<span>/100</span></div>
    <div class="mc-track"><div class="mc-fill" style="width:81%;background:#2A7A50"></div></div></div></div>
  <div class="col"><div class="metric-card-v2"><div class="mc-icon">⭐</div><div class="mc-label">Weighted Skill Score</div>
    <div class="mc-value" style="color:#9A6020">74<span>/100</span></div>
    <div class="mc-track"><div class="mc-fill" style="width:74%;background:#9A6020"></div></div></div></div>
</div>
<div class="section-h">🤖 Nhận xét chi tiết từ Shiba AI</div>
<div class="rv-overall"><div class="rv-overall-label">📋 Đánh giá tổng quan</div>
<div class="rv-overall-body">Hồ sơ thể hiện nền tảng backend vững với Python và thiết kế API. Bổ sung kinh nghiệm container hoá và CI/CD sẽ giúp bạn nổi bật hơn.</div></div>
<div class="cols">
  <div class="col"><div class="rv-card"><div class="rv-card-title" style="color:#2e7d5b">💪 Điểm mạnh</div>
    <ul class="rv-list"><li>Thành thạo Python, FastAPI</li><li>Hiểu thiết kế cơ sở dữ liệu quan hệ</li></ul></div></div>
  <div class="col"><div class="rv-card"><div class="rv-card-title" style="color:#b54708">🔍 Kỹ năng còn thiếu</div>
    <ul class="rv-list"><li>Docker / Kubernetes</li><li>Kinh nghiệm CI/CD pipeline</li></ul></div></div>
</div>
<div class="section-h">📊 Đối chiếu kỹ năng</div>
<div class="cols">
  <div class="col"><div class="skill-card"><div class="skill-sub-label green">● KỸ NĂNG ĐÁP ỨNG</div>
    {badges(["Python", "FastAPI", "PostgreSQL", "REST API", "Git"], "badge-matched")}</div></div>
  <div class="col"><div class="skill-card"><div class="skill-sub-label amber">● KỸ NĂNG CÒN THIẾU</div>
    {badges(["Docker", "Kubernetes", "Redis", "CI/CD", "AWS"], "badge-missing")}</div></div>
</div>

</div></div></body></html>"""

OUT.write_text(HTML, encoding="utf-8")
print("wrote", OUT)
