"""src.online.recommendation_step11 – Sinh khuyến nghị AI và client LLM dùng chung."""

from src.online.recommendation_step11.llm_client import LLMClient, get_llm_client
from src.online.recommendation_step11.recommender import (
    generate_recommendation,
    generate_cv_review,
    cv_review_to_markdown,
)

__all__ = [
    "LLMClient",
    "get_llm_client",
    "generate_recommendation",
    "generate_cv_review",
    "cv_review_to_markdown",
]
