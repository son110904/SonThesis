"""home.py – Trang chủ: so sánh CV vs JD (chính) + chọn nghề thủ công (phụ)."""

from __future__ import annotations

import html
import logging

import streamlit as st

from src.frontend.utils.api_client import (
    APIError,
    activate_cv,
    delete_cv,
    download_cv,
    get_cv_history,
    get_cv_info,
    get_occupations,
    save_cv,
)
from src.frontend.utils.resources import is_model_ready, start_background_warmup
from src.frontend.utils.styling import img_tag, render_footer

logger = logging.getLogger(__name__)


@st.cache_data(show_spinner=False, ttl=300)
def _load_occupations() -> list[dict]:
    return get_occupations()


_STEPS = ("Tải CV", "Phân tích AI", "Báo cáo")

# JD dán tay ngắn hơn ngưỡng này gần như chắc chắn là dán thiếu/nhầm — chặn sớm
# để không tốn một lần gọi LLM cho nội dung không đủ căn cứ phân tích.
_MIN_JD_TEXT_CHARS = 50


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
        ("Skill Gap", "Kỹ năng đáp ứng &amp; còn thiếu cho JD."),
        ("Coverage Score", "Tỷ lệ kỹ năng yêu cầu được đáp ứng."),
        ("AI CV Review", "Nhận xét chi tiết cho tin tuyển dụng đó."),
        ("Learning Roadmap", "Lộ trình học tập cá nhân hóa theo CV."),
    ]
    feat_html = "".join(
        f'<div class="feature-card">'
        f'<div class="fc-title">{t}</div><div class="fc-desc">{d}</div></div>'
        for t, d in features
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


@st.dialog("Lịch sử CV đã tải")
def _cv_history_dialog(user_id: int) -> None:
    """
    Modal lịch sử CV.

    Dùng st.dialog (Streamlit >= 1.37): tự render cửa sổ nổi giữa màn hình kèm
    lớp nền mờ (backdrop) và nút đóng — không phải tự dựng overlay bằng CSS.
    """
    try:
        items = get_cv_history(user_id)
    except APIError as e:
        st.error(f"Không tải được lịch sử: {e}")
        return

    if not items:
        st.info("Bạn chưa tải lên CV nào.")
        return

    st.caption(f"Tổng cộng {len(items)} lần tải lên — mới nhất ở trên cùng.")
    for it in items:
        cv_id = it["id"]
        active = it.get("is_active", False)
        exists = it.get("exists", True)

        badge = (
            '<span class="cvh-badge cvh-current">Đang dùng</span>' if active
            else '<span class="cvh-badge cvh-old">CV cũ</span>'
        )
        missing = (
            '<span class="cvh-badge cvh-missing">Tệp không còn</span>' if not exists else ""
        )
        st.markdown(
            f"""
            <div class="cvh-row">
              <div class="cvh-main">
                <div class="cvh-name">{html.escape(it["original_filename"])}</div>
                <div class="cvh-time">Tải lên: {html.escape(str(it["uploaded_at"]))}</div>
              </div>
              <div class="cvh-tags">{badge}{missing}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Hàng nút cho từng mục. Tệp đã mất trên đĩa thì không tải về lẫn chọn
        # dùng lại được → chỉ hiện ghi chú thay vì nút bấm lỗi.
        if not exists:
            st.caption("Không thao tác được vì tệp gốc không còn trên máy chủ.")
            continue

        # Xóa là thao tác không hoàn tác được (mất cả bản ghi lẫn file gốc) nên
        # cần bấm 2 lần: lần đầu chỉ mở hàng xác nhận cho đúng mục đó.
        if st.session_state.get("cvh_confirm_del") == cv_id:
            st.warning("Xóa vĩnh viễn CV này khỏi lịch sử?")
            col_yes, col_no = st.columns(2, gap="small")
            with col_yes:
                if st.button("Xóa vĩnh viễn", key=f"cvh_del_yes_{cv_id}",
                             type="primary", use_container_width=True):
                    try:
                        delete_cv(user_id, cv_id)
                    except APIError as e:
                        st.error(f"Không xóa được CV: {e}")
                    else:
                        st.session_state.pop("cvh_confirm_del", None)
                        # scope="fragment": vẽ lại danh sách NGAY trong modal.
                        # st.rerun() thường sẽ đóng modal, làm người dùng không
                        # thấy được kết quả vừa xóa.
                        st.rerun(scope="fragment")
            with col_no:
                if st.button("Hủy", key=f"cvh_del_no_{cv_id}", use_container_width=True):
                    st.session_state.pop("cvh_confirm_del", None)
                    st.rerun(scope="fragment")
            continue

        col_dl, col_use, col_del = st.columns(3, gap="small")
        with col_dl:
            try:
                data, fname = download_cv(user_id, cv_id)
                st.download_button(
                    "Tải về",
                    data=data,
                    file_name=fname,
                    mime="application/octet-stream",
                    key=f"cvh_dl_{cv_id}",
                    use_container_width=True,
                )
            except APIError as e:
                st.caption(f"Không đọc được tệp: {e}")
        with col_use:
            if active:
                st.button("Đang dùng", key=f"cvh_use_{cv_id}",
                          disabled=True, use_container_width=True)
            elif st.button("Dùng CV này", key=f"cvh_use_{cv_id}",
                           type="primary", use_container_width=True):
                try:
                    activate_cv(user_id, cv_id)
                except APIError as e:
                    st.error(f"Không đổi được CV: {e}")
                else:
                    # Uploader đang mở (nếu có) phải đóng lại, nếu không trang
                    # vẫn hiện ô tải tệp thay vì CV vừa chọn.
                    st.session_state.pop("show_cv_uploader", None)
                    st.rerun()
        with col_del:
            # Backend chặn xóa CV đang dùng (409) để tài khoản không rơi vào
            # trạng thái không có CV nào — khóa nút ở đây cho khớp.
            if active:
                st.button("Xóa", key=f"cvh_del_{cv_id}", disabled=True,
                          use_container_width=True,
                          help="Hãy chọn một CV khác làm CV đang dùng trước khi xóa CV này.")
            elif st.button("Xóa", key=f"cvh_del_{cv_id}", use_container_width=True):
                st.session_state["cvh_confirm_del"] = cv_id
                st.rerun(scope="fragment")


def _save_cv_best_effort(user_id: int, cv_file) -> dict | None:
    """
    Lưu CV vào tài khoản để tái sử dụng lần sau — best-effort, không chặn luồng chính.

    Trả về thông tin CV đã lưu (có cờ ``duplicate``) hoặc None nếu lưu lỗi.
    """
    try:
        return save_cv(user_id, cv_file.getvalue(), cv_file.name)
    except APIError as e:
        logger.warning(f"Không lưu được CV cho user #{user_id}: {e}")
        return None


def _save_uploaded_cv_once(user_id: int, cv_file) -> dict | None:
    """
    Lưu tệp vừa chọn ở uploader, chỉ gọi backend MỘT lần cho mỗi tệp.

    Streamlit chạy lại toàn bộ script sau mỗi tương tác, mà backend chống trùng
    theo nội dung → gọi lại sẽ báo ``duplicate=True`` cho chính tệp người dùng
    vừa tải lên. Cache kết quả theo (tên, kích thước) để thông báo "CV đã tồn
    tại" chỉ xuất hiện khi tệp thực sự trùng với một CV cũ trong lịch sử.
    """
    sig = (user_id, cv_file.name, cv_file.size)
    cached = st.session_state.get("cv_upload_result")
    if cached and cached.get("sig") == sig:
        return cached.get("info")
    info = _save_cv_best_effort(user_id, cv_file)
    st.session_state["cv_upload_result"] = {"sig": sig, "info": info}
    return info


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
                '<div class="form-label" style="margin-bottom:0.4rem;">Tải lên CV</div>',
                unsafe_allow_html=True,
            )
            cv_file = st.file_uploader(
                "Tải lên CV (PDF, DOCX, Markdown)",
                type=["pdf", "docx", "md"],
                accept_multiple_files=False,
                label_visibility="collapsed",
                key="cv_uploader",
            )
            if cv_file is not None:
                saved = _save_uploaded_cv_once(user["id"], cv_file)
                if saved and saved.get("duplicate"):
                    st.info(
                        f"CV này đã tồn tại trong lịch sử "
                        f"(**{saved['original_filename']}**, tải lên {saved['uploaded_at']}). "
                        "Hệ thống dùng lại bản đã lưu thay vì tạo bản mới."
                    )
            if cv_info is not None and st.button("← Dùng CV đã lưu", key="cancel_replace_cv"):
                st.session_state["show_cv_uploader"] = False
                st.rerun()
        else:
            st.markdown(
                f"""
                <div class="privacy-note" style="display:flex;align-items:center;gap:0.5rem">
                  CV hiện tại: <strong>{html.escape(cv_info['original_filename'])}</strong>
                  &nbsp;•&nbsp; tải lên {html.escape(str(cv_info['uploaded_at']))}
                </div>
                """,
                unsafe_allow_html=True,
            )
            btn_replace, btn_history, _ = st.columns([1, 1, 1.4], gap="small")
            with btn_replace:
                if st.button("↻ Thay CV mới", key="show_replace_cv",
                             use_container_width=True):
                    st.session_state["show_cv_uploader"] = True
                    st.rerun()
            with btn_history:
                if st.button("Lịch sử CV", key="show_cv_history",
                             use_container_width=True):
                    # Mở modal lần mới phải sạch trạng thái xác nhận xóa của lần trước.
                    st.session_state.pop("cvh_confirm_del", None)
                    _cv_history_dialog(user["id"])

        st.markdown(
            '<div class="form-label" style="margin-top:1rem;margin-bottom:0.4rem;">Job Description</div>',
            unsafe_allow_html=True,
        )
        # Nhiều tin tuyển dụng chỉ có trên web, không tải file về được → cho phép
        # dán thẳng nội dung. Hai tab để người dùng chọn 1 trong 2 cách.
        tab_paste, tab_upload = st.tabs(["Dán nội dung JD", "Tải lên file JD"])
        with tab_paste:
            jd_text = st.text_area(
                "Dán nội dung tin tuyển dụng vào đây",
                height=200,
                placeholder="Dán toàn bộ mô tả công việc và yêu cầu ứng viên vào đây…",
                label_visibility="collapsed",
                key="jd_text_input",
            )
        with tab_upload:
            jd_file = st.file_uploader(
                "Tải lên Job Description (PDF, DOCX, Markdown)",
                type=["pdf", "docx", "md"],
                accept_multiple_files=False,
                label_visibility="collapsed",
                key="jd_uploader",
            )

        jd_text = (jd_text or "").strip()

        if not ready:
            st.caption("Shiba đang khởi động ở chế độ nền — bạn cứ nhập JD trước nhé.")
        st.markdown("<div style='margin-top:0.3rem'></div>", unsafe_allow_html=True)

        if st.button("So sánh với JD", use_container_width=True, type="primary"):
            # Ưu tiên file nếu người dùng cung cấp cả hai (file thường đầy đủ hơn).
            jd_payload = (
                {"jd_bytes": jd_file.getvalue(), "jd_filename": jd_file.name}
                if jd_file is not None
                else {"jd_text": jd_text, "jd_filename": "JD dán trực tiếp"}
            )
            if show_uploader and cv_file is None:
                st.warning("Vui lòng tải lên file CV trước.")
            elif jd_file is None and len(jd_text) < _MIN_JD_TEXT_CHARS:
                st.warning(
                    f"Vui lòng dán nội dung JD (ít nhất {_MIN_JD_TEXT_CHARS} ký tự) "
                    "hoặc tải lên file JD."
                )
            elif show_uploader:
                _save_uploaded_cv_once(user["id"], cv_file)
                st.session_state["jd_job"] = {
                    "cv_bytes": cv_file.getvalue(),
                    "cv_filename": cv_file.name,
                    **jd_payload,
                }
                st.session_state.pop("show_cv_uploader", None)
                st.session_state["view"] = "jd_comparison"
                st.rerun()
            else:
                st.session_state["jd_job"] = {
                    "use_saved": True,
                    "user_id": user["id"],
                    **jd_payload,
                }
                st.session_state["view"] = "jd_comparison"
                st.rerun()

        st.markdown(
            '<div class="privacy-note">Dữ liệu của bạn được bảo mật tuyệt đối bởi ShibaCV Guard.</div>',
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
                    _save_uploaded_cv_once(user["id"], cv_file)
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
