"""src.online.embedding – Sinh embedding cho ứng viên."""

from src.online.embedding.candidate_embedder import (
    build_candidate_text,
    embed_candidate,
    get_shared_model,
)

__all__ = ["build_candidate_text", "embed_candidate", "get_shared_model"]
