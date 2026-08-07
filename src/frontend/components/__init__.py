"""src.frontend.components – Thành phần UI tái dùng."""

from src.frontend.components.badges import render_skill_badges
from src.frontend.components.cards import (
    render_metric_card,
    render_recommendation_card,
    render_cv_review,
    render_cv_improvement,
    render_application_email,
)

__all__ = [
    "render_skill_badges",
    "render_metric_card",
    "render_recommendation_card",
    "render_cv_review",
    "render_cv_improvement",
    "render_application_email",
]
