"""scanning.py – Trang quét CV (loading).

Xử lý 3 loại job (theo session_state), vẽ hiệu ứng quét rồi gọi backend:
  • pending_recommend → recommend_occupations → trang Top 3 (recommend).
  • pending_review    → review_occupation (tái dùng profile+embedding) → result.
  • cv_job (cũ)       → analyze_cv (chọn nghề thủ công trực tiếp) → result.
"""

from __future__ import annotations

from src.frontend.utils.api_client import (
    APIError,
    analyze_cv,
    recommend_occupations,
    review_occupation,
)
from src.frontend.utils.styling import render_scanning


def _fail(st, e: "APIError") -> None:
    """Hiển thị lỗi thân thiện theo loại + nút quay lại home."""
    # Overlay .scan-wrap (position:fixed, phủ toàn màn hình) đã render trước khi
    # gọi API — phải ẩn nó đi, nếu không error + nút quay lại bị che, user kẹt luôn.
    st.markdown("<style>.scan-wrap{display:none !important}</style>", unsafe_allow_html=True)
    msg = str(e)
    if "không phải là CV" in msg or "không phải CV" in msg:
        st.error("📄 " + msg)
    elif "không được hỗ trợ" in msg or "không hỗ trợ" in msg:
        st.error("📎 " + msg)
    else:
        st.error(f"Lỗi phân tích: {msg}")
    if st.button("← Quay lại"):
        st.session_state["view"] = "home"
        st.rerun()


def render_scanning_page() -> None:
    import streamlit as st

    rec_job = st.session_state.get("pending_recommend")
    review_job = st.session_state.get("pending_review")
    cv_job = st.session_state.get("cv_job")

    if not (rec_job or review_job or cv_job):
        st.session_state["view"] = "home"
        st.rerun()
        return

    # Loading rõ ràng theo từng luồng — console steps khớp ĐÚNG việc đang chạy.
    if rec_job:
        render_scanning(
            title="🐾 Shiba đang tìm nghề phù hợp nhất…",
            quotes=(
                "Đang đọc kỹ năng & kinh nghiệm trong CV…",
                "Đối chiếu với toàn bộ nhóm nghề…",
                "Xếp hạng Top 3 phù hợp nhất, gâu gâu! 🐶",
            ),
        )
    elif review_job:
        # Review tái dùng profile + embedding — KHÔNG trích xuất lại, chỉ 1 nghề.
        render_scanning(
            title="🐾 Chờ chút, Shiba đang đưa ra đánh giá chi tiết hơn…",
            quotes=(
                "Đang phân tích sâu điểm mạnh & điểm yếu…",
                "Đối chiếu kỹ năng với yêu cầu của nghề…",
                "Soạn nhận xét & lộ trình riêng cho bạn, sắp xong! 🐶",
            ),
            steps=(
                "Nạp hồ sơ ứng viên đã trích xuất",
                "Đối chiếu kỹ năng với nghề đã chọn",
                "Phân tích điểm mạnh & thiếu hụt",
                "Sinh nhận xét AI & lộ trình học tập",
            ),
        )
    else:
        # Phân tích trực tiếp 1 nghề đã chọn thủ công (pipeline đầy đủ, 1 nghề).
        render_scanning(
            title="🐾 Shiba đang đánh giá CV của bạn…",
            quotes=(
                "Đang chấm điểm phù hợp với nghề…",
                "Phân tích điểm mạnh & kỹ năng còn thiếu…",
                "Soạn nhận xét chi tiết, sắp xong! 🐶",
            ),
            steps=(
                "Đọc & bóc tách văn bản CV",
                "Trích xuất kỹ năng & kinh nghiệm",
                "Tính vector ngữ nghĩa (embedding)",
                "Đối chiếu với nghề đã chọn",
                "Sinh nhận xét AI & lộ trình học tập",
            ),
        )

    # ── 1) Gợi ý Top 3 nghề ──────────────────────────────────────────────────
    if rec_job:
        try:
            out = recommend_occupations(**rec_job)
        except APIError as e:
            st.session_state.pop("pending_recommend", None)
            _fail(st, e)
            return
        st.session_state["recommendations"] = out["recommendations"]
        st.session_state["candidate_profile"] = out["candidate_profile"]
        st.session_state["candidate_embedding"] = out["candidate_embedding"]
        st.session_state.pop("pending_recommend", None)
        st.session_state["view"] = "recommend"
        st.rerun()
        return

    # ── 2) Review nghề người dùng chọn từ Top 3 ──────────────────────────────
    if review_job:
        try:
            result = review_occupation(
                candidate_profile=st.session_state.get("candidate_profile", {}),
                candidate_embedding=st.session_state.get("candidate_embedding", []),
                occupation_key=review_job["occupation_key"],
                include_recommendation=st.session_state.get("include_rec", True),
            )
        except APIError as e:
            st.session_state.pop("pending_review", None)
            _fail(st, e)
            return
        st.session_state["result"] = result
        st.session_state.pop("pending_review", None)
        st.session_state["view"] = "result"
        st.rerun()
        return

    # ── 3) Phân tích trực tiếp (chọn nghề thủ công) ──────────────────────────
    try:
        result = analyze_cv(**cv_job)
    except APIError as e:
        st.session_state.pop("cv_job", None)
        _fail(st, e)
        return
    st.session_state["result"] = result
    st.session_state.pop("cv_job", None)
    st.session_state["view"] = "result"
    st.rerun()
