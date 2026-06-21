"""home.py – Trang upload CV."""

from __future__ import annotations

import logging

from src.frontend.utils.api_client import APIError, analyze_cv, get_occupations
from src.frontend.utils.styling import img_tag, render_footer

logger = logging.getLogger(__name__)


def _load_occupations() -> list[dict]:
    import streamlit as st

    @st.cache_data(show_spinner=False, ttl=300)
    def _fetch() -> list[dict]:
        return get_occupations()

    return _fetch()


def render_home() -> None:
    import streamlit as st

    st.markdown(
        """
        <div style="padding-top:0.5rem">
          <div class="page-h1">Cùng nâng cấp CV của bạn</div>
          <div class="page-h1-sub">
            Hãy tải CV của bạn lên và chọn lĩnh vực nghề nghiệp của mình.
            Shiba AI sẽ lo phần còn lại.
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

    # Cấu trúc 2 cấp: lĩnh vực (cha) → vị trí (con).
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

    col_form, col_shiba = st.columns([1.15, 0.85], gap="large")

    # ── Left: form ───────────────────────────────────────────────────────────
    with col_form:
        uploaded = st.file_uploader(
            "Tải lên hồ sơ (PDF, DOCX)",
            type=["pdf", "docx"],
            accept_multiple_files=False,
            help="Kéo thả hoặc nhấn để chọn tệp",
        )

        # Cấp 1 — lĩnh vực (ĐẶT NGOÀI form để đổi lĩnh vực sẽ cập nhật list vị trí).
        st.markdown(
            """
            <div class="field-label">
              <span class="fl-icon">📁</span>
              <span>Lĩnh vực nghề nghiệp của bạn</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        field_display = st.selectbox(
            "Lĩnh vực nghề nghiệp",
            options=list(fields.keys()),
            index=0,
            key="sel_field",
            label_visibility="collapsed",
        )
        parent_key = fields[field_display]
        positions = positions_by_parent.get(parent_key, [("Tổng quát — toàn lĩnh vực", parent_key)])

        # Cấp 2 — vị trí trong lĩnh vực. Key gắn theo parent_key để đổi lĩnh vực thì reset.
        st.markdown(
            """
            <div class="field-label">
              <span class="fl-icon">🎯</span>
              <span>Vị trí việc làm</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        pos_map = dict(positions)
        pos_label = st.selectbox(
            "Vị trí việc làm",
            options=[lbl for lbl, _ in positions],
            index=0,
            key=f"sel_pos_{parent_key}",
            label_visibility="collapsed",
            help="Chọn vị trí cụ thể để chấm điểm sát hơn (nếu có).",
        )
        occ_key = pos_map[pos_label]

        with st.form("analyze_form", clear_on_submit=False):
            include_rec = st.toggle("Sinh khuyến nghị AI", value=True)
            st.markdown("<div style='margin-top:0.6rem'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("✦  Phân tích bằng AI", use_container_width=True)
            st.markdown(
                '<div class="privacy-note">🔒 Dữ liệu của bạn được bảo mật tuyệt đối bởi ShibaCV Guard.</div>',
                unsafe_allow_html=True,
            )

    # ── Right: shiba + cards ─────────────────────────────────────────────────
    with col_shiba:
        st.markdown(
            img_tag("shiba_ai.png", style="width:100%;max-width:320px;height:auto;display:block;margin:0 auto"),
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="shiba-ready-card">
              <div class="rct-label">🐾 Shiba đang sẵn sàng giúp bạn!</div>
              <div class="rct-quote">
                "Tôi sẽ quét qua hàng ngàn tiêu chuẩn tuyển dụng để đảm bảo
                CV của bạn luôn dẫn đầu xu hướng thị trường."
              </div>
            </div>
            <div class="stats-row">
              <div class="stat-chip">
                <div class="s-icon">✅</div>
                <div class="s-main">Chính xác 99%</div>
                <div class="s-sub">Phân tích sâu ATS</div>
              </div>
              <div class="stat-chip">
                <div class="s-icon">⚡</div>
                <div class="s-main">Tốc độ Shiba</div>
                <div class="s-sub">Xong trong 15s</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Submit ───────────────────────────────────────────────────────────────
    if submitted:
        if uploaded is None:
            st.warning("Vui lòng tải lên file CV trước.")
            return
        with st.spinner("Đang trích xuất CV, embed và đánh giá độ phù hợp…"):
            try:
                result = analyze_cv(
                    file_bytes=uploaded.getvalue(),
                    filename=uploaded.name,
                    occupation_key=occ_key,
                    include_recommendation=include_rec,
                )
            except APIError as e:
                st.error(f"Lỗi phân tích: {e}")
                return
        st.session_state["result"] = result
        st.session_state["view"] = "result"
        st.rerun()

    render_footer()
