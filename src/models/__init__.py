"""
src.models – Các kiểu dữ liệu domain dùng chung cho Online Pipeline.

Tách riêng khỏi Pydantic schema của API (src/api/schemas.py) để các module
nghiệp vụ (src/online/*) không phụ thuộc vào tầng web.
"""

from src.models.domain import (
    CandidateProfile,
    ScoreBreakdown,
    SkillGap,
    AnalysisResult,
)

__all__ = [
    "CandidateProfile",
    "ScoreBreakdown",
    "SkillGap",
    "AnalysisResult",
]
