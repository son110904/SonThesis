"""
semantic_skill_match.py – So khớp kỹ năng theo NGỮ NGHĨA (Lỗ hổng 5).

Ba tầng so khớp, áp dụng theo thứ tự ưu tiên:

  1. Exact match (canonicalize)      → sim = 1.0
  2. Parent-skill match (PARENT_SKILL_MAP) → sim = 0.95
     VD: nghề yêu cầu "Lập trình", candidate có Python/Java/C++
  3. Semantic match (gte embedding)  → sim = cosine

Vấn đề cũ của exact-string match:
    "Học máy"     ≠ "Machine Learning"   (cùng nghĩa, khác ngôn ngữ)
    "Python developer" ≠ "Python"         (cùng lõi, khác cụm)
    "Lập trình"   ≠ "Python"            (nhóm cha ≠ ngôn ngữ cụ thể)

Kết quả (SkillMatchResult) được DÙNG CHUNG cho cả Bước 8 (weighted score) và
Bước 10 (skill gap) để khỏi nhúng embedding hai lần.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np

from src.config import SKILL_MATCH_MODE, SKILL_MATCH_THRESHOLD
from src.offline.skill_normalize import PARENT_SKILL_MAP, canonicalize_skill

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

    # Xây reverse map: parent → set(children) để match "nhóm cha"
    parent_to_children: dict[str, set[str]] = {}
    for child, parent in PARENT_SKILL_MAP.items():
        parent_to_children.setdefault(parent.lower(), set()).add(child)

    # Với mỗi skill ứng viên, ghi nhận các parent mà nó thuộc về
    candidate_parents: dict[str, set[str]] = {}  # parent → set(children ứng viên)
    for skill in candidate_skills:
        canon = _normalize(skill)
        for child, parent in PARENT_SKILL_MAP.items():
            if _normalize(child) == canon:
                p = parent.lower()
                candidate_parents.setdefault(p, set()).add(canon)

    res = SkillMatchResult(mode_used="exact")

    for occupation_skill in occupation_skills:
        canonical_key = _normalize(occupation_skill)

        # ① Exact match
        if canonical_key in candidate_lookup:
            res.matched[occupation_skill] = candidate_lookup[canonical_key]
            res.sims[occupation_skill] = 1.0
            continue

        # ② Parent skill match: nghề yêu cầu "Lập trình", candidate có Python/Java/C…
        occ_lower = canonical_key.lower()
        if occ_lower in parent_to_children and occ_lower in candidate_parents:
            # Trả về skill con đầu tiên của candidate làm bằng chứng
            matched_child = next(iter(candidate_parents[occ_lower]))
            # Tìm display name gốc của child đó
            matched_display = next(
                (s for s in candidate_skills if _normalize(s) == matched_child), matched_child
            )
            res.matched[occupation_skill] = matched_display
            res.sims[occupation_skill] = 0.95
            continue

        res.unmatched.append(occupation_skill)
        res.sims[occupation_skill] = 0.0

    return res


def _pick_best_candidate_match(
    occupation_skill: str,
    candidate_skills: list[str],
    candidate_lookup: dict[str, str],
    similarity_row: np.ndarray,
    threshold: float,
    parent_to_children: dict[str, set[str]] | None = None,
    candidate_parents: dict[str, set[str]] | None = None,
) -> tuple[str | None, float]:
    """Chọn candidate phù hợp nhất: exact → semantic → parent-skill fallback."""
    canonical_key = _normalize(occupation_skill)
    if canonical_key in candidate_lookup:
        return candidate_lookup[canonical_key], 1.0

    if similarity_row.size == 0:
        # Fallback parent match
        if parent_to_children and candidate_parents:
            occ_lower = canonical_key.lower()
            if occ_lower in parent_to_children and occ_lower in candidate_parents:
                matched_child = next(iter(candidate_parents[occ_lower]))
                matched_display = next(
                    (s for s in candidate_skills if _normalize(s) == matched_child), matched_child
                )
                return matched_display, 0.95
        return None, 0.0

    best_index = int(np.argmax(similarity_row))
    best_similarity = float(similarity_row[best_index])

    if best_similarity >= threshold:
        return candidate_skills[best_index], best_similarity

    # Semantic thấp hơn ngưỡng → thử parent skill match
    if parent_to_children and candidate_parents:
        occ_lower = canonical_key.lower()
        if occ_lower in parent_to_children and occ_lower in candidate_parents:
            matched_child = next(iter(candidate_parents[occ_lower]))
            matched_display = next(
                (s for s in candidate_skills if _normalize(s) == matched_child), matched_child
            )
            return matched_display, 0.95

    return candidate_skills[best_index], best_similarity


def _semantic_match(
    occupation_skills: list[str],
    candidate_skills: list[str],
    threshold: float,
    model,
) -> SkillMatchResult:
    """Dùng embedding để so khớp skill nghề ↔ ứng viên khi exact match không đủ."""
    occupation_canon = [canonicalize_skill(s) for s in occupation_skills]
    candidate_canon = [canonicalize_skill(s) for s in candidate_skills]

    # Xây parent maps một lần (giống _build_exact_match_result)
    parent_to_children: dict[str, set[str]] = {}
    for child, parent in PARENT_SKILL_MAP.items():
        parent_to_children.setdefault(parent.lower(), set()).add(child.lower())

    candidate_parents: dict[str, set[str]] = {}
    for skill in candidate_skills:
        canon = _normalize(skill)
        for child, parent in PARENT_SKILL_MAP.items():
            if _normalize(child) == canon:
                p = parent.lower()
                candidate_parents.setdefault(p, set()).add(canon)

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
            parent_to_children=parent_to_children,
            candidate_parents=candidate_parents,
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

    Ba tầng ưu tiên:
    1. Exact match (canonicalize) → sim=1.0
    2. Parent-skill match → sim=0.95
    3. Semantic (gte embedding) → sim=cosine ≥ threshold

    mode="exact" (mặc định): chạy 1+2, bỏ qua 3.
    mode="semantic": chạy cả 3 theo thứ tự.
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
