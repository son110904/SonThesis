"""landing.py – Trang chủ hero (redesign 2026: badge, trust row, workspace động)."""

from __future__ import annotations

from src.frontend.utils.styling import img_tag, render_footer


def _workspace_html() -> str:
    """Panel workspace động bên phải hero: Shiba + metric chip trôi + particle.

    Các con số ở đây mang tính MINH HỌA cho hero marketing (không phải kết quả thật
    của người dùng) — giống hero của các SaaS hiện đại.
    """
    # Dùng bản ĐÃ TÁCH NỀN (_cut) — bản thường có nền beige vuông đè lên glow/ring.
    shiba = img_tag("shiba_ai_cut.png", style="").replace("<img ", '<img class="ws-shiba" ')
    return f"""
    <div class="hero-workspace land-img-in">
      <div class="ws-glow"></div>
      <div class="ws-ring"></div>
      <div class="ws-ring r2"></div>
      <span class="ws-particle p1"></span><span class="ws-particle p2"></span>
      <span class="ws-particle p3"></span><span class="ws-particle p4"></span>
      {shiba}
      <div class="ws-chip c1">
        <span><span class="wc-k">Resume</span><br><span class="wc-v">Đã tải lên</span></span>
      </div>
      <div class="ws-chip c2">
        <span><span class="wc-k">ATS Match</span><br><span class="wc-v good">94%</span></span>
      </div>
      <div class="ws-chip c3">
        <span><span class="wc-k">Kỹ năng</span><br><span class="wc-v">Đã phát hiện 27 skills</span></span>
      </div>
      <div class="ws-chip c4">
        <span><span class="wc-k">Semantic</span><br><span class="wc-v">Đang khớp…</span></span>
      </div>
    </div>
    """


def render_landing() -> None:
    import streamlit as st

    col_l, col_r = st.columns([1.05, 0.95], gap="large")

    with col_l:
        st.markdown(
            """
            <div class="land-hero" style="padding: 2.4rem 0 0.5rem; min-height: 300px; display:flex; flex-direction:column; justify-content:center">
              <div class="land-rise" style="--d:0.03s">
                <span class="hero-badge">AI Career Intelligence</span>
              </div>
              <div class="hero-title land-rise" style="--d:0.12s">
                Nâng tầm sự nghiệp cùng<br>
                <span class="accent">Shiba Intelligence</span>
              </div>
              <div class="hero-subtitle land-rise" style="--d:0.22s">
                AI đọc &amp; đánh giá CV, so sánh trực tiếp với <strong>Job Description</strong> và
                vạch lộ trình phát triển riêng cho bạn — chỉ trong vài giây.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        # Hiệu ứng vào trang cho nút CTA áp qua class .st-key-cta_hero (styling.py) —
        # KHÔNG wrap bằng st.markdown vì mỗi block markdown tự đóng thẻ HTML.
        if st.button("Bắt đầu ngay →", key="cta_hero"):
            # Đã đăng nhập (còn trong session) → vào thẳng home; chưa thì phải
            # đăng nhập/đăng ký trước (luồng: Đăng ký → Đăng nhập → Upload CV).
            st.session_state["view"] = "home" if st.session_state.get("user") else "auth"
            st.rerun()

        st.markdown(
            """
            <div class="trust-row land-rise" style="--d:0.4s">
              <span class="trust-item"><span class="tick">✓</span> Tương thích ATS</span>
              <span class="trust-item"><span class="tick">✓</span> Ứng dụng AI</span>
              <span class="trust-item"><span class="tick">✓</span> Bảo mật tuyệt đối</span>
              <span class="trust-item"><span class="tick">✓</span> So sánh CV ↔ JD</span>
            </div>
            <div class="social-proof land-rise" style="--d:0.5s">
              <div class="sp-label">Được xây dựng trên nền tảng công nghệ</div>
              <div class="sp-row">
                <span class="sp-badge">gte-multilingual</span>
                <span class="sp-badge">GPT-4o</span>
                <span class="sp-badge">97 nhóm nghề</span>
                <span class="sp-badge">Semantic Matching</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_r:
        st.markdown(_workspace_html(), unsafe_allow_html=True)

    render_footer()
