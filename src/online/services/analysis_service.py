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

from src.models import AnalysisResult, CandidateProfile
from src.online.extraction_step2 import extract_text_from_bytes
from src.online.candidate_profile_step4 import build_candidate_profile
from src.online.embedding_step5 import embed_candidate
from src.online.semantic_matching_step7 import compute_semantic_score
from src.online.semantic_skill_match import match_skills
from src.online.weighted_matching_step8 import compute_weighted_skill_score
from src.online.scoring_step9 import compute_final_score
from src.online.skill_gap_step10 import analyze_skill_gap
from src.online.recommendation_step11 import generate_cv_review, cv_review_to_markdown
from src.online.services.occupation_loader import get_occupation
from src.online.validation import NotACVError, is_cv

logger = logging.getLogger(__name__)


class EmptyCVError(ValueError):
    """Raise khi CV trích ra rỗng (vd PDF scan ảnh)."""


def analyze_cv(
    file_bytes: bytes,
    filename: str,
    occupation_key: str,
    include_recommendation: bool = True,
) -> AnalysisResult:
    """
    Chạy toàn bộ pipeline phân tích CV với 1 nghề mục tiêu.

    Args:
        file_bytes:             Nội dung file CV (PDF/DOCX).
        filename:               Tên file (xác định loại).
        occupation_key:         Key nghề (từ list_occupations).
        include_recommendation: Có gọi LLM sinh khuyến nghị không.

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

    # Bước 2: text extraction
    raw_text = extract_text_from_bytes(file_bytes, filename)
    if not raw_text.strip():
        raise EmptyCVError(
            "Không trích được văn bản từ CV (có thể là PDF scan ảnh). "
            "Hãy thử file PDF có text hoặc DOCX."
        )

    # Kiểm tra: tài liệu có phải CV không. Không phải → dừng, KHÔNG chạy tiếp.
    ok, reason = is_cv(raw_text)
    if not ok:
        raise NotACVError(
            "Tài liệu được tải lên không phải là CV hoặc Resume. "
            "Vui lòng tải lên CV hợp lệ."
        )

    # Bước 3-4: candidate profile (regex skills + LLM sections)
    profile = build_candidate_profile(raw_text)

    # Bước 5: candidate embedding
    candidate_embedding = embed_candidate(profile)

    # Bước 6-11: chấm điểm + AI review cho nghề này
    return _analyze_one(profile, candidate_embedding, occupation, include_recommendation)


def _analyze_one(
    profile: CandidateProfile,
    candidate_embedding: list[float],
    occupation: dict,
    include_recommendation: bool = True,
) -> AnalysisResult:
    """
    Chấm điểm 1 nghề (Bước 6-11) từ candidate profile + embedding ĐÃ tính sẵn.

    Tách riêng để dùng lại: (1) analyze_cv chấm 1 nghề, (2) review_occupation chấm
    nghề người dùng chọn từ Top 3, (3) recommend_occupations gọi phần 6-10 (bỏ 11).
    """
    occ_display = occupation["_display"]
    occ_embedding = occupation.get("embedding", [])

    # Bước 7: semantic matching
    semantic_score = compute_semantic_score(candidate_embedding, occ_embedding)

    # Skill matching dùng chung cho Bước 8 & 10 (theo config mode).
    occ_skills = list({**occupation.get("optional_skills", {}),
                       **occupation.get("core_skills", {})}.keys())
    skill_match = match_skills(profile.skills, occ_skills)

    # Bước 8: weighted skill matching
    weighted_score = compute_weighted_skill_score(profile.skills, occupation, skill_match)

    # Bước 9: final score
    scores = compute_final_score(semantic_score, weighted_score)

    # Bước 10: skill gap
    skill_gap = analyze_skill_gap(profile.skills, occupation, skill_match)

    # Bước 11: AI CV Review — đầu ra TRUNG TÂM (graceful nếu thiếu key)
    cv_review: Optional[dict] = None
    recommendation: Optional[str] = None
    if include_recommendation:
        cv_review = generate_cv_review(
            occupation_display=occ_display,
            occupation_profile=occupation,
            scores=scores,
            candidate_profile=profile,
            skill_gap=skill_gap,
        )
        recommendation = cv_review_to_markdown(cv_review)

    logger.info(
        f"=== Hoàn tất '{occupation['_key']}': match_score={scores.match_score:.2%} "
        f"(semantic={semantic_score:.2%}, weighted={weighted_score:.2%}) ==="
    )
    return AnalysisResult(
        occupation_key=occupation["_key"],
        occupation_display=occ_display,
        scores=scores,
        skill_gap=skill_gap,
        candidate_profile=profile,
        ai_recommendation=recommendation,
        cv_review=cv_review,
    )


def review_occupation(
    candidate_profile: dict,
    candidate_embedding: list[float],
    occupation_key: str,
    include_recommendation: bool = True,
) -> AnalysisResult:
    """
    Sinh AI CV Review cho 1 nghề người dùng chọn, TÁI DÙNG candidate profile +
    embedding đã tính ở bước recommend → KHÔNG re-extract / re-embed / gọi lại LLM
    trích profile. Chỉ tốn 1 lần LLM cho AI Review.

    Args:
        candidate_profile:   dict (từ recommend_occupations → profile.to_dict() + raw_text).
        candidate_embedding: vector 768 chiều đã tính.
        occupation_key:      nghề người dùng chọn.
    """
    occupation = get_occupation(occupation_key)
    profile = CandidateProfile(
        skills=candidate_profile.get("skills", []),
        experience=candidate_profile.get("experience", []),
        projects=candidate_profile.get("projects", []),
        education=candidate_profile.get("education", []),
        raw_text=candidate_profile.get("raw_text", ""),
    )
    return _analyze_one(profile, candidate_embedding, occupation, include_recommendation)
