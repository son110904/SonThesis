"""
candidate_embedder.py – Sinh candidate_embedding từ Candidate Profile.

Bước 5 của Online Pipeline.

Dùng LẠI embedder.load_model() của offline để chắc chắn ứng viên và occupation
được embed bằng CÙNG một model (cùng không gian vector → cosine có nghĩa).
Nếu fine-tuned model hỏng (NaN), load_model tự fallback sang pretrained — và vì
occupation embeddings cũng sinh bằng load_model, hai bên vẫn nhất quán.

Trước khi embed, text được clean bằng _clean_text() để loại bỏ:
    - Dãy emoji/symbol noise từ PDF extraction (VD: "♔ ♔ ๋İ ๋Ï")
    - Khoảng trắng thừa
Giữ nguyên: chữ Latin/VI/EN, số, dấu câu, ký hiệu có nghĩa (CI/CD, Node.js).
"""

from __future__ import annotations

import logging
import re
import threading
import unicodedata

import numpy as np

from src.models import CandidateProfile
from src.offline.embedding_step7.embedder import load_model

logger = logging.getLogger(__name__)

_MAX_SKILLS = 30
_MAX_EXP = 5
_MAX_PROJ = 5


def _is_latin_viet_char(ch: str) -> bool:
    """True nếu ký tự là chữ Latin/Vietnamese có nghĩa (giữ lại)."""
    cp = ord(ch)
    # Latin cơ bản: A-Z a-z
    if 65 <= cp <= 122 and cp not in range(91, 97):  # A-Z, a-z (không qua khoảng [\]^_`)
        return True
    # Latin Extended-A/B (tiếng Việt có dấu: ă, â, đ, ê, ô, ơ, ư)
    if 192 <= cp <= 383:  # Latin Extended-A + Latin Extended-B
        return True
    # Vietnamese special letters: đ (U+0111), Đ (U+0110)
    if cp in (0x0110, 0x0111):
        return True
    return False


def _is_noise_char(ch: str) -> bool:
    """True nếu ký tự KHÔNG mang ngữ nghĩa (emoji, symbol, mark, control, non-Latin letters)."""
    if ch.isdigit() or ch.isspace():
        return False
    if ch in (",", ".", ":", ";", "-", "/", "(", ")", "@", "+", "=", "#", "$", "%", "&", "'", '"'):
        return False
    if _is_latin_viet_char(ch):
        return False
    cat = unicodedata.category(ch)
    # Lo=Other letter (CJK, Hangul, etc.), So=Symbol, Sc=Currency,
    # Sk=Modifier, Sm=Math, Co=Private, Cs=Surrogate, Me/Mn=Mark
    return cat in ("Lo", "So", "Sc", "Sk", "Sm", "Co", "Cs", "Me", "Mn")


def _clean_text(text: str) -> str:
    """
    Loại bỏ dãy ký tự noise (emoji/symbol) khỏi text trước khi embed.

    Giữ: chữ (Latin, tiếng Việt có dấu), số, dấu câu có nghĩa.
    Loại: emoji, symbol, decorative noise (VD: "♔ ♔ ๋İ ๋Ï" từ PDF extraction).
    """
    result: list[str] = []
    noise_run = 0

    for ch in text:
        if _is_noise_char(ch):
            noise_run += 1
        else:
            if noise_run >= 3:
                result.append(" ")
            result.append(ch)
            noise_run = 0

    if noise_run >= 3 and result and result[-1] != " ":
        result.append(" ")

    cleaned = "".join(result)
    return re.sub(r"\s{2,}", " ", cleaned).strip()


# Model dùng chung toàn ứng dụng (load 1 lần). Lock để an toàn khi vừa prewarm ở
# luồng nền vừa có request phân tích → chỉ load đúng 1 lần, không nạp đôi.
_shared_model = None
_model_lock = threading.Lock()


def get_shared_model(use_finetuned: bool = True):
    """Lấy SentenceTransformer dùng chung (load 1 lần, lazy, thread-safe)."""
    global _shared_model
    if _shared_model is not None:
        return _shared_model
    with _model_lock:
        if _shared_model is None:  # double-checked locking
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
        skills_text = _clean_text(", ".join(skills))
        parts.append(f"Skills: {skills_text}.")
        parts.append(f"Key competencies: {skills_text}.")

    if profile.experience:
        exp = _clean_text(" ".join(e.strip().rstrip(".") + "." for e in profile.experience[:_MAX_EXP]))
        parts.append(f"Experience: {exp}")

    if profile.projects:
        proj = _clean_text(" ".join(p.strip().rstrip(".") + "." for p in profile.projects[:_MAX_PROJ]))
        parts.append(f"Projects: {proj}")

    # Fallback: nếu profile rỗng (vd thiếu LLM + ít skill) thì dùng raw_text
    if not parts and profile.raw_text:
        return _clean_text(profile.raw_text[:2000])

    return _clean_text(" ".join(parts))


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
