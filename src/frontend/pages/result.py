"""
result.py – Trang kết quả: Match Score (gauge + progress), Semantic & Weighted
(thẻ riêng), Matched/Missing skills (badge), AI Recommendation (thẻ lớn).
"""

from __future__ import annotations

import html

from src.frontend.components import (
    render_match_gauge,
    render_metric_card,
    render_recommendation_card,
    render_skill_badges,
)


def _verdict(match_0_1: float) -> str:
    pct = match_0_1 * 100
    if pct >= 70:
        return "Rất phù hợp"
    if pct >= 40:
        return "Phù hợp một phần"
    return "Chưa phù hợp"


def render_result() -> None:
    """Render trang kết quả từ session_state['result']."""
    import streamlit as st

    result = st.session_state.get("result")
    if not result:
        st.session_state["view"] = "home"
        st.rerun()
        return

    match = result["match_score"]

    # ── Header + điều hướng ─────────────────────────────────────────────
    top_l, top_r = st.columns([4, 1])
    with top_l:
        st.markdown(
            f"""
            <div class="app-header">
              <div class="title">{html.escape(result['occupation_display'])}</div>
              <div class="subtitle">{_verdict(match)} · Match score tổng {match*100:.0f}/100</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with top_r:
        if st.button("← CV khác", width="stretch"):
            st.session_state["view"] = "home"
            st.rerun()

    st.markdown("<hr class='app-divider'/>", unsafe_allow_html=True)

    # ── Match Score: gauge + progress + 2 thẻ thành phần ────────────────
    g_col, m_col = st.columns([1, 1])
    with g_col:
        st.markdown("<div class='section-label'>Match Score</div>", unsafe_allow_html=True)
        render_match_gauge(match)
        st.progress(min(max(match, 0.0), 1.0))
    with m_col:
        st.markdown("<div class='section-label'>Thành phần điểm</div>", unsafe_allow_html=True)
        render_metric_card("Semantic Similarity", result["semantic_similarity_score"])
        st.write("")
        render_metric_card("Weighted Skill Score", result["weighted_skill_score"])

    # ── Skill gap ───────────────────────────────────────────────────────
    st.markdown("<div class='section-label'>Kỹ năng đã đáp ứng</div>", unsafe_allow_html=True)
    render_skill_badges(result.get("matched_skills", []), kind="matched",
                        empty_text="Chưa khớp kỹ năng nào của nghề này.")

    st.markdown("<div class='section-label'>Kỹ năng còn thiếu</div>", unsafe_allow_html=True)
    render_skill_badges(result.get("missing_skills", []), kind="missing", max_items=30,
                        empty_text="Tuyệt vời — không thiếu kỹ năng quan trọng nào.")

    # ── Hồ sơ ứng viên (trích từ CV) ────────────────────────────────────
    profile = result.get("candidate_profile", {})
    with st.expander("Hồ sơ trích xuất từ CV", expanded=False):
        st.markdown("**Kỹ năng**")
        render_skill_badges(profile.get("skills", []), kind="muted", empty_text="(không có)")
        for label, key in [("Kinh nghiệm", "experience"), ("Dự án", "projects"), ("Học vấn", "education")]:
            items = profile.get(key, [])
            st.markdown(f"**{label}**")
            if items:
                st.markdown("\n".join(f"- {html.escape(str(i))}" for i in items))
            else:
                st.markdown("<span class='hint'>(không có — cần OPENAI_API_KEY để trích)</span>",
                            unsafe_allow_html=True)

    # ── AI Recommendation ───────────────────────────────────────────────
    st.markdown("<div class='section-label'>Khuyến nghị AI</div>", unsafe_allow_html=True)
    render_recommendation_card(result.get("ai_recommendation"))
