"""src.online.validation – Kiểm tra đầu vào: định dạng, có phải CV, đủ nội dung."""

from src.online.validation.cv_detector import NotACVError, is_cv
from src.online.validation.profile_completeness import (
    assess_profile_completeness,
    build_sparse_review,
)

__all__ = ["NotACVError", "is_cv", "assess_profile_completeness", "build_sparse_review"]
