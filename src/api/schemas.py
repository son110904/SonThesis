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


class AnalyzeResponse(BaseModel):
    """Kết quả endpoint POST /analyze."""

    occupation_key: str
    occupation_display: str

    match_score: float = Field(..., ge=0, le=1)
    semantic_similarity_score: float = Field(..., ge=0, le=1)
    weighted_skill_score: float = Field(..., ge=0, le=1)

    matched_skills: list[str] = []
    missing_skills: list[str] = []
    extra_skills: list[str] = []

    candidate_profile: CandidateProfileOut
    ai_recommendation: Optional[str] = None
    # AI CV Review có cấu trúc — đầu ra trung tâm (6 phần). None nếu thiếu LLM.
    cv_review: Optional[dict] = None


class RecommendationItem(BaseModel):
    """1 nghề trong Top-K gợi ý."""

    occupation_key: str
    occupation_display: str
    match_score: float = Field(..., ge=0, le=1)
    semantic_similarity_score: float = Field(..., ge=0, le=1)
    weighted_skill_score: float = Field(..., ge=0, le=1)
    # Giải thích "vì sao phù hợp" (deterministic, không LLM).
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    reason: str = ""


class RecommendationResponse(BaseModel):
    """Kết quả endpoint POST /recommend."""

    recommendations: list[RecommendationItem]
    candidate_profile: dict          # skills/experience/projects/education/raw_text/filename
    candidate_embedding: list[float]  # tái dùng cho /review


class ReviewRequest(BaseModel):
    """Body endpoint POST /review (chọn 1 nghề từ Top-K, tái dùng profile + embedding)."""

    candidate_profile: dict
    candidate_embedding: list[float]
    occupation: str
    include_recommendation: bool = True
