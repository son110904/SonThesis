"""auth.py – Trang Đăng nhập / Đăng ký.

Authentication chỉ hỗ trợ trải nghiệm: lưu CV theo tài khoản để tái sử dụng ở
các lần phân tích sau, không phải hệ thống quản lý người dùng đầy đủ.
"""

from __future__ import annotations

from src.frontend.utils.api_client import APIError, login, register
from src.frontend.utils.styling import render_footer


def render_auth_page() -> None:
    import streamlit as st

    st.markdown(
        """
        <div style="padding-top:0.4rem">
          <div class="eyebrow">Bắt đầu</div>
          <div class="page-h1">Đăng nhập để tiếp tục</div>
          <div class="page-h1-sub">
            Lưu CV của bạn và tái sử dụng ở mọi lần phân tích — không cần tải lên lại.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    _, col_center, _ = st.columns([1, 1.3, 1])
    with col_center:
        tab_login, tab_register = st.tabs(["Đăng nhập", "Đăng ký"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Mật khẩu", type="password", key="login_password")
                submitted = st.form_submit_button(
                    "Đăng nhập", use_container_width=True, type="primary"
                )
            if submitted:
                if not email or not password:
                    st.warning("Vui lòng nhập email và mật khẩu.")
                else:
                    try:
                        user = login(email, password)
                    except APIError as e:
                        st.error(str(e))
                    else:
                        st.session_state["user"] = user
                        st.session_state["view"] = "home"
                        st.rerun()

        with tab_register:
            with st.form("register_form"):
                full_name = st.text_input("Họ và tên", key="reg_name")
                email_r = st.text_input("Email", key="reg_email")
                password_r = st.text_input(
                    "Mật khẩu", type="password", key="reg_password",
                    help="Ít nhất 6 ký tự",
                )
                submitted_r = st.form_submit_button(
                    "Đăng ký", use_container_width=True, type="primary"
                )
            if submitted_r:
                if not full_name or not email_r or not password_r:
                    st.warning("Vui lòng nhập đầy đủ họ tên, email và mật khẩu.")
                else:
                    try:
                        user = register(full_name, email_r, password_r)
                    except APIError as e:
                        st.error(str(e))
                    else:
                        st.session_state["user"] = user
                        st.session_state["view"] = "home"
                        st.rerun()

    render_footer()
