"""
domain.py – Dataclass domain dùng xuyên suốt Online Pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CandidateProfile:
    """
    Hồ sơ ứng viên trích từ CV (Bước 3-4).

    Attributes:
        skills:       Danh sách kỹ năng (regex, nhất quán với offline extractor).
        experience:   Danh sách mục kinh nghiệm làm việc (LLM trích).
        projects:     Danh sách dự án (LLM trích).
        education:    Danh sách học vấn (LLM trích).
        raw_text:     Toàn văn CV đã trích (để embed / debug).
    """

    skills: list[str] = field(default_factory=list)
    experience: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    education: list[str] = field(default_factory=list)
    raw_text: str = ""

    def to_dict(self) -> dict:
        return {
            "skills": self.skills,
            "experience": self.experience,
            "projects": self.projects,
            "education": self.education,
        }


@dataclass
class ScoreBreakdown:
    """
    Kết quả chấm điểm phù hợp (Bước 7-9).

    Tất cả điểm nằm trong [0, 1].
    """

    semantic_similarity_score: float
    weighted_skill_score: float
    match_score: float
    alpha: float
    beta: float

    def to_dict(self) -> dict:
        return {
            "semantic_similarity_score": self.semantic_similarity_score,
            "weighted_skill_score": self.weighted_skill_score,
            "match_score": self.match_score,
            "alpha": self.alpha,
            "beta": self.beta,
        }


@dataclass
class SkillGap:
    """
    Phân tích khoảng cách kỹ năng (Bước 10) — set difference.

    Attributes:
        matched_skills:  Kỹ năng ứng viên có & nghề yêu cầu.
        missing_skills:  Kỹ năng nghề yêu cầu nhưng ứng viên thiếu.
        extra_skills:    Kỹ năng ứng viên có nhưng nghề không liệt kê.
    """

    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    extra_skills: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "extra_skills": self.extra_skills,
        }


@dataclass
class AnalysisResult:
    """
    Kết quả phân tích hoàn chỉnh trả về cho client (Bước 7-11).
    """

    occupation_key: str
    occupation_display: str
    scores: ScoreBreakdown
    skill_gap: SkillGap
    candidate_profile: CandidateProfile
    ai_recommendation: Optional[str] = None
    # AI CV Review có cấu trúc (đầu ra TRUNG TÂM): overall_assessment, strengths,
    # missing_skills, cv_quality, recommendations, learning_roadmap.
    cv_review: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "occupation_key": self.occupation_key,
            "occupation_display": self.occupation_display,
            "match_score": self.scores.match_score,
            "semantic_similarity_score": self.scores.semantic_similarity_score,
            "weighted_skill_score": self.scores.weighted_skill_score,
            "matched_skills": self.skill_gap.matched_skills,
            "missing_skills": self.skill_gap.missing_skills,
            "extra_skills": self.skill_gap.extra_skills,
            "candidate_profile": self.candidate_profile.to_dict(),
            "ai_recommendation": self.ai_recommendation,
            "cv_review": self.cv_review,
        }
