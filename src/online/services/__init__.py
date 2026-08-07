"""src.online.services – Tầng điều phối Online Pipeline."""

from src.online.services.occupation_loader import (
    list_occupations,
    get_occupation,
    OccupationNotFound,
)
from src.online.services.analysis_service import analyze_cv
from src.online.services.cv_improvement_service import generate_cv_improvement_for_occupation
from src.online.services.email_service import generate_application_email_for_occupation
from src.online.services.jd_comparison_service import (
    compare_cv_with_jd,
    generate_cv_improvement_for_jd,
    generate_application_email_for_jd,
)
from src.online.services.auth_service import (
    register_user,
    login_user,
    save_cv_for_user,
    get_cv_info_for_user,
    analyze_cv_for_saved_user,
    compare_saved_cv_with_jd,
    InvalidCredentialsError,
    NoSavedCVError,
)

__all__ = [
    "list_occupations",
    "get_occupation",
    "OccupationNotFound",
    "analyze_cv",
    "generate_cv_improvement_for_occupation",
    "generate_application_email_for_occupation",
    "compare_cv_with_jd",
    "generate_cv_improvement_for_jd",
    "generate_application_email_for_jd",
    "register_user",
    "login_user",
    "save_cv_for_user",
    "get_cv_info_for_user",
    "analyze_cv_for_saved_user",
    "compare_saved_cv_with_jd",
    "InvalidCredentialsError",
    "NoSavedCVError",
]
