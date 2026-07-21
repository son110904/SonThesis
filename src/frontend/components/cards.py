"""
cards.py – Metric card và AI Recommendation card.
"""

from __future__ import annotations

import html
import re

from src.frontend.utils.styling import score_color


def _simple_md(text: str) -> str:
    """Convert basic GPT markdown (##, - bullets, **bold**) to HTML, no external deps."""
    lines = text.splitlines()
    out: list[str] = []
    in_ul = False

    def fmt(s: str) -> str:
        s = html.escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(
            r"`(.+?)`",
            r'<code style="background:#f3ede5;padding:.1rem .3rem;border-radius:4px;font-size:.85em">\1</code>',
            s,
        )
        return s

    for line in lines:
        s = line.strip()
        if s.startswith("### "):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(f"<h4>{fmt(s[4:])}</h4>")
        elif s.startswith("## "):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(f"<h3>{fmt(s[3:])}</h3>")
        elif s.startswith("# "):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(f"<h3>{fmt(s[2:])}</h3>")
        elif s.startswith("- ") or s.startswith("* "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{fmt(s[2:])}</li>")
        elif s == "":
            if in_ul:
                out.append("</ul>")
                in_ul = False
        else:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(f"<p>{fmt(s)}</p>")

    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


def render_metric_card(label: str, score_0_1: float) -> None:
    import streamlit as st

    pct = round(score_0_1 * 100, 1)
    color = score_color(score_0_1)
    icon = "🧠" if "Semantic" in label else "⭐"
    st.markdown(
        f"""
        <div class="metric-card-v2">
          <div class="mc-icon">{icon}</div>
          <div class="mc-label">{html.escape(label)}</div>
          <div class="mc-value" style="color:{color}">{pct:g}<span>/100</span></div>
          <div class="mc-track">
            <div class="mc-fill" style="width:{pct}%;background:{color}"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_recommendation_card(markdown_text: str | None) -> None:
    import streamlit as st

    if not markdown_text:
        st.markdown(
            """<div class="ai-rec-wrap">
              <p style="color:var(--muted);font-size:.9rem">
                chưa có khuyến nghị
              </p>
            </div>""",
            unsafe_allow_html=True,
        )
        return

    body_html = _simple_md(markdown_text)
    st.markdown(f'<div class="ai-rec-wrap">{body_html}</div>', unsafe_allow_html=True)


def _review_block(title: str, icon: str, items: list[str], accent: str = "var(--accent)") -> str:
    """Render 1 khối nhận xét (list bullet) thành HTML."""
    if not items:
        body = '<div class="hint">(không có nhận xét)</div>'
    else:
        lis = "".join(f"<li>{html.escape(str(it))}</li>" for it in items)
        body = f'<ul class="rv-list">{lis}</ul>'
    return (
        f'<div class="rv-card">'
        f'<div class="rv-card-title" style="color:{accent}">{icon} {html.escape(title)}</div>'
        f"{body}</div>"
    )


def render_cv_review(review: dict | None, fallback_markdown: str | None = None) -> None:
    """
    Render AI CV Review có cấu trúc (đầu ra trung tâm). Nếu không có review cấu trúc
    (vd bản ghi lịch sử) → fallback sang markdown.
    """
    import streamlit as st

    if not review:
        render_recommendation_card(fallback_markdown)
        return

    # CV quá sơ sài: hiển thị cảnh báo riêng (mentor yêu cầu bổ sung), KHÔNG render
    # các khối nhận xét rỗng (strengths/missing/roadmap) cho gọn và đúng ý nghĩa.
    if review.get("_sparse"):
        overall = html.escape(review.get("overall_assessment", ""))
        tips = "".join(f"<li>{html.escape(str(t))}</li>" for t in review.get("recommendations", []))
        tips_html = f'<div class="rv-warn-title">Cần bổ sung:</div><ul class="rv-list">{tips}</ul>' if tips else ""
        st.markdown(
            f'<div class="rv-warn">'
            f'<div class="rv-warn-label">⚠️ CV chưa đủ thông tin để đánh giá</div>'
            f'<div class="rv-warn-body">{overall}</div>'
            f'{tips_html}'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    # 1. Overall assessment — phần nổi bật nhất
    overall = review.get("overall_assessment") or ""
    if overall:
        st.markdown(
            f'<div class="rv-overall"><div class="rv-overall-label">📋 Đánh giá tổng quan</div>'
            f'<div class="rv-overall-body">{html.escape(overall)}</div></div>',
            unsafe_allow_html=True,
        )

    # 2-5. Các khối nhận xét — xếp DỌC trong MỘT cột để không bị lệch khung;
    # mỗi .rv-card cao theo nội dung (height auto) nên khung luôn ôm sát số chữ.
    blocks = (
        _review_block("Điểm mạnh", "💪", review.get("strengths", []), "#2e7d5b")
        + _review_block("Chất lượng CV", "📝", review.get("cv_quality", []), "#b06a00")
        + _review_block("Kỹ năng còn thiếu", "🔍", review.get("missing_skills", []), "#b54708")
        + _review_block("Khuyến nghị cải thiện", "✦", review.get("recommendations", []), "var(--accent)")
    )
    st.markdown(f'<div class="rv-stack">{blocks}</div>', unsafe_allow_html=True)

    # 6. Learning roadmap — dạng timeline
    roadmap = review.get("learning_roadmap", [])
    if roadmap:
        steps_html = []
        for step in roadmap:
            head = " — ".join(x for x in [step.get("phase"), step.get("focus")] if x)
            items = "".join(f"<li>{html.escape(str(it))}</li>" for it in step.get("items", []))
            steps_html.append(
                f'<div class="rv-road-step"><div class="rv-road-head">{html.escape(head) or "Giai đoạn"}</div>'
                f'<ul class="rv-list">{items}</ul></div>'
            )
        st.markdown(
            '<div class="rv-card"><div class="rv-card-title" style="color:var(--accent)">'
            "🗺️ Lộ trình phát triển</div>" + "".join(steps_html) + "</div>",
            unsafe_allow_html=True,
        )


def render_cv_improvement(improvement: dict) -> None:
    """
    Render AI CV Improvement — tiếp nối AI CV Review: bố cục, diễn đạt, chính
    tả/ngữ pháp, và gợi ý viết lại từng bullet (current → rewrite).
    """
    import streamlit as st

    blocks = (
        _review_block("Bố cục CV", "🗂️", improvement.get("structure_review", []), "#6a4fb0")
        + _review_block("Chất lượng diễn đạt", "🖋️", improvement.get("writing_review", []), "#b06a00")
        + _review_block("Chính tả & ngữ pháp", "🔤", improvement.get("grammar_review", []), "#2e7d5b")
    )
    st.markdown(f'<div class="rv-stack">{blocks}</div>', unsafe_allow_html=True)

    rewrites = improvement.get("rewrite_suggestions", [])
    if rewrites:
        rows = []
        for item in rewrites:
            current = html.escape(str(item.get("current", "")))
            rewrite = html.escape(str(item.get("rewrite", "")))
            rows.append(
                '<div class="rw-pair">'
                f'<div class="rw-block rw-current"><span class="rw-tag">Hiện tại</span>{current}</div>'
                f'<div class="rw-block rw-rewrite"><span class="rw-tag">Gợi ý viết lại</span>{rewrite}</div>'
                "</div>"
            )
        st.markdown(
            '<div class="rv-card"><div class="rv-card-title" style="color:var(--accent)">'
            "✨ Gợi ý viết lại bullet</div>" + "".join(rows) + "</div>",
            unsafe_allow_html=True,
        )


def render_application_email(email: dict) -> None:
    """Render email ứng tuyển do AI soạn (subject + body + matching highlights)."""
    import streamlit as st

    subject = html.escape(str(email.get("subject", "")))
    body_html = html.escape(str(email.get("body", ""))).replace("\n", "<br>")
    highlights = email.get("matching_highlights", [])

    st.markdown(
        f'<div class="rv-overall"><div class="rv-overall-label">✉️ {subject}</div>'
        f'<div class="rv-overall-body">{body_html}</div></div>',
        unsafe_allow_html=True,
    )
    if highlights:
        st.markdown(
            _review_block("Điểm nhấn phù hợp với vị trí", "⭐", highlights, "#2e7d5b"),
            unsafe_allow_html=True,
        )
