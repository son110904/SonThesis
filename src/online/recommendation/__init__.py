"""src.online.recommendation – Sinh khuyến nghị AI và client LLM dùng chung."""

from src.online.recommendation.llm_client import LLMClient, get_llm_client
from src.online.recommendation.recommender import generate_recommendation

__all__ = ["LLMClient", "get_llm_client", "generate_recommendation"]
