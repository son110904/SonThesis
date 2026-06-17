"""src.frontend.components – Thành phần UI tái dùng."""

from src.frontend.components.score_gauge import render_match_gauge
from src.frontend.components.badges import render_skill_badges
from src.frontend.components.cards import (
    render_metric_card,
    render_recommendation_card,
)

__all__ = [
    "render_match_gauge",
    "render_skill_badges",
    "render_metric_card",
    "render_recommendation_card",
]
