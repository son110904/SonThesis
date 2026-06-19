"""result.py – Trang kết quả."""

from __future__ import annotations

import html
from datetime import datetime

from src.frontend.components import (
    render_match_gauge,
    render_metric_card,
    render_recommendation_card,
    render_skill_badges,
)
from src.frontend.utils.styling import img_tag, render_footer


def _verdict(pct: float) -> tuple[str, str]:
    if pct >= 70:
        return "Rất phù hợp!", "Shiba AI nhận thấy hồ sơ của bạn rất ấn tượng và có sự tương đồng cao với yêu cầu tuyển dụng. Đừng ngần ngại nộp đơn ngay!"
    if pct >= 40:
        return "Phù hợp một phần", "Hồ sơ có tiềm năng nhưng cần bổ sung thêm một số kỹ năng quan trọng để tăng cơ hội được chọn."
    return "Cần cải thiện thêm", "Hồ sơ chưa đáp ứng đủ yêu cầu. Tham khảo phần khuyến nghị để định hướng phát triển phù hợp."


def render_result() -> None:
    import streamlit as st

    result = st.session_state.get("result")
    if not result:
        st.session_state["view"] = "home"
        st.rerun()
        return

    match = result["match_score"]
    pct = match * 100
    verdict_label, verdict_desc = _verdict(pct)
    now_str = datetime.now().strftime("%I:%M %p, %d/%m/%Y")

    # ── Header ───────────────────────────────────────────────────────────────
    hdr_l, hdr_r = st.columns([3, 1])
    with hdr_l:
        st.markdown(
            f"""
            <div class="results-title">Kết quả phân tích</div>
            <div class="results-sub">
              Vị trí ứng tuyển: <strong style="color:var(--accent)">{html.escape(result['occupation_display'])}</strong>
              &nbsp;•&nbsp; Phân tích lúc {now_str}
            </div>
            """,
            unsafe_allow_html=True,
        )
    with hdr_r:
        if st.button("← Phân tích CV khác", use_container_width=True):
            st.session_state["view"] = "home"
            st.rerun()

    st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)

    # ── Row 1: score ring | shiba win + rec ──────────────────────────────────
    score_col, shiba_col = st.columns([1, 1], gap="large")

    with score_col:
        render_match_gauge(match)
        st.markdown(
            f"""
            <div class="score-verdict" style="text-align:center;margin-top:0.6rem">{verdict_label}</div>
            <div class="score-desc" style="text-align:center;margin-top:0.35rem">{verdict_desc}</div>
            """,
            unsafe_allow_html=True,
        )

    with shiba_col:
        st.markdown(
            img_tag("shiba_win.png", style="width:100%;max-width:280px;height:auto;display:block;margin:0 auto"),
            unsafe_allow_html=True,
        )
        rec_text = result.get("ai_recommendation") or ""
        rec_preview = ""
        if rec_text:
            first_line = next(
                (ln.strip(" #*-") for ln in rec_text.splitlines() if ln.strip()), ""
            )
            rec_preview = first_line[:160] + ("…" if len(first_line) > 160 else "")
        if rec_preview:
            st.markdown(
                f"""
                <div class="shiba-rec-card">
                  <div class="rec-badge">SHIBA RECOMMENDATION</div>
                  <div class="rec-quote">"{html.escape(rec_preview)}"</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)

    # ── Row 2: sub-metric cards ──────────────────────────────────────────────
    m1, m2 = st.columns(2, gap="medium")
    with m1:
        render_metric_card("Semantic Similarity", result["semantic_similarity_score"])
    with m2:
        render_metric_card("Weighted Skill Score", result["weighted_skill_score"])

    # ── Row 3: skill analysis ────────────────────────────────────────────────
    st.markdown('<div class="section-h">📊 Phân tích Kỹ năng</div>', unsafe_allow_html=True)
    sk_l, sk_r = st.columns(2, gap="medium")

    with sk_l:
        st.markdown('<div class="skill-card"><div class="skill-card-title">🎯 Kỹ năng hiện có</div>', unsafe_allow_html=True)
        st.markdown('<div class="skill-sub-label green">● KỸ NĂNG ĐÁP ỨNG</div>', unsafe_allow_html=True)
        render_skill_badges(result.get("matched_skills", []), kind="matched",
                            empty_text="Chưa khớp kỹ năng nào của nghề này.")
        st.markdown("</div>", unsafe_allow_html=True)

    with sk_r:
        st.markdown('<div class="skill-card"><div class="skill-card-title">📌 Kỹ năng cần bổ sung</div>', unsafe_allow_html=True)
        st.markdown('<div class="skill-sub-label amber">● KỸ NĂNG CÒN THIẾU</div>', unsafe_allow_html=True)
        render_skill_badges(result.get("missing_skills", []), kind="missing", max_items=24,
                            empty_text="Tuyệt vời — không thiếu kỹ năng quan trọng nào.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Row 4: AI recommendation ─────────────────────────────────────────────
    st.markdown('<div class="section-h">🤖 Khuyến nghị từ Shiba AI</div>', unsafe_allow_html=True)
    render_recommendation_card(result.get("ai_recommendation"))

    # ── Profile expander ─────────────────────────────────────────────────────
    profile = result.get("candidate_profile", {})
    with st.expander("Hồ sơ trích xuất từ CV", expanded=False):
        st.markdown("**Kỹ năng phát hiện được**")
        render_skill_badges(profile.get("skills", []), kind="muted", empty_text="(không có)")
        for label, key in [("Kinh nghiệm", "experience"), ("Dự án", "projects"), ("Học vấn", "education")]:
            items = profile.get(key, [])
            st.markdown(f"**{label}**")
            if items:
                st.markdown("\n".join(f"- {html.escape(str(i))}" for i in items))
            else:
                st.markdown(
                    "<span class='hint'>(không có — cần OPENAI_API_KEY để trích xuất)</span>",
                    unsafe_allow_html=True,
                )

    render_footer()
