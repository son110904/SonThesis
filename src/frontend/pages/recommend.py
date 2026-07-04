"""recommend.py – Trang Career Recommendation: hiển thị Top 3 nghề phù hợp nhất.

Người dùng chọn 1 nghề để xem AI CV Review chi tiết (sinh khi chọn, không sinh sẵn
cho cả 3 để tiết kiệm LLM). Muốn nghề khác → tải lại CV, dùng chọn thủ công ở trang chủ.
"""

from __future__ import annotations

import html

from src.frontend.utils.styling import render_footer, score_color


def _go_review(occupation_key: str) -> None:
    import streamlit as st
    st.session_state["pending_review"] = {"occupation_key": occupation_key}
    st.session_state["view"] = "scanning"
    st.rerun()


def _confidence(pct: float) -> tuple[str, str, str]:
    """Nhãn độ phù hợp suy ra TRỰC TIẾP từ match score (không bịa dữ liệu ngoài)."""
    if pct >= 70:
        return "Độ phù hợp cao", "var(--good-bg)", "var(--good)"
    if pct >= 40:
        return "Phù hợp một phần", "var(--warn-bg)", "var(--warn)"
    return "Cần cân nhắc", "var(--bad-bg)", "var(--bad)"


def render_recommend_page() -> None:
    import streamlit as st

    recs = st.session_state.get("recommendations")
    if not recs:
        st.session_state["view"] = "home"
        st.rerun()
        return

    st.markdown(
        """
        <div style="padding-top:0.3rem">
          <div class="eyebrow">Bước 3 · Gợi ý nghề nghiệp</div>
          <div class="results-title">Top nghề phù hợp với bạn</div>
          <div class="results-sub">
            Shiba AI đã đối chiếu CV của bạn với toàn bộ nhóm nghề. Chọn một nghề
            để xem <strong>nhận xét chi tiết</strong> và lộ trình phát triển.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

    medals = ["🥇", "🥈", "🥉"]
    ranks = ["#1 · Phù hợp nhất", "#2", "#3"]
    cols = st.columns(len(recs), gap="medium")
    for i, (col, r) in enumerate(zip(cols, recs)):
        pct = round(r["match_score"] * 100, 1)
        sem = round(r["semantic_similarity_score"] * 100, 1)
        wgt = round(r["weighted_skill_score"] * 100, 1)
        color = score_color(r["match_score"])
        confidence, cf_bg, cf_fg = _confidence(pct)
        with col:
            st.markdown(
                f"""
                <div class="rec-card {'top' if i == 0 else ''}">
                  <div class="rec-rank">{medals[i] if i < len(medals) else '⭐'}
                    <span>{ranks[i] if i < len(ranks) else f'#{i+1}'}</span></div>
                  <div class="rec-occ">{html.escape(r['occupation_display'])}</div>
                  <div class="rec-score" style="color:{color}">{pct:g}<span>/100</span></div>
                  <div class="rec-conf" style="background:{cf_bg};color:{cf_fg}">{confidence}</div>
                  <div class="rec-metric">
                    <div class="rm-row"><span>🧠 Semantic</span><b>{sem:g}</b></div>
                    <div class="rm-track"><div class="rm-fill" style="width:{sem}%;background:{color}"></div></div>
                    <div class="rm-row" style="margin-top:0.6rem"><span>⭐ Kỹ năng</span><b>{wgt:g}</b></div>
                    <div class="rm-track"><div class="rm-fill" style="width:{wgt}%;background:{color}"></div></div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
            if st.button("Xem đánh giá chi tiết", key=f"rec_{i}",
                         use_container_width=True, type="primary" if i == 0 else "secondary"):
                _go_review(r["occupation_key"])

    st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)

    # ── Quay lại upload CV khác ──────────────────────────────────────────────
    if st.button("← Tải lên CV khác", key="back_home"):
        for k in ("recommendations", "candidate_profile", "candidate_embedding", "result"):
            st.session_state.pop(k, None)
        st.session_state["view"] = "home"
        st.rerun()

    render_footer()
