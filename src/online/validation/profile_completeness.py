"""
profile_completeness.py – Chặn "CV quá sơ sài" TRƯỚC khi gọi LLM sinh AI Review.

Một mentor thật sẽ không cố nhận xét sâu về một CV gần như trống. Thay vào đó họ
chỉ ra CV còn thiếu gì và yêu cầu bổ sung. Module này tái hiện đúng hành vi đó:

  • assess_profile_completeness(profile) → (is_sparse, missing_sections)
  • build_sparse_review(occupation, missing_sections) → dict CÙNG schema với AI CV
    Review (6 khóa) + cờ "_sparse" để tầng UI hiển thị dạng cảnh báo riêng.

Lợi ích: (1) không tốn 1 lần gọi LLM để nhận về nhận xét thiếu căn cứ; (2) hướng
dẫn người dùng cải thiện CV ngay tại chỗ. Hoạt động cả khi KHÔNG có API key.
"""

from __future__ import annotations

from src.config import MIN_PROFILE_SKILLS
from src.models import CandidateProfile


def assess_profile_completeness(
    profile: CandidateProfile,
) -> tuple[bool, list[str]]:
    """
    Đánh giá CV có đủ thông tin để nhận xét không.
    Returns:
        (is_sparse, missing_sections):
          is_sparse       — True nếu CV quá sơ sài để đánh giá chính xác.
          missing_sections— các mục cốt lõi đang trống/quá ít
    """
    missing: list[str] = []
    if len(profile.skills) < MIN_PROFILE_SKILLS:
        missing.append("kỹ năng chuyên môn")
    if not profile.experience:
        missing.append("kinh nghiệm làm việc")
    if not profile.projects:
        missing.append("dự án")

    too_few_skills = len(profile.skills) < MIN_PROFILE_SKILLS
    no_exp_and_proj = (not profile.experience) and (not profile.projects)
    is_sparse = too_few_skills or no_exp_and_proj
    return is_sparse, missing


def build_sparse_review(occupation_display: str, missing_sections: list[str]) -> dict:
    """
    Dựng "AI CV Review" dạng cảnh báo cho CV sơ sài — CÙNG schema 6 khóa để tầng UI
    render bình thường, kèm cờ `_sparse=True` để hiển thị nổi bật (không phải nhận
    xét chuẩn). KHÔNG gọi LLM.
    """
    if missing_sections:
        thieu = ", ".join(missing_sections)
        overall = (
            f"CV hiện tại còn quá sơ lược để hệ thống có thể đánh giá chính xác cho vị "
            f"trí \"{occupation_display}\". Cụ thể, chưa có thông tin về {thieu}. "
            f"Đề nghị bổ sung các mục này trước khi phân tích lại."
        )
    else:
        overall = (
            "CV hiện tại còn quá sơ lược để hệ thống có thể đánh giá chính xác. "
            "Đề nghị bổ sung kinh nghiệm làm việc, dự án và kỹ năng chuyên môn trước "
            "khi phân tích lại."
        )

    tips: list[str] = []
    if "kinh nghiệm làm việc" in missing_sections:
        tips.append(
            "Bổ sung mục Kinh nghiệm: mỗi vị trí nêu công ty, thời gian, vai trò và "
            "2-3 gạch đầu dòng mô tả công việc kèm kết quả (có số liệu nếu được)."
        )
    if "dự án" in missing_sections:
        tips.append(
            "Bổ sung mục Dự án: tên dự án, công nghệ/kỹ năng sử dụng, vai trò của bạn "
            "và kết quả đạt được."
        )
    if "kỹ năng chuyên môn" in missing_sections:
        tips.append(
            "Liệt kê rõ các kỹ năng chuyên môn (công cụ, ngôn ngữ, nền tảng) liên quan "
            "đến vị trí ứng tuyển — hiện hệ thống trích được quá ít để đánh giá."
        )
    tips.append("Sau khi bổ sung, tải lại CV để nhận đánh giá chi tiết và lộ trình phát triển.")

    return {
        "_sparse": True,
        "overall_assessment": overall,
        "strengths": [],
        "missing_skills": [],
        "cv_quality": [
            f"Thiếu mục: {', '.join(missing_sections)}." if missing_sections
            else "CV chưa có đủ nội dung cốt lõi (kinh nghiệm, dự án, kỹ năng)."
        ],
        "recommendations": tips,
        "learning_roadmap": [],
    }
