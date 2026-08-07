"""home.py – Trang chủ: so sánh CV vs JD (chính) + chọn nghề thủ công (phụ)."""

from __future__ import annotations

import html
import logging

import streamlit as st

from src.frontend.utils.api_client import APIError, get_cv_info, get_occupations, save_cv
from src.frontend.utils.resources import is_model_ready, start_background_warmup
from src.frontend.utils.styling import img_tag, render_footer

logger = logging.getLogger(__name__)


@st.cache_data(show_spinner=False, ttl=300)
def _load_occupations() -> list[dict]:
    return get_occupations()


_STEPS = ("Tải CV", "Phân tích AI", "Báo cáo")


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
        ("Đọc &amp; bóc tách CV &amp; JD", True),
        ("Trích xuất kỹ năng &amp; đối chiếu", ready),
        ("Sinh nhận xét cá nhân hóa", False),
    ]
    line_html = "".join(
        f'<div class="assist-line {"on" if on else ""}"><span class="al-dot"></span>{txt}</div>'
        for txt, on in lines
    )
    features = [
        ("🧩", "Skill Gap", "Kỹ năng đáp ứng &amp; còn thiếu cho JD."),
        ("📊", "Coverage Score", "Tỷ lệ kỹ năng yêu cầu được đáp ứng."),
        ("✉️", "AI CV Review", "Nhận xét chi tiết cho tin tuyển dụng đó."),
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


def _save_cv_best_effort(user_id: int, cv_file) -> None:
    """Lưu CV vào tài khoản để tái sử dụng lần sau — best-effort, không chặn luồng chính."""
    try:
        save_cv(user_id, cv_file.getvalue(), cv_file.name)
    except APIError as e:
        logger.warning(f"Không lưu được CV cho user #{user_id}: {e}")


def render_home() -> None:
    start_background_warmup()
    ready = is_model_ready()

    # ── Guard: chức năng Authentication chỉ hỗ trợ lưu/tái dùng CV — chưa đăng
    # nhập thì bắt buộc qua trang auth trước (không có luồng ẩn danh song song).
    user = st.session_state.get("user")
    if not user:
        st.session_state["view"] = "auth"
        st.rerun()
        return

    cv_info = get_cv_info(user["id"])
    # "Thay CV mới" bấm 1 lần thì hiện uploader tới khi user thực sự nộp (hoặc
    # hủy) — không tự ẩn lại giữa chừng khi Streamlit rerun vì các tương tác khác.
    show_uploader = cv_info is None or st.session_state.get("show_cv_uploader", False)

    # ── Page header ───────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="padding-top:0.4rem">
          <div class="eyebrow">Bước 1 · Tải hồ sơ</div>
          <div class="page-h1">Cùng nâng cấp CV của bạn</div>
          <div class="page-h1-sub">
            Xin chào <strong>{html.escape(user['full_name'])}</strong> — so sánh CV với
            <strong>Job Description</strong> hoặc chọn nghề để Shiba AI đưa ra nhận xét cá nhân hóa.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_form, col_assist = st.columns([1.25, 0.75], gap="large")

    # ── Primary: CV + JD ──────────────────────────────────────────────────────
    with col_form:
        cv_file = None
        if show_uploader:
            st.markdown(
                '<div class="form-label" style="margin-bottom:0.4rem;">📄 Tải lên CV</div>',
                unsafe_allow_html=True,
            )
            cv_file = st.file_uploader(
                "📄 Tải lên CV (PDF, DOCX, Markdown)",
                type=["pdf", "docx", "md"],
                accept_multiple_files=False,
                label_visibility="collapsed",
                key="cv_uploader",
            )
            if cv_info is not None and st.button("← Dùng CV đã lưu", key="cancel_replace_cv"):
                st.session_state["show_cv_uploader"] = False
                st.rerun()
        else:
            st.markdown(
                f"""
                <div class="privacy-note" style="display:flex;align-items:center;gap:0.5rem">
                  📄 CV hiện tại: <strong>{html.escape(cv_info['original_filename'])}</strong>
                  &nbsp;•&nbsp; tải lên {html.escape(str(cv_info['uploaded_at']))}
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("↻ Thay CV mới", key="show_replace_cv"):
                st.session_state["show_cv_uploader"] = True
                st.rerun()

        st.markdown(
            '<div class="form-label" style="margin-top:1rem;margin-bottom:0.4rem;">📋 Tải lên Job Description</div>',
            unsafe_allow_html=True,
        )
        jd_file = st.file_uploader(
            "📋 Tải lên Job Description (PDF, DOCX, Markdown)",
            type=["pdf", "docx", "md"],
            accept_multiple_files=False,
            label_visibility="collapsed",
            key="jd_uploader",
        )

        if not ready:
            st.caption("🐾 Shiba đang khởi động ở chế độ nền — bạn cứ tải file lên trước nhé.")
        st.markdown("<div style='margin-top:0.3rem'></div>", unsafe_allow_html=True)

        if st.button("🔍  So sánh với JD", use_container_width=True, type="primary"):
            if show_uploader and cv_file is None:
                st.warning("Vui lòng tải lên file CV trước.")
            elif jd_file is None:
                st.warning("Vui lòng tải lên file JD trước.")
            elif show_uploader:
                _save_cv_best_effort(user["id"], cv_file)
                st.session_state["jd_job"] = {
                    "cv_bytes": cv_file.getvalue(),
                    "cv_filename": cv_file.name,
                    "jd_bytes": jd_file.getvalue(),
                    "jd_filename": jd_file.name,
                }
                st.session_state.pop("show_cv_uploader", None)
                st.session_state["view"] = "jd_comparison"
                st.rerun()
            else:
                st.session_state["jd_job"] = {
                    "use_saved": True,
                    "user_id": user["id"],
                    "jd_bytes": jd_file.getvalue(),
                    "jd_filename": jd_file.name,
                }
                st.session_state["view"] = "jd_comparison"
                st.rerun()

        st.markdown(
            '<div class="privacy-note">🔒 Dữ liệu của bạn được bảo mật tuyệt đối bởi ShibaCV Guard.</div>',
            unsafe_allow_html=True,
        )

        # ── Secondary: chọn nghề thủ công ─────────────────────────────────────
        with st.expander("Hoặc chọn nghề từ danh sách để phân tích"):
            try:
                occupations = _load_occupations()
            except APIError as e:
                st.error(f"Không tải được danh sách nghề. {e}")
                st.stop()
                return

            if not occupations:
                st.warning("Backend chưa có nghề nào. Hãy chạy offline pipeline trước.")
                st.stop()
                return

            fields = {o["parent_display"]: o["parent_key"] for o in occupations if not o["is_sub"]}
            positions_by_parent: dict = {}
            for o in occupations:
                if o["is_sub"]:
                    positions_by_parent.setdefault(o["parent_key"], [])
                    positions_by_parent[o["parent_key"]].append(
                        (o["sub_display"] or o["display"], o["key"])
                    )
            # Lĩnh vực KHÔNG có vị trí con nào (vd "Nhóm nghề khác") vẫn cần ít
            # nhất 1 lựa chọn cho selectbox — dùng chính tên lĩnh vực đó thay vì
            # nhãn "Tổng quát — toàn lĩnh vực" (đã bỏ theo yêu cầu).
            for field_display, pk in fields.items():
                positions_by_parent.setdefault(pk, [(field_display, pk)])

            field_display = st.selectbox(
                "Lĩnh vực nghề nghiệp",
                options=list(fields.keys()),
                index=0,
                key="sel_field",
            )
            parent_key = fields[field_display]
            # Fallback lý thuyết — mọi parent_key trong `fields` đều đã được
            # đảm bảo có mặt trong positions_by_parent ở trên.
            positions = positions_by_parent.get(parent_key, [(field_display, parent_key)])
            pos_map = dict(positions)
            pos_label = st.selectbox(
                "Vị trí việc làm",
                options=[lbl for lbl, _ in positions],
                index=0,
                key=f"sel_pos_{parent_key}",
            )
            occ_key = pos_map[pos_label]

            if st.button("Phân tích nghề này", use_container_width=True):
                if show_uploader and cv_file is None:
                    st.warning("Vui lòng tải lên file CV trước.")
                elif show_uploader:
                    _save_cv_best_effort(user["id"], cv_file)
                    st.session_state["cv_job"] = {
                        "file_bytes": cv_file.getvalue(),
                        "filename": cv_file.name,
                        "occupation_key": occ_key,
                        "include_recommendation": True,
                    }
                    st.session_state.pop("show_cv_uploader", None)
                    st.session_state["view"] = "scanning"
                    st.rerun()
                else:
                    st.session_state["cv_job"] = {
                        "use_saved": True,
                        "user_id": user["id"],
                        "occupation_key": occ_key,
                        "include_recommendation": True,
                    }
                    st.session_state["view"] = "scanning"
                    st.rerun()

        st.markdown(_step_flow_html(active=0), unsafe_allow_html=True)

    # ── Right: assistant panel ─────────────────────────────────────────────────
    with col_assist:
        st.markdown(_assistant_html(ready), unsafe_allow_html=True)

    render_footer()
