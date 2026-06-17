"""
analysis_service.py – Điều phối toàn bộ Online Pipeline (Bước 2 → 11).

Luồng:
    raw_text         (Bước 2)  text_extractor
    candidate skills (Bước 3)  candidate_skill_extractor
    candidate profile(Bước 4)  profile_builder (regex + LLM)
    candidate_emb    (Bước 5)  candidate_embedder
    occupation prof  (Bước 6)  occupation_loader
    semantic score   (Bước 7)  semantic_matcher
    weighted score   (Bước 8)  weighted_matcher
    final score      (Bước 9)  score_calculator
    skill gap        (Bước 10) skill_gap_analyzer
    recommendation   (Bước 11) recommender
    → lưu lịch sử (SQLite)
"""

from __future__ import annotations

import logging
from typing import Optional

from src.models import AnalysisResult
from src.online.extraction import extract_text_from_bytes
from src.online.candidate_profile import build_candidate_profile
from src.online.embedding import embed_candidate
from src.online.semantic_matching import compute_semantic_score
from src.online.weighted_matching import compute_weighted_skill_score
from src.online.scoring import compute_final_score
from src.online.skill_gap import analyze_skill_gap
from src.online.recommendation import generate_recommendation
from src.online.services.occupation_loader import get_occupation

logger = logging.getLogger(__name__)


class EmptyCVError(ValueError):
    """Raise khi CV trích ra rỗng (vd PDF scan ảnh)."""


def analyze_cv(
    file_bytes: bytes,
    filename: str,
    occupation_key: str,
    include_recommendation: bool = True,
    persist: bool = True,
) -> AnalysisResult:
    """
    Chạy toàn bộ pipeline phân tích CV với 1 nghề mục tiêu.

    Args:
        file_bytes:             Nội dung file CV (PDF/DOCX).
        filename:               Tên file (xác định loại).
        occupation_key:         Key nghề (từ list_occupations).
        include_recommendation: Có gọi LLM sinh khuyến nghị không.
        persist:                Có lưu lịch sử vào SQLite không.

    Returns:
        AnalysisResult đầy đủ.

    Raises:
        UnsupportedFileType: File không phải PDF/DOCX.
        OccupationNotFound:  occupation_key không hợp lệ.
        EmptyCVError:        CV trích ra rỗng.
    """
    logger.info(f"=== Analyze CV '{filename}' cho nghề '{occupation_key}' ===")

    # Bước 6: occupation (validate sớm trước khi tốn công xử lý CV)
    occupation = get_occupation(occupation_key)
    occ_display = occupation["_display"]
    occ_embedding = occupation.get("embedding", [])

    # Bước 2: text extraction
    raw_text = extract_text_from_bytes(file_bytes, filename)
    if not raw_text.strip():
        raise EmptyCVError(
            "Không trích được văn bản từ CV (có thể là PDF scan ảnh). "
            "Hãy thử file PDF có text hoặc DOCX."
        )

    # Bước 3-4: candidate profile (regex skills + LLM sections)
    profile = build_candidate_profile(raw_text)

    # Bước 5: candidate embedding
    candidate_embedding = embed_candidate(profile)

    # Bước 7: semantic matching
    semantic_score = compute_semantic_score(candidate_embedding, occ_embedding)

    # Bước 8: weighted skill matching
    weighted_score = compute_weighted_skill_score(profile.skills, occupation)

    # Bước 9: final score
    scores = compute_final_score(semantic_score, weighted_score)

    # Bước 10: skill gap
    skill_gap = analyze_skill_gap(profile.skills, occupation)

    # Bước 11: AI recommendation (graceful nếu thiếu key)
    recommendation: Optional[str] = None
    if include_recommendation:
        recommendation = generate_recommendation(
            occupation_display=occ_display,
            scores=scores,
            candidate_profile=profile,
            skill_gap=skill_gap,
        )

    result = AnalysisResult(
        occupation_key=occupation_key,
        occupation_display=occ_display,
        scores=scores,
        skill_gap=skill_gap,
        candidate_profile=profile,
        ai_recommendation=recommendation,
    )

    if persist:
        _save_history(filename, result)

    logger.info(
        f"=== Hoàn tất: match_score={scores.match_score:.2%} "
        f"(semantic={semantic_score:.2%}, weighted={weighted_score:.2%}) ==="
    )
    return result


def _save_history(filename: str, result: AnalysisResult) -> None:
    """Lưu kết quả vào lịch sử. Lỗi DB không làm hỏng phân tích."""
    try:
        from src.database import save_evaluation

        save_evaluation(cv_filename=filename, result=result)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Không lưu được lịch sử đánh giá: {e}")
