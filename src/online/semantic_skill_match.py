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

Thiết kế "degrade graceful": nếu mode="exact" hoặc không load được model →
tự rơi về exact-match (đúng hành vi cũ, không vỡ pipeline).
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
    """Lazy-load + cache fine-tuned model. None nếu không load được."""
    try:
        from src.offline.embedding_step7.embedder import load_model

        model = load_model(use_finetuned=True)
        logger.info("semantic_skill_match: model đã sẵn sàng.")
        return model
    except Exception as e:  # noqa: BLE001
        logger.error(f"semantic_skill_match: không load được model ({e}) → fallback exact.")
        return None


def _exact_match(
    occupation_skills: list[str],
    candidate_skills: list[str],
) -> SkillMatchResult:
    """Khớp tuyệt đối (sau canonicalize). Đúng hành vi cũ nhưng đã canonical hóa."""
    cand_norm = {_normalize(s): s for s in candidate_skills}
    res = SkillMatchResult(mode_used="exact")
    for occ in occupation_skills:
        key = _normalize(occ)
        if key in cand_norm:
            res.matched[occ] = cand_norm[key]
            res.sims[occ] = 1.0
        else:
            res.unmatched.append(occ)
            res.sims[occ] = 0.0
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

    Args:
        candidate_skills:  Skill của ứng viên.
        occupation_skills: Skill của nghề (core + optional).
        mode:              "semantic" hoặc "exact".
        threshold:         Ngưỡng cosine để coi là khớp (chỉ dùng khi semantic).
        model:             SentenceTransformer (nếu None & semantic → tự load cache).

    Returns:
        SkillMatchResult.
    """
    if not occupation_skills:
        return SkillMatchResult(mode_used=mode)

    if mode != "semantic":
        return _exact_match(occupation_skills, candidate_skills)

    if not candidate_skills:
        res = _exact_match(occupation_skills, candidate_skills)
        res.mode_used = "semantic"  # vẫn là semantic nhưng không có gì để khớp
        return res

    if model is None:
        model = _get_model()
    if model is None:  # load thất bại → fallback exact
        return _exact_match(occupation_skills, candidate_skills)

    # Canonical hóa hai phía trước khi embed (giữ alias/đồng nghĩa nhất quán).
    occ_canon = [canonicalize_skill(s) for s in occupation_skills]
    cand_canon = [canonicalize_skill(s) for s in candidate_skills]

    try:
        occ_emb = model.encode(occ_canon, normalize_embeddings=True,
                               convert_to_numpy=True, show_progress_bar=False)
        cand_emb = model.encode(cand_canon, normalize_embeddings=True,
                                convert_to_numpy=True, show_progress_bar=False)
    except Exception as e:  # noqa: BLE001
        logger.error(f"semantic_skill_match: encode lỗi ({e}) → fallback exact.")
        return _exact_match(occupation_skills, candidate_skills)

    # sim_matrix[i, j] = cosine(occ_i, cand_j) (đã L2-norm → dot).
    sim_matrix = occ_emb @ cand_emb.T
    cand_norm = {_normalize(s): s for s in candidate_skills}

    res = SkillMatchResult(mode_used="semantic")
    for i, occ in enumerate(occupation_skills):
        # Exact thắng tuyệt đối (sim = 1.0) — vừa nhanh vừa chắc.
        key = _normalize(occ)
        if key in cand_norm:
            res.matched[occ] = cand_norm[key]
            res.sims[occ] = 1.0
            continue
        j = int(np.argmax(sim_matrix[i]))
        best_sim = float(sim_matrix[i, j])
        res.sims[occ] = round(best_sim, 4)
        if best_sim >= threshold:
            res.matched[occ] = candidate_skills[j]
        else:
            res.unmatched.append(occ)
    return res
