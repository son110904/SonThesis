"""src.online.services – Tầng điều phối Online Pipeline."""

from src.online.services.occupation_loader import (
    list_occupations,
    get_occupation,
    OccupationNotFound,
)
from src.online.services.analysis_service import analyze_cv, review_occupation
from src.online.services.recommendation_service import recommend_occupations
from src.online.services.cv_improvement_service import generate_cv_improvement_for_occupation
from src.online.services.email_service import generate_application_email_for_occupation

__all__ = [
    "list_occupations",
    "get_occupation",
    "OccupationNotFound",
    "analyze_cv",
    "review_occupation",
    "recommend_occupations",
    "generate_cv_improvement_for_occupation",
    "generate_application_email_for_occupation",
]
