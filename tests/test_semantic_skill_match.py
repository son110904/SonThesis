import numpy as np

from src.online.semantic_skill_match import (
    _build_exact_match_result,
    _pick_best_candidate_match,
)


def test_build_exact_match_result_uses_canonicalized_names():
    result = _build_exact_match_result(
        occupation_skills=["Machine Learning", "Web Development"],
        candidate_skills=["machine learning", "python"],
    )

    assert result.mode_used == "exact"
    assert result.matched["Machine Learning"] == "machine learning"
    assert result.unmatched == ["Web Development"]
    assert result.sims["Machine Learning"] == 1.0
    assert result.sims["Web Development"] == 0.0


def test_pick_best_candidate_match_prefers_exact_match_before_similarity():
    candidate_lookup = {"python": "Python"}
    similarity_row = np.array([0.82])

    matched_skill, similarity = _pick_best_candidate_match(
        occupation_skill="Python",
        candidate_skills=["Java"],
        candidate_lookup=candidate_lookup,
        similarity_row=similarity_row,
        threshold=0.75,
    )

    assert matched_skill == "Python"
    assert similarity == 1.0
