"""
candidate_embedder.py – Sinh candidate_embedding từ Candidate Profile.

Bước 5 của Online Pipeline.

Dùng LẠI embedder.load_model() của offline để chắc chắn ứng viên và occupation
được embed bằng CÙNG một model (cùng không gian vector → cosine có nghĩa).
Nếu fine-tuned model hỏng (NaN), load_model tự fallback sang pretrained — và vì
occupation embeddings cũng sinh bằng load_model, hai bên vẫn nhất quán.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from src.models import CandidateProfile
from src.offline.embedding.embedder import load_model

logger = logging.getLogger(__name__)

# Số mục tối đa đưa vào text để embed (tránh quá dài)
_MAX_SKILLS = 30
_MAX_EXP = 5
_MAX_PROJ = 5

# Model dùng chung toàn ứng dụng (load 1 lần)
_shared_model = None


def get_shared_model(use_finetuned: bool = True):
    """Lấy SentenceTransformer dùng chung (load 1 lần, lazy)."""
    global _shared_model
    if _shared_model is None:
        logger.info("Đang load embedding model (lần đầu)...")
        _shared_model = load_model(use_finetuned=use_finetuned)
    return _shared_model


def build_candidate_text(profile: CandidateProfile) -> str:
    """
    Dựng văn bản đại diện cho ứng viên để embed.

    Cấu trúc song song với build_occupation_text của offline (Skills ưu tiên).
    """
    parts: list[str] = []

    if profile.skills:
        skills = profile.skills[:_MAX_SKILLS]
        parts.append(f"Skills: {', '.join(skills)}.")
        parts.append(f"Key competencies: {', '.join(skills[:10])}.")

    if profile.experience:
        exp = " ".join(e.strip().rstrip(".") + "." for e in profile.experience[:_MAX_EXP])
        parts.append(f"Experience: {exp}")

    if profile.projects:
        proj = " ".join(p.strip().rstrip(".") + "." for p in profile.projects[:_MAX_PROJ])
        parts.append(f"Projects: {proj}")

    # Fallback: nếu profile rỗng (vd thiếu LLM + ít skill) thì dùng raw_text
    if not parts and profile.raw_text:
        return profile.raw_text[:2000]

    return " ".join(parts)


def embed_candidate(
    profile: CandidateProfile,
    model=None,
    normalize: bool = True,
) -> list[float]:
    """
    Sinh candidate_embedding.

    Args:
        profile:   CandidateProfile.
        model:     SentenceTransformer (None → dùng shared model).
        normalize: L2-normalize (tốt cho cosine).

    Returns:
        Embedding vector (list[float], dim=768).
    """
    if model is None:
        model = get_shared_model()

    text = build_candidate_text(profile)

    # Truncate qua tokenizer trước khi encode (tránh position_ids overflow)
    tokens = model.tokenizer(text, max_length=512, truncation=True, return_tensors=None)
    text = model.tokenizer.decode(tokens["input_ids"], skip_special_tokens=True)

    vec = model.encode(
        [text],
        normalize_embeddings=normalize,
        convert_to_numpy=True,
        show_progress_bar=False,
    )[0]

    if np.isnan(vec).any():
        raise RuntimeError("candidate_embedding chứa NaN — model có thể bị hỏng.")

    return vec.astype(float).tolist()
