"""
recommendation_service.py – Career Recommendation: gợi ý Top-K nghề phù hợp nhất.

Sau khi upload CV: trích text → kiểm tra có phải CV → dựng candidate profile +
embedding (1 LẦN) → chấm Match Score với TẤT CẢ occupation profiles → xếp hạng →
Top-K. AI CV Review chỉ sinh khi người dùng chọn 1 nghề (xem review_occupation).

Tái dùng toàn bộ logic chấm điểm bước 7-9 (không gọi LLM ở đây).
"""

from __future__ import annotations

import logging

from src.online.extraction_step2 import extract_text_from_bytes
from src.online.candidate_profile_step4 import build_candidate_profile
from src.online.embedding_step5 import embed_candidate
from src.online.semantic_matching_step7 import compute_semantic_score
from src.online.semantic_skill_match import match_skills
from src.online.weighted_matching_step8 import compute_weighted_skill_score
from src.online.scoring_step9 import compute_final_score
from src.online.services.occupation_loader import list_occupations, get_occupation
from src.online.services.analysis_service import EmptyCVError
from src.online.validation import NotACVError, is_cv

logger = logging.getLogger(__name__)


def recommend_occupations(
    file_bytes: bytes,
    filename: str,
    top_k: int = 3,
) -> dict:
    """
    Gợi ý Top-K nghề phù hợp nhất với CV.

    Returns:
        {
          "recommendations": [
            {occupation_key, occupation_display, match_score,
             semantic_similarity_score, weighted_skill_score}, ...  (top_k)
          ],
          "candidate_profile": {skills, experience, projects, education, raw_text, filename},
          "candidate_embedding": [float, ...]   # để tái dùng khi review nghề đã chọn
        }

    Raises:
        UnsupportedFileType, EmptyCVError, NotACVError.
    """
    logger.info(f"=== Recommend occupations cho CV '{filename}' (top_k={top_k}) ===")

    # Bước 2: text extraction
    raw_text = extract_text_from_bytes(file_bytes, filename)
    if not raw_text.strip():
        raise EmptyCVError(
            "Không trích được văn bản từ CV (có thể là PDF scan ảnh). "
            "Hãy thử file PDF có text hoặc DOCX."
        )

    # Kiểm tra có phải CV không
    ok, _reason = is_cv(raw_text)
    if not ok:
        raise NotACVError(
            "Tài liệu được tải lên không phải là CV hoặc Resume. "
            "Vui lòng tải lên CV hợp lệ."
        )

    # Bước 3-5: candidate profile + embedding (1 LẦN, dùng cho mọi nghề)
    profile = build_candidate_profile(raw_text)
    candidate_embedding = embed_candidate(profile)

    # Chấm điểm với TẤT CẢ occupation profiles
    scored: list[dict] = []
    for item in list_occupations():
        occ_key = item["key"]
        occupation = get_occupation(occ_key)

        semantic_score = compute_semantic_score(
            candidate_embedding, occupation.get("embedding", [])
        )
        occ_skills = list({**occupation.get("optional_skills", {}),
                           **occupation.get("core_skills", {})}.keys())
        skill_match = match_skills(profile.skills, occ_skills)
        weighted_score = compute_weighted_skill_score(profile.skills, occupation, skill_match)
        scores = compute_final_score(semantic_score, weighted_score)

        scored.append({
            "occupation_key": occ_key,
            "occupation_display": occupation["_display"],
            "match_score": scores.match_score,
            "semantic_similarity_score": scores.semantic_similarity_score,
            "weighted_skill_score": scores.weighted_skill_score,
        })

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    top = scored[:top_k]
    logger.info(
        "Top nghề: " + ", ".join(f"{r['occupation_display']}={r['match_score']:.2%}" for r in top)
    )

    candidate_dict = profile.to_dict()
    candidate_dict["raw_text"] = profile.raw_text
    candidate_dict["filename"] = filename

    return {
        "recommendations": top,
        "candidate_profile": candidate_dict,
        "candidate_embedding": candidate_embedding,
    }
