"""result.py – Trang kết quả. AI CV Review là đầu ra TRUNG TÂM; skill gap hỗ trợ."""

from __future__ import annotations

import html
from datetime import datetime

from src.config import VIETNAM_TZ
from src.frontend.components import (
    render_metric_card,
    render_cv_review,
    render_cv_improvement,
    render_application_email,
    render_skill_badges,
)
from src.frontend.utils.api_client import APIError, generate_application_email
from src.frontend.utils.styling import img_tag, render_footer


def render_result() -> None:
    import streamlit as st

    result = st.session_state.get("result")
    if not result:
        st.session_state["view"] = "home"
        st.rerun()
        return

    now_str = datetime.now(VIETNAM_TZ).strftime("%I:%M %p, %d/%m/%Y")

    # ── Header ───────────────────────────────────────────────────────────────
    hdr_l, hdr_r = st.columns([3, 1])
    with hdr_l:
        st.markdown(
            f"""
            <div class="eyebrow">Bước 4 · Báo cáo chi tiết</div>
            <div class="results-title">Kết quả phân tích</div>
            <div class="results-sub">
              Vị trí: <strong style="color:var(--accent)">{html.escape(result['occupation_display'])}</strong>
              &nbsp;•&nbsp; Phân tích lúc {now_str}
            </div>
            """,
            unsafe_allow_html=True,
        )
    with hdr_r:
        if st.button("← Quay lại", key="back_home", use_container_width=True):
            for k in ("candidate_profile", "candidate_embedding", "result", "application_email"):
                st.session_state.pop(k, None)
            st.session_state["view"] = "home"
            st.rerun()

    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

    # ── Row 1: 2 metric cards + shiba (3 cột) ─────────────────────────────────
    m1, m2, shiba_col = st.columns([1, 1, 1], gap="medium")
    with m1:
        render_metric_card("Semantic Similarity", result["semantic_similarity_score"])
    with m2:
        render_metric_card("Weighted Skill Score", result["weighted_skill_score"])
    with shiba_col:
        st.markdown(
            img_tag(
                "shiba_win_cut.png",
                style="width:100%;max-width:180px;height:auto;display:block;margin:0 auto",
            ).replace("<img ", '<img class="shiba-float" '),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    # ── HERO: AI CV Review (đầu ra trung tâm) ─────────────────────────────────
    st.markdown('<div class="section-h">Nhận xét chi tiết từ Shiba AI</div>', unsafe_allow_html=True)
    render_cv_review(result.get("cv_review"), result.get("ai_recommendation"))

    # ── AI CV Improvement: tiếp nối AI CV Review, sinh tự động (nếu có) ───────
    if result.get("cv_improvement"):
        st.markdown('<div class="section-h">Gợi ý cải thiện CV</div>', unsafe_allow_html=True)
        render_cv_improvement(result["cv_improvement"])

    # ── AI Application Email: CHỈ sinh khi người dùng bấm nút ─────────────────
    st.markdown('<div class="section-h">Chuẩn bị ứng tuyển</div>', unsafe_allow_html=True)
    application_email = st.session_state.get("application_email")
    if application_email:
        render_application_email(application_email)
        # Bấm "Tạo lại" phải sinh email mới NGAY (trước đây chỉ xóa email cũ rồi
        # rerun → phải bấm lần thứ hai mới thực sự tạo).
        do_generate = st.button("↻ Tạo lại email khác", key="regen_email")
    else:
        do_generate = st.button("Tạo email ứng tuyển", type="primary", key="gen_email")

    if do_generate:
        with st.spinner("Shiba đang soạn email ứng tuyển…"):
            try:
                email = generate_application_email(
                    candidate_profile=result.get("candidate_profile", {}),
                    occupation_key=result["occupation_key"],
                    semantic_similarity_score=result["semantic_similarity_score"],
                    weighted_skill_score=result["weighted_skill_score"],
                    matched_skills=result.get("matched_skills", []),
                    missing_skills=result.get("missing_skills", []),
                    cv_review=result.get("cv_review"),
                )
            except APIError as e:
                st.error(f"Không tạo được email: {e}")
                email = None
        if email:
            st.session_state["application_email"] = email
            st.rerun()
        else:
            st.warning(
                "CV chưa đủ thông tin để soạn email cá nhân hóa cho vị trí này, "
                "hoặc dịch vụ AI hiện không khả dụng."
            )

    # ── Hồ sơ trích xuất ─────────────────────────────────────────────────────
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
