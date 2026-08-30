"""
schemas.py – Pydantic models cho request/response của FastAPI.

Tách riêng khỏi domain (src/models) để tầng web tự do thay đổi mà không ảnh
hưởng logic nghiệp vụ.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class OccupationItem(BaseModel):
    """1 nghề trong dropdown (hỗ trợ 2 cấp lĩnh vực → vị trí)."""

    key: str = Field(..., description="Key ổn định (tên file profile)")
    display: str = Field(..., description="Tên hiển thị")
    core_skill_count: int = 0
    parent_key: Optional[str] = None
    parent_display: Optional[str] = None
    sub_display: Optional[str] = None
    is_sub: bool = False


class OccupationListResponse(BaseModel):
    occupations: list[OccupationItem]


class CandidateProfileOut(BaseModel):
    skills: list[str] = []
    experience: list[str] = []
    projects: list[str] = []
    education: list[str] = []
    # Nội dung CV gốc — dùng cho CV Improvement (Grammar/Structure review) và
    # Application Email. Optional để không phá vỡ response cũ.
    raw_text: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """Kết quả endpoint POST /analyze."""

    occupation_key: str
    occupation_display: str

    # 2 chỉ số độc lập (đã bỏ match_score tổng hợp từ 2026-08).
    semantic_similarity_score: float = Field(..., ge=0, le=1)
    weighted_skill_score: float = Field(..., ge=0, le=1)

    matched_skills: list[str] = []
    missing_skills: list[str] = []
    extra_skills: list[str] = []

    candidate_profile: CandidateProfileOut
    ai_recommendation: Optional[str] = None
    # AI CV Review có cấu trúc — đầu ra trung tâm (6 phần). None nếu thiếu LLM.
    cv_review: Optional[dict] = None


class CVImprovementRequest(BaseModel):
    """Body endpoint POST /cv-improvement (tái dùng profile + điểm số đã tính)."""

    candidate_profile: dict
    occupation: str
    semantic_similarity_score: float = Field(..., ge=0, le=1)
    weighted_skill_score: float = Field(..., ge=0, le=1)
    matched_skills: list[str] = []
    missing_skills: list[str] = []


class ApplicationEmailRequest(BaseModel):
    """Body endpoint POST /application-email (chỉ gọi khi người dùng chủ động bấm nút)."""

    candidate_profile: dict
    occupation: str
    semantic_similarity_score: float = Field(..., ge=0, le=1)
    weighted_skill_score: float = Field(..., ge=0, le=1)
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    cv_review: Optional[dict] = None


# ══════════════════════════════════════════════════════════════════════════
# Authentication (đăng ký/đăng nhập + lưu CV tái sử dụng)
# ══════════════════════════════════════════════════════════════════════════
class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    full_name: str
    email: str


class CVInfoOut(BaseModel):
    original_filename: str
    uploaded_at: str
    # Chỉ /auth/cv (upload) điền giá trị thật; /auth/cv/{id} và /auth/cv/activate
    # trả None vì không có khái niệm "trùng lặp" ở hai thao tác đó.
    duplicate: Optional[bool] = None


class CVHistoryItemOut(BaseModel):
    """Một lần tải CV trong lịch sử của tài khoản."""

    id: int
    original_filename: str
    uploaded_at: str
    exists: bool       # file còn trên đĩa không (bản ghi cũ có thể đã mất file)
    is_active: bool    # có phải CV đang dùng để phân tích không


class CVHistoryOut(BaseModel):
    items: list[CVHistoryItemOut] = []


class ActivateCVRequest(BaseModel):
    """Body endpoint POST /auth/cv/activate — chọn CV trong lịch sử để dùng."""

    user_id: int
    cv_id: int


class AnalyzeSavedRequest(BaseModel):
    """Body endpoint POST /analyze-saved (dùng CV đã lưu của user, không upload lại)."""

    user_id: int
    occupation: str
    include_recommendation: bool = True


# ══════════════════════════════════════════════════════════════════════════
# JD Comparison (Chế độ 2 — so sánh trực tiếp CV ↔ JD cụ thể)
# ══════════════════════════════════════════════════════════════════════════
class JDComparisonResponse(BaseModel):
    """Kết quả endpoint POST /compare-jd — so sánh CV với 1 JD cụ thể."""

    # Thông tin JD (đã trích text)
    jd_filename: str
    jd_position: str = ""              # tên vị trí dự đoán (heuristic)
    jd_skills: list[str] = []         # skill trích từ JD (regex)
    jd_text_preview: str = ""         # ~500 ký tự đầu của JD

    # 2 chỉ số độc lập. KHÔNG có weighted_skill_score như chế độ chọn nghề: với
    # một tin tuyển dụng đơn lẻ không có dữ liệu thống kê để suy ra trọng số kỹ
    # năng, nên chế độ này dùng thẳng tỉ lệ đáp ứng.
    semantic_similarity_score: float = Field(..., ge=0, le=1)
    coverage_pct: float = Field(..., ge=0, le=1)  # matched/required

    matched_skills: list[str] = []
    missing_skills: list[str] = []

    candidate_profile: CandidateProfileOut
    # AI Recommendation cho JD cụ thể (cùng schema với AI CV Review).
    ai_recommendation: Optional[dict] = None
    cv_review: Optional[dict] = None


class JDCVImprovementRequest(BaseModel):
    """Body endpoint POST /jd/cv-improvement (tái dùng profile + điểm số đã tính)."""

    candidate_profile: dict
    jd_position: str = ""
    jd_skills: list[str] = []
    semantic_similarity_score: float = Field(..., ge=0, le=1)
    coverage_pct: float = Field(..., ge=0, le=1)
    matched_skills: list[str] = []
    missing_skills: list[str] = []


class JDApplicationEmailRequest(BaseModel):
    """Body endpoint POST /jd/application-email (chỉ gọi khi người dùng chủ động bấm nút).

    KHÔNG có `jd_position`: tên vị trí là kết quả đoán bằng heuristic nên có thể sai,
    mà email là thư gửi thật cho nhà tuyển dụng. LLM tự đọc `jd_text_preview`.
    """

    candidate_profile: dict
    jd_skills: list[str] = []
    jd_text_preview: str = ""
    semantic_similarity_score: float = Field(..., ge=0, le=1)
    coverage_pct: float = Field(..., ge=0, le=1)
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    cv_review: Optional[dict] = None

