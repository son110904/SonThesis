"""
schemas.py – Pydantic models cho request/response của FastAPI.

Tách riêng khỏi domain (src/models) để tầng web tự do thay đổi mà không ảnh
hưởng logic nghiệp vụ.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class OccupationItem(BaseModel):
    """1 nghề trong dropdown."""

    key: str = Field(..., description="Key ổn định (tên file profile)")
    display: str = Field(..., description="Tên hiển thị")
    core_skill_count: int = 0


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


class HistoryItem(BaseModel):
    id: int
    created_at: str
    cv_filename: Optional[str] = None
    occupation_key: str
    occupation_display: Optional[str] = None
    match_score: Optional[float] = None
    semantic_similarity_score: Optional[float] = None
    weighted_skill_score: Optional[float] = None
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    candidate_profile: Optional[CandidateProfileOut] = None
    ai_recommendation: Optional[str] = None


class HistoryListResponse(BaseModel):
    items: list[HistoryItem]


class ErrorResponse(BaseModel):
    detail: str
