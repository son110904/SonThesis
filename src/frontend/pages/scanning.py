"""scanning.py – Trang quét CV (loading).

Xử lý job (theo session_state), vẽ hiệu ứng quét rồi gọi backend:
  • cv_job     → analyze_cv (chọn nghề thủ công từ dropdown) → result.
  • jd_job     → compare_cv_with_jd (so sánh CV vs JD) → jd_result.

Sau khi có kết quả (cv_job), tự động sinh thêm AI CV Improvement (tiếp nối AI CV
Review, KHÔNG cần người dùng bấm nút) — lỗi/không có LLM key thì bỏ qua lặng lẽ,
không chặn luồng chính.
"""

from __future__ import annotations

import logging

from src.frontend.utils.api_client import (
    APIError,
    analyze_cv,
    analyze_cv_saved,
    generate_cv_improvement,
)
from src.frontend.utils.styling import render_scanning

logger = logging.getLogger(__name__)


def _attach_cv_improvement(result: dict) -> None:
    """Sinh AI CV Improvement và gắn vào result (best-effort, không chặn luồng chính)."""
    try:
        result["cv_improvement"] = generate_cv_improvement(
            candidate_profile=result.get("candidate_profile", {}),
            occupation_key=result["occupation_key"],
            semantic_similarity_score=result["semantic_similarity_score"],
            weighted_skill_score=result["weighted_skill_score"],
            matched_skills=result.get("matched_skills", []),
            missing_skills=result.get("missing_skills", []),
        )
    except APIError as e:
        logger.warning(f"Bỏ qua AI CV Improvement: {e}")
        result["cv_improvement"] = None


def _fail(st, e: "APIError") -> None:
    """Hiển thị lỗi thân thiện theo loại + nút quay lại home."""
    # Overlay .scan-wrap (position:fixed, phủ toàn màn hình) đã render trước khi
    # gọi API — phải ẩn nó đi, nếu không error + nút quay lại bị che, user kẹt luôn.
    st.markdown("<style>.scan-wrap{display:none !important}</style>", unsafe_allow_html=True)
    msg = str(e)
    if "không phải là CV" in msg or "không phải CV" in msg:
        st.error(msg)
    elif "không được hỗ trợ" in msg or "không hỗ trợ" in msg:
        st.error(msg)
    else:
        st.error(f"Lỗi phân tích: {msg}")
    if st.button("← Quay lại"):
        st.session_state["view"] = "home"
        st.rerun()


def render_scanning_page() -> None:
    import streamlit as st

    cv_job = st.session_state.get("cv_job")

    if not cv_job:
        st.session_state["view"] = "home"
        st.rerun()
        return

    # Phân tích trực tiếp 1 nghề đã chọn thủ công (pipeline đầy đủ, 1 nghề).
    render_scanning(
        title="Shiba đang đánh giá CV của bạn…",
        quotes=(
            "Đang chấm điểm phù hợp với nghề…",
            "Phân tích điểm mạnh & kỹ năng còn thiếu…",
            "Soạn nhận xét chi tiết, sắp xong!",
        ),
        steps=(
            "Đọc & bóc tách văn bản CV",
            "Trích xuất kỹ năng & kinh nghiệm",
            "Tính vector ngữ nghĩa (embedding)",
            "Đối chiếu với nghề đã chọn",
            "Sinh nhận xét AI & lộ trình học tập",
        ),
    )

    try:
        if cv_job.get("use_saved"):
            # CV đã lưu theo tài khoản (Authentication) — không cần upload lại.
            result = analyze_cv_saved(
                user_id=cv_job["user_id"],
                occupation_key=cv_job["occupation_key"],
                include_recommendation=cv_job.get("include_recommendation", True),
            )
        else:
            result = analyze_cv(
                file_bytes=cv_job["file_bytes"],
                filename=cv_job["filename"],
                occupation_key=cv_job["occupation_key"],
                include_recommendation=cv_job.get("include_recommendation", True),
            )
    except APIError as e:
        st.session_state.pop("cv_job", None)
        _fail(st, e)
        return
    _attach_cv_improvement(result)
    st.session_state["result"] = result
    st.session_state.pop("cv_job", None)
    st.session_state.pop("application_email", None)  # nghề mới → xóa email của nghề cũ
    st.session_state["view"] = "result"
    st.rerun()
