"""home.py – Trang upload CV (redesign 2026: 2 cột, step flow, assistant panel)."""

from __future__ import annotations

import html
import logging

import streamlit as st

from src.frontend.utils.api_client import APIError, get_occupations
from src.frontend.utils.resources import is_model_ready, start_background_warmup
from src.frontend.utils.styling import img_tag, render_footer

logger = logging.getLogger(__name__)


@st.cache_data(show_spinner=False, ttl=300)
def _load_occupations() -> list[dict]:
    return get_occupations()


_STEPS = ("Tải CV", "Phân tích AI", "Gợi ý nghề", "Báo cáo")


def _step_flow_html(active: int = 0) -> str:
    parts = []
    for i, label in enumerate(_STEPS):
        cls = "active" if i == active else ("done" if i < active else "")
        parts.append(
            f'<div class="step-item {cls}"><div class="step-dot">{i + 1}</div>'
            f'<div class="step-label">{html.escape(label)}</div></div>'
        )
    return f'<div class="step-flow">{"".join(parts)}</div>'


def _assistant_html(ready: bool) -> str:
    avatar = img_tag("shiba_ai.png", style="").replace("<img ", '<img class="ah-avatar" ')
    status = "Sẵn sàng phân tích" if ready else "Đang khởi động engine…"
    lines = [
        ("Đọc &amp; bóc tách CV", True),
        ("Trích xuất kỹ năng &amp; kinh nghiệm", ready),
        ("Đối chiếu 97+ nhóm nghề", False),
        ("Sinh nhận xét &amp; lộ trình", False),
    ]
    line_html = "".join(
        f'<div class="assist-line {"on" if on else ""}"><span class="al-dot"></span>{txt}</div>'
        for txt, on in lines
    )
    features = [
        ("🎯", "Phân tích ATS", "Chấm độ tương thích với hệ thống lọc hồ sơ."),
        ("🧩", "Skill Gap", "Kỹ năng đang có &amp; còn thiếu cho nghề."),
        ("🧭", "Career Match", "Top nghề phù hợp nhất với hồ sơ của bạn."),
        ("🗺️", "Learning Roadmap", "Lộ trình học tập cá nhân hóa theo CV."),
    ]
    feat_html = "".join(
        f'<div class="feature-card"><span class="fc-ico">{ic}</span>'
        f'<div class="fc-title">{t}</div><div class="fc-desc">{d}</div></div>'
        for ic, t, d in features
    )
    return f"""
    <div class="assist-panel">
      <div class="assist-head">
        {avatar}
        <div>
          <div class="ah-title">Trợ lý Shiba AI</div>
          <div class="ah-sub"><span class="live"></span> {status}</div>
        </div>
      </div>
      <div class="assist-status">{line_html}</div>
      <div class="assist-divider"></div>
      <div class="eyebrow" style="margin-bottom:0.7rem">Bạn sẽ nhận được</div>
      <div class="feature-grid">{feat_html}</div>
    </div>
    """


def render_home() -> None:
    # Đảm bảo prewarm nền đã chạy (idempotent) — KHÔNG chặn trang.
    start_background_warmup()
    ready = is_model_ready()

    st.markdown(
        """
        <div style="padding-top:0.4rem">
          <div class="eyebrow">Bước 1 · Tải hồ sơ</div>
          <div class="page-h1">Cùng nâng cấp CV của bạn</div>
          <div class="page-h1-sub">
            Tải CV lên — Shiba AI sẽ gợi ý <strong>Top 3 nghề phù hợp nhất</strong> với bạn,
            rồi đưa ra nhận xét chi tiết cho nghề bạn chọn.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        occupations = _load_occupations()
    except APIError as e:
        st.error(f"Không tải được danh sách nghề. {e}")
        st.info("Hãy chắc chắn backend đang chạy: `uvicorn src.api.main:app`")
        return

    if not occupations:
        st.warning("Backend chưa có nghề nào. Hãy chạy offline pipeline trước.")
        return

    fields = {o["parent_display"]: o["parent_key"] for o in occupations if not o["is_sub"]}
    positions_by_parent: dict[str, list[tuple[str, str]]] = {
        pk: [("Tổng quát — toàn lĩnh vực", pk)] for pk in fields.values()
    }
    for o in occupations:
        if o["is_sub"]:
            positions_by_parent.setdefault(
                o["parent_key"], [("Tổng quát — toàn lĩnh vực", o["parent_key"])]
            )
            positions_by_parent[o["parent_key"]].append(
                (o["sub_display"] or o["display"], o["key"])
            )

    col_form, col_assist = st.columns([1.25, 0.75], gap="large")

    # ── Left: upload zone + controls + step flow ─────────────────────────────
    with col_form:
        uploaded = st.file_uploader(
            "Tải lên hồ sơ (PDF, DOCX, Markdown)",
            type=["pdf", "docx", "md"],
            accept_multiple_files=False,
            help="Chấp nhận PDF, DOCX hoặc Markdown (.md). File .doc cũ vui lòng lưu lại .docx.",
            label_visibility="collapsed",
        )

        include_rec = st.toggle(
            "Sinh nhận xét AI chi tiết", value=True,
            help="Bật GPT-4o để sinh AI CV Review khi xem 1 nghề.",
        )

        if not ready:
            st.caption("🐾 Shiba đang khởi động ở chế độ nền — bạn cứ tải CV lên trước nhé.")
        st.markdown("<div style='margin-top:0.3rem'></div>", unsafe_allow_html=True)

        # CTA chính — gợi ý Top 3 nghề phù hợp nhất.
        if st.button("✦  Gợi ý nghề phù hợp", use_container_width=True, type="primary"):
            if uploaded is None:
                st.warning("Vui lòng tải lên file CV trước.")
            else:
                st.session_state["pending_recommend"] = {
                    "file_bytes": uploaded.getvalue(),
                    "filename": uploaded.name,
                }
                st.session_state["include_rec"] = include_rec
                st.session_state["view"] = "scanning"
                st.rerun()

        st.markdown(
            '<div class="privacy-note">🔒 Dữ liệu của bạn được bảo mật tuyệt đối bởi ShibaCV Guard.</div>',
            unsafe_allow_html=True,
        )

        # ── Lựa chọn phụ: tự chọn nghề cụ thể (giữ luồng cũ) ─────────────────
        with st.expander("Hoặc tôi đã biết nghề muốn ứng tuyển"):
            field_display = st.selectbox(
                "Lĩnh vực nghề nghiệp",
                options=list(fields.keys()),
                index=0,
                key="sel_field",
            )
            parent_key = fields[field_display]
            positions = positions_by_parent.get(parent_key, [("Tổng quát — toàn lĩnh vực", parent_key)])

            pos_map = dict(positions)
            pos_label = st.selectbox(
                "Vị trí việc làm",
                options=[lbl for lbl, _ in positions],
                index=0,
                key=f"sel_pos_{parent_key}",
                help="Chọn vị trí cụ thể để chấm điểm sát hơn (nếu có).",
            )
            occ_key = pos_map[pos_label]

            if st.button("Phân tích nghề này", use_container_width=True, key="manual_analyze"):
                if uploaded is None:
                    st.warning("Vui lòng tải lên file CV trước.")
                else:
                    st.session_state["cv_job"] = {
                        "file_bytes": uploaded.getvalue(),
                        "filename": uploaded.name,
                        "occupation_key": occ_key,
                        "include_recommendation": include_rec,
                    }
                    st.session_state["view"] = "scanning"
                    st.rerun()

        # Step indicator (bước 1 đang active).
        st.markdown(_step_flow_html(active=0), unsafe_allow_html=True)

    # ── Right: sticky assistant panel + feature cards ────────────────────────
    with col_assist:
        st.markdown(_assistant_html(ready), unsafe_allow_html=True)

    render_footer()
