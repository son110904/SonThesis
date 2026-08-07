"""jd_comparison.py – Trang so sánh CV ↔ JD (chế độ 2, không dùng Occupation KB)."""

from __future__ import annotations

import html
import logging

from src.frontend.components import (
    render_metric_card,
    render_cv_review,
    render_cv_improvement,
    render_application_email,
    render_skill_badges,
)
from src.frontend.utils.api_client import (
    APIError,
    compare_cv_with_jd,
    compare_cv_with_jd_saved,
    generate_application_email_for_jd,
    generate_cv_improvement_for_jd,
)
from src.frontend.utils.styling import img_tag, render_footer, render_scanning

logger = logging.getLogger(__name__)


def _attach_cv_improvement(result: dict) -> None:
    """Sinh AI CV Improvement cho JD và gắn vào result (best-effort, không chặn luồng chính)."""
    try:
        result["cv_improvement"] = generate_cv_improvement_for_jd(
            candidate_profile=result.get("candidate_profile", {}),
            jd_position=result.get("jd_position", ""),
            jd_skills=result.get("jd_skills", []),
            semantic_similarity_score=result["semantic_similarity_score"],
            weighted_skill_score=result["weighted_skill_score"],
            matched_skills=result.get("matched_skills", []),
            missing_skills=result.get("missing_skills", []),
        )
    except APIError as e:
        logger.warning(f"Bỏ qua AI CV Improvement (JD mode): {e}")
        result["cv_improvement"] = None


def _fail(st, msg: str) -> None:
    logger.error(f"JD Comparison failed: {msg}")
    st.markdown("<style>.scan-wrap{display:none !important}</style>", unsafe_allow_html=True)
    st.error(msg)
    if st.button("← Quay lại"):
        for k in ("jd_result", "jd_loading_shown", "jd_application_email"):
            st.session_state.pop(k, None)
        st.session_state["view"] = "home"
        st.rerun()


def render_jd_comparison_page() -> None:
    import streamlit as st

    job = st.session_state.get("jd_job")
    if not job:
        st.session_state["view"] = "home"
        st.rerun()
        return

    # Render loading screen 1 lần rồi chạy API ngay (giống scanning.py —
    # spinner + render result → rerun để chuyển sang trang kết quả).
    render_scanning(
        title="🐾 Shiba đang so sánh CV với JD…",
        quotes=(
            "Đang bóc tách văn bản từ CV & JD…",
            "Trích kỹ năng & đối chiếu hai hồ sơ…",
            "Sinh nhận xét cá nhân hóa cho JD này, gâu gâu! 🐶",
        ),
        steps=(
            "Bóc tách văn bản CV & JD",
            "Trích xuất kỹ năng ứng viên (hybrid regex + LLM)",
            "Trích kỹ năng yêu cầu từ JD",
            "Tính Semantic Similarity & Weighted Skill Score",
            "Sinh AI CV Review cho JD cụ thể",
        ),
    )

    logger.info(f"Running compare_cv_with_jd: cv={job.get('cv_filename')}, jd={job.get('jd_filename')}")

    try:
        if job.get("use_saved"):
            # CV đã lưu theo tài khoản (Authentication) — không cần upload lại.
            result = compare_cv_with_jd_saved(
                user_id=job["user_id"],
                jd_bytes=job["jd_bytes"],
                jd_filename=job["jd_filename"],
            )
        else:
            result = compare_cv_with_jd(
                cv_bytes=job["cv_bytes"],
                cv_filename=job["cv_filename"],
                jd_bytes=job["jd_bytes"],
                jd_filename=job["jd_filename"],
            )
        logger.info(f"compare_cv_with_jd OK: matched={len(result.get('matched_skills', []))} skills, "
                    f"missing={len(result.get('missing_skills', []))}")
    except APIError as e:
        logger.error(f"APIError: {e}")
        st.session_state.pop("jd_job", None)
        _fail(st, f"Lỗi so sánh: {e}")
        return
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        st.session_state.pop("jd_job", None)
        _fail(st, f"Lỗi không xác định: {e}")
        return

    _attach_cv_improvement(result)
    st.session_state["jd_result"] = result
    st.session_state.pop("jd_job", None)
    st.session_state.pop("jd_application_email", None)  # JD mới → xóa email của JD cũ
    st.session_state["view"] = "jd_result"
    st.rerun()


def render_jd_result() -> None:
    import streamlit as st

    result = st.session_state.get("jd_result")
    if not result:
        st.session_state["view"] = "home"
        st.rerun()
        return

    matched_count = len(result.get("matched_skills", []))
    total_jd_skills = len(result.get("jd_skills", []))
    coverage_pct = result.get("coverage_pct", 0.0)

    # ── Header ───────────────────────────────────────────────────────────────
    hdr_l, hdr_r = st.columns([3, 1])
    with hdr_l:
        st.markdown(
            f"""
            <div class="eyebrow">Bước 4 · Kết quả so sánh</div>
            <div class="results-title">CV vs {html.escape(result.get('jd_position') or 'Job Description')}</div>
            <div class="results-sub">
              {result.get('jd_filename', '')} &nbsp;•&nbsp;
              {matched_count}/{total_jd_skills} kỹ năng khớp &nbsp;•&nbsp;
              Coverage {coverage_pct:.0%}
            </div>
            """,
            unsafe_allow_html=True,
        )
    with hdr_r:
        # Trước đây có 2 nút ("So sánh JD khác" / "Phân tích CV với nghề khác")
        # nhưng CÙNG hành vi (xóa jd_result+jd_job rồi về home) → gộp làm một.
        if st.button("← Quay lại", key="jd_back_home", use_container_width=True):
            for k in ("jd_result", "jd_job", "jd_application_email"):
                st.session_state.pop(k, None)
            st.session_state["view"] = "home"
            st.rerun()

    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

    # ── JD Summary ────────────────────────────────────────────────────────────
    with st.expander("📋 Nội dung JD đã tải lên", expanded=False):
        jd_preview = result.get("jd_text_preview", "")
        st.markdown(f"**Vị trí:** {html.escape(result.get('jd_position') or '(không xác định)')}")
        st.markdown(f"**Trích đoạn đầu JD:**\n{jd_preview[:800]}")
        if result.get("jd_skills"):
            st.markdown("**Kỹ năng yêu cầu (từ JD):**")
            render_skill_badges(result.get("jd_skills", []), kind="muted", max_items=30)

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

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

    # ── Skill Gap ─────────────────────────────────────────────────────────────
    sk_l, sk_r = st.columns(2, gap="medium")
    with sk_l:
        st.markdown('<div class="skill-sub-label green">● KỸ NĂNG ĐÁP ỨNG</div>', unsafe_allow_html=True)
        render_skill_badges(result.get("matched_skills", []), kind="matched",
                            empty_text="Chưa khớp kỹ năng nào của JD này.")
    with sk_r:
        st.markdown('<div class="skill-sub-label amber">● KỸ NĂNG CÒN THIẾU</div>', unsafe_allow_html=True)
        render_skill_badges(result.get("missing_skills", []), kind="missing", max_items=24,
                            empty_text="Tuyệt vời — không thiếu kỹ năng quan trọng nào.")

    # ── Coverage bar ─────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="section-h">📊 Coverage: {matched_count}/{total_jd_skills} kỹ năng JD ({coverage_pct:.0%})</div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(float(coverage_pct), text=f"{coverage_pct:.0%} kỹ năng yêu cầu được đáp ứng")

    # ── HERO: AI CV Review cho JD cụ thể ──────────────────────────────────────
    ai_rec = result.get("ai_recommendation")
    cv_review_data = result.get("cv_review") or {}
    # Ưu tiên ai_recommendation (dict), fallback về cv_review_data (dict)
    # Dùng "is not None" vì {} là falsy → không dùng `or`
    review = ai_rec if ai_rec is not None else cv_review_data
    if review:
        st.markdown('<div class="section-h">🤖 Nhận xét chi tiết từ Shiba AI</div>', unsafe_allow_html=True)
        render_cv_review(review)
    else:
        st.info(
            "📝 Không có AI Recommendation cho JD này (cần OPENAI_API_KEY để sinh nhận xét cá nhân hóa)."
        )

    # ── AI CV Improvement: tiếp nối AI CV Review, sinh tự động (nếu có) ───────
    if result.get("cv_improvement"):
        st.markdown('<div class="section-h">✍️ Gợi ý cải thiện CV</div>', unsafe_allow_html=True)
        render_cv_improvement(result["cv_improvement"])

    # ── AI Application Email: CHỈ sinh khi người dùng bấm nút ─────────────────
    st.markdown('<div class="section-h">✉️ Chuẩn bị ứng tuyển</div>', unsafe_allow_html=True)
    jd_application_email = st.session_state.get("jd_application_email")
    if jd_application_email:
        render_application_email(jd_application_email)
        if st.button("↻ Tạo lại email khác"):
            st.session_state.pop("jd_application_email", None)
            st.rerun()
    else:
        if st.button("✉️ Tạo email ứng tuyển", type="primary", key="jd_gen_email"):
            with st.spinner("Shiba đang soạn email ứng tuyển…"):
                try:
                    email = generate_application_email_for_jd(
                        candidate_profile=result.get("candidate_profile", {}),
                        jd_position=result.get("jd_position", ""),
                        jd_skills=result.get("jd_skills", []),
                        jd_text_preview=result.get("jd_text_preview", ""),
                        semantic_similarity_score=result["semantic_similarity_score"],
                        weighted_skill_score=result["weighted_skill_score"],
                        matched_skills=result.get("matched_skills", []),
                        missing_skills=result.get("missing_skills", []),
                        cv_review=review or None,
                    )
                except APIError as e:
                    st.error(f"Không tạo được email: {e}")
                    email = None
            if email:
                st.session_state["jd_application_email"] = email
                st.rerun()
            else:
                st.warning(
                    "CV chưa đủ thông tin để soạn email cá nhân hóa cho JD này, "
                    "hoặc dịch vụ AI hiện không khả dụng."
                )

    # ── Candidate extracted profile ───────────────────────────────────────────
    profile = result.get("candidate_profile") or {}
    with st.expander("Hồ sơ trích xuất từ CV", expanded=False):
        st.markdown("**Kỹ năng phát hiện được (hybrid regex + LLM):**")
        render_skill_badges(profile.get("skills", []), kind="muted", empty_text="(không có)")
        for label, key in [
            ("Kinh nghiệm", "experience"),
            ("Dự án", "projects"),
            ("Học vấn", "education"),
        ]:
            items = profile.get(key, [])
            st.markdown(f"**{label}**")
            if items:
                st.markdown("\n".join(f"- {html.escape(str(i))}" for i in items))
            else:
                st.markdown("<span class='hint'>(không có)</span>", unsafe_allow_html=True)

    render_footer()
