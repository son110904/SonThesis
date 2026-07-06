"""
semantic_skill_match.py – So khớp kỹ năng theo NGỮ NGHĨA (Lỗ hổng 5).

Vấn đề của exact-string match (weighted_matcher / skill_gap bản cũ):
    Chỉ chuẩn hóa lowercase + strip rồi so khớp tuyệt đối, nên:
        "Học máy"     ≠ "Machine Learning"   (cùng nghĩa, khác ngôn ngữ)
        "Python developer" ≠ "Python"         (cùng lõi, khác cụm)
        "lập trình web"    ≠ "lập trình"
    → bỏ sót nhiều khớp đúng, kéo weighted_skill_score xuống thấp giả tạo.

Giải pháp ở đây: dùng CHÍNH embedding model đã fine-tune để đo cosine similarity
giữa từng skill của nghề và từng skill ứng viên. Một skill nghề coi là "matched"
nếu có ít nhất một skill ứng viên:
    - trùng tuyệt đối (sau canonicalize) → sim = 1.0, hoặc
    - cosine similarity ≥ SKILL_MATCH_THRESHOLD.

Kết quả (SkillMatchResult) được DÙNG CHUNG cho cả Bước 8 (weighted score) và
Bước 10 (skill gap) để khỏi nhúng embedding hai lần.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np

from src.config import SKILL_MATCH_MODE, SKILL_MATCH_THRESHOLD
from src.offline.skill_normalize import canonicalize_skill

logger = logging.getLogger(__name__)


@dataclass
class SkillMatchResult:
    """
    Kết quả so khớp skill nghề ↔ skill ứng viên.

    Attributes:
        matched:   Dict[skill_nghề → skill_ứng_viên khớp] (skill nghề đã match).
        unmatched: List skill nghề KHÔNG match (ứng viên thiếu).
        sims:      Dict[skill_nghề → cosine sim cao nhất] (để giải thích/ngưỡng).
        mode_used: "semantic" hoặc "exact" (mode thực tế đã chạy, sau fallback).
    """

    matched: dict[str, str] = field(default_factory=dict)
    unmatched: list[str] = field(default_factory=list)
    sims: dict[str, float] = field(default_factory=dict)
    mode_used: str = "exact"


def _normalize(skill: str) -> str:
    return canonicalize_skill(skill).strip().lower()


@lru_cache(maxsize=1)
def _get_model():
    """
    Lấy model dùng CHUNG với candidate_embedder (cùng 1 instance đã prewarm) thay vì
    load thêm bản thứ 2 → tiết kiệm ~6s và một bản sao RAM. None nếu không load được.
    """
    try:
        from src.online.embedding_step5 import get_shared_model

        model = get_shared_model(use_finetuned=True)
        logger.info("semantic_skill_match: dùng chung model đã nạp.")
        return model
    except Exception as e:  # noqa: BLE001
        logger.error(f"semantic_skill_match: không load được model ({e}) → fallback exact.")
        return None


def _build_exact_match_result(
    occupation_skills: list[str],
    candidate_skills: list[str],
) -> SkillMatchResult:
    """Tạo kết quả khớp chính xác sau khi chuẩn hóa tên skill."""
    candidate_lookup = {_normalize(s): s for s in candidate_skills}
    res = SkillMatchResult(mode_used="exact")

    for occupation_skill in occupation_skills:
        canonical_key = _normalize(occupation_skill)
        if canonical_key in candidate_lookup:
            res.matched[occupation_skill] = candidate_lookup[canonical_key]
            res.sims[occupation_skill] = 1.0
        else:
            res.unmatched.append(occupation_skill)
            res.sims[occupation_skill] = 0.0

    return res


def _pick_best_candidate_match(
    occupation_skill: str,
    candidate_skills: list[str],
    candidate_lookup: dict[str, str],
    similarity_row: np.ndarray,
    threshold: float,
) -> tuple[str | None, float]:
    """Chọn candidate phù hợp nhất bằng hai tầng: exact trước, semantic sau."""
    canonical_key = _normalize(occupation_skill)
    if canonical_key in candidate_lookup:
        return candidate_lookup[canonical_key], 1.0

    if similarity_row.size == 0:
        return None, 0.0

    best_index = int(np.argmax(similarity_row))
    best_similarity = float(similarity_row[best_index])
    if best_similarity >= threshold:
        return candidate_skills[best_index], best_similarity
    return None, best_similarity


def _semantic_match(
    occupation_skills: list[str],
    candidate_skills: list[str],
    threshold: float,
    model,
) -> SkillMatchResult:
    """Dùng embedding để so khớp skill nghề ↔ ứng viên khi exact match không đủ."""
    occupation_canon = [canonicalize_skill(s) for s in occupation_skills]
    candidate_canon = [canonicalize_skill(s) for s in candidate_skills]

    try:
        occupation_embeddings = model.encode(
            occupation_canon,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        candidate_embeddings = model.encode(
            candidate_canon,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"semantic_skill_match: encode lỗi ({e}) → fallback exact.")
        return _build_exact_match_result(occupation_skills, candidate_skills)

    similarity_matrix = occupation_embeddings @ candidate_embeddings.T
    candidate_lookup = {_normalize(s): s for s in candidate_skills}

    res = SkillMatchResult(mode_used="semantic")
    for index, occupation_skill in enumerate(occupation_skills):
        matched_skill, similarity = _pick_best_candidate_match(
            occupation_skill=occupation_skill,
            candidate_skills=candidate_skills,
            candidate_lookup=candidate_lookup,
            similarity_row=similarity_matrix[index],
            threshold=threshold,
        )
        res.sims[occupation_skill] = round(similarity, 4)
        if matched_skill is not None:
            res.matched[occupation_skill] = matched_skill
        else:
            res.unmatched.append(occupation_skill)

    return res


def match_skills(
    candidate_skills: list[str],
    occupation_skills: list[str],
    mode: str = SKILL_MATCH_MODE,
    threshold: float = SKILL_MATCH_THRESHOLD,
    model=None,
) -> SkillMatchResult:
    """
    So khớp danh sách skill nghề với skill ứng viên.

    Luồng dễ hiểu:
    1. Thử khớp chính xác trước (đã chuẩn hóa tên).
    2. Nếu bật semantic và chưa khớp được, dùng embedding để đo mức độ tương tự.
    3. Nếu model không sẵn, tự fallback về exact match.
    """
    if not occupation_skills:
        return SkillMatchResult(mode_used=mode)

    if mode != "semantic":
        return _build_exact_match_result(occupation_skills, candidate_skills)

    if not candidate_skills:
        res = _build_exact_match_result(occupation_skills, candidate_skills)
        res.mode_used = "semantic"
        return res

    if model is None:
        model = _get_model()
    if model is None:
        return _build_exact_match_result(occupation_skills, candidate_skills)

    return _semantic_match(
        occupation_skills=occupation_skills,
        candidate_skills=candidate_skills,
        threshold=threshold,
        model=model,
    )
