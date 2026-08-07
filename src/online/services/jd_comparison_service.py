"""
jd_comparison_service.py – So sánh CV với Job Description trực tiếp.

Chế độ 2 (JD Comparison): không dùng Occupation Knowledge Base.
Pipeline:
  1. Extract CV text  (PDF/DOCX/MD)
  2. Extract JD text   (PDF/DOCX/MD)
  3. Build Candidate Profile (skills + experiences + projects + education)
  4. Extract skills từ JD (regex → canonicalize)
  5. Match skills (candidate vs JD) → matched / missing
  6. Semantic similarity (CV text vs JD text) – gte-multilingual-base
  7. Weighted Skill Score (heuristic weights, không có occupation profile)
  8. AI CV Review cho JD context (jd_recommender)

Module này còn điều phối 2 tính năng bổ trợ CHỈ dành cho chế độ 2 — AI CV
Improvement và Application Email — tái dùng candidate profile + scores + skill
gap ĐÃ TÍNH ở bước compare_cv_with_jd(), KHÔNG re-extract/re-embed.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from src.models import CandidateProfile, ScoreBreakdown, SkillGap

logger = logging.getLogger(__name__)

# ─── JD file → position hint extraction ───────────────────────────────────────

_POSITION_PATTERNS = [
    re.compile(r"(?im)^\s*(?:job\s*title|position|vị\s*trí|chức\s*danh|role)\s*[:\-]\s*(.+)", re.MULTILINE),
    re.compile(r"(?im)^\s*(?:senior|junior|lead|staff|principal)?\s*(?:backend|frontend|full[- ]?stack|"
               r"data\s*engineer|data\s*scientist|devops|cloud|ml\s*engineer|"
               r"software\s*engineer|software\s*developer|web\s*developer)\s*(?:engineer|developer)?", re.MULTILINE),
    re.compile(r"(?im)^\s*(?:hiring| tuyển| recruitment)\s*[:\-]?\s*(.+)", re.MULTILINE),
]


def _extract_position_hint(jd_text: str) -> str:
    """Trích job title / position từ JD text."""
    lines = jd_text.splitlines()
    # Ưu tiên 10 dòng đầu
    head = "\n".join(lines[:10])
    for pat in _POSITION_PATTERNS:
        m = pat.search(head)
        if m:
            result = m.group(1).strip()
            if len(result) >= 3:
                return result

    # Thử dòng đầu tiên non-empty có ≥3 từ
    for line in lines[:5]:
        line = line.strip()
        if len(line.split()) >= 2 and len(line) <= 80 and not any(
            line.lower().startswith(k) for k in ["job", "position", "title", "mô tả"]
        ):
            return line

    return ""


# ─── Heuristic skill weight cho JD (không có occupation profile) ──────────────

# Trọng số cốt lõi — framework/technology chính của role
_CORE_WEIGHT = 0.80
# Trọng số phụ — tool/platform/supporting library
_SUPPORT_WEIGHT = 0.50
# Trọng số soft skill / method
_SOFT_WEIGHT = 0.30
# Trọng số mặc định
_DEFAULT_WEIGHT = 0.60

# Patterns gì → weight bao nhiêu
_WEIGHT_SIGNALS: list[tuple[re.Pattern, float]] = [
    (re.compile(r"(?i)\b(react|vue|angular|svelte|next\.?js|nuxt\.?js)\b"), _CORE_WEIGHT),
    (re.compile(r"(?i)\b(flask|fastapi|django|express|node\.?js|nest\.?js)\b"), _CORE_WEIGHT),
    (re.compile(r"(?i)\b(postgres|mysql|mongodb|redis|elasticsearch|clickhouse|"
                r"sql\s*server|oracle)\b"), _CORE_WEIGHT),
    (re.compile(r"(?i)\b(pytorch|tensorflow|keras|scikit|sklearn|scipy|pandas|numpy)\b"), _CORE_WEIGHT),
    (re.compile(r"(?i)\b(grpc|graphql|websocket|rest\s*api|restful|api\s*design)\b"), _CORE_WEIGHT),
    (re.compile(r"(?i)\b(kubernetes|k8s|docker|terraform|ansible|helm)\b"), _CORE_WEIGHT),
    (re.compile(r"(?i)\b(aws|azure|gcp|google\s*cloud|cloud\s*(?:platform|aws?))\b"), _CORE_WEIGHT),
    (re.compile(r"(?i)\b(ci/?cd|jenkins|github\s*actions|gitlab\s*ci|bitbucket)\b"), _SUPPORT_WEIGHT),
    (re.compile(r"(?i)\b(git|github|gitlab|bitbucket|jira|confluence|agile|scrum|kanban)\b"), _SUPPORT_WEIGHT),
    (re.compile(r"(?i)\b(machine\s*learning|deep\s*learning|nlp|cv|computer\s*vision|"
                r"llm|generative\s*ai|gen\s*ai)\b"), _CORE_WEIGHT),
    (re.compile(r"(?i)\b(microservices|serverless|event[- ]?driven|eventbus)\b"), _CORE_WEIGHT),
    (re.compile(r"(?i)\b(leadership|communication|problem[- ]solving|teamwork|"
                r"presentation|mentoring)\b"), _SOFT_WEIGHT),
]


def _infer_skill_weight(skill: str) -> float:
    """Heuristic weight cho skill trích từ JD (không có occupation profile)."""
    for pat, weight in _WEIGHT_SIGNALS:
        if pat.search(skill):
            return weight
    return _DEFAULT_WEIGHT


# ─── Skill matching helper ────────────────────────────────────────────────────

def _match_skills(candidate_skills: list[str], jd_skills: list[str]) -> tuple[list[str], list[str]]:
    """Match candidate skills vs JD skills — trả về (matched, missing)."""
    cand_lower = {s.lower().strip() for s in candidate_skills}
    matched, missing = [], []
    for skill in jd_skills:
        sl = skill.lower().strip()
        if sl in cand_lower:
            matched.append(skill)
        else:
            # Partial match
            if any(sl in cl or cl in sl for cl in cand_lower):
                matched.append(skill)
            else:
                missing.append(skill)
    return matched, missing


# ─── Main service ─────────────────────────────────────────────────────────────

def compare_cv_with_jd(
    cv_file_bytes: bytes,
    cv_filename: str,
    jd_file_bytes: bytes,
    jd_filename: str,
) -> dict:
    """
    So sánh trực tiếp CV với Job Description.

    Args:
        cv_file_bytes:  Nội dung file CV (PDF/DOCX/MD).
        cv_filename:   Tên file CV (để detect format).
        jd_file_bytes:  Nội dung file JD (PDF/DOCX/MD).
        jd_filename:    Tên file JD (để detect format).

    Returns:
        dict với keys:
          jd_filename, jd_position, jd_skills, jd_text_preview,
          semantic_similarity_score, weighted_skill_score, coverage_pct,
          matched_skills, missing_skills, candidate_profile,
          ai_recommendation
    """
    from src.online.extraction_step2.text_extractor import extract_text_from_bytes
    from src.online.skill_extraction_step3.candidate_skill_extractor import (
        extract_candidate_skills,
    )
    from src.online.candidate_profile_step4.profile_builder import (
        build_candidate_profile,
    )
    from src.offline.preprocessing_step1.text_cleaner import clean_text
    from src.offline.skill_extraction_step2.extractor import extract_skills_from_text
    from src.offline.skill_normalize import canonicalize_skill
    from src.online.semantic_matching_step7.semantic_matcher import (
        compute_semantic_score,
    )
    from src.online.recommendation_step11.jd_recommender import (
        generate_jd_recommendation,
    )

    # ── Step 1: Extract CV text ────────────────────────────────────────────
    logger.info(f"JD Comparison: extract CV from '{cv_filename}'")
    cv_text = extract_text_from_bytes(cv_file_bytes, cv_filename)
    if not cv_text or not cv_text.strip():
        raise ValueError("Không trích được văn bản từ file CV.")
    logger.info(f"CV text length: {len(cv_text)} chars")

    # ── Step 2: Extract JD text ──────────────────────────────────────────────
    logger.info(f"JD Comparison: extract JD from '{jd_filename}'")
    jd_text = extract_text_from_bytes(jd_file_bytes, jd_filename)
    if not jd_text or not jd_text.strip():
        raise ValueError("Không trích được văn bản từ file JD.")
    jd_text_preview = jd_text[:2000]
    logger.info(f"JD text length: {len(jd_text)} chars")

    # ── Step 3: Extract JD position ────────────────────────────────────────
    jd_position = _extract_position_hint(jd_text)
    logger.info(f"JD position hint: '{jd_position}'")

    # ── Step 4: Extract JD skills ───────────────────────────────────────────
    jd_clean = clean_text(jd_text)
    raw_jd_skills = extract_skills_from_text(jd_clean)
    seen: set[str] = set()
    jd_skills: list[str] = []
    for s in raw_jd_skills:
        cs = canonicalize_skill(s)
        if cs and cs.lower() not in seen:
            seen.add(cs.lower())
            jd_skills.append(cs)
    logger.info(f"Trích {len(jd_skills)} skills từ JD")

    # ── Step 5: Candidate profile ────────────────────────────────────────────
    candidate_skills = extract_candidate_skills(cv_text)
    candidate_profile: CandidateProfile = build_candidate_profile(cv_text)
    # Override skills với hybrid-extracted list
    candidate_profile = CandidateProfile(
        skills=candidate_skills,
        experience=candidate_profile.experience,
        projects=candidate_profile.projects,
        education=candidate_profile.education,
    )
    logger.info(f"Candidate skills (hybrid): {len(candidate_skills)}")

    # ── Step 6: Match skills ───────────────────────────────────────────────
    matched_skills, missing_skills = _match_skills(candidate_skills, jd_skills)
    logger.info(
        f"JD skill match: {len(matched_skills)} matched / {len(missing_skills)} missing "
        f"({len(jd_skills)} total JD skills)"
    )

    # ── Step 7: Weighted Skill Score ───────────────────────────────────────
    if jd_skills:
        # Sum weights của matched skills / sum weights của ALL JD skills
        matched_w = sum(_infer_skill_weight(s) for s in matched_skills)
        total_w = sum(_infer_skill_weight(s) for s in jd_skills)
        weighted_skill_score = matched_w / total_w if total_w > 0 else 0.0
    else:
        weighted_skill_score = 0.0
    coverage_pct = len(matched_skills) / len(jd_skills) if jd_skills else 0.0
    logger.info(f"Weighted Skill Score: {weighted_skill_score:.3f}, Coverage: {coverage_pct:.1%}")

    # ── Step 8: Semantic similarity ──────────────────────────────────────────
    # compute_semantic_score nhận 2 embedding (list[float]), không phải raw text.
    # Embed CV text (rút gọn) và JD text (rút gọn) bằng shared model → cosine.
    from src.online.embedding_step5.candidate_embedder import get_shared_model

    cv_embed_text = cv_text[:3000]
    jd_embed_text = jd_text[:3000]
    model = get_shared_model()
    cv_vec = model.encode([cv_embed_text], normalize_embeddings=True,
                          convert_to_numpy=True, show_progress_bar=False)[0]
    jd_vec = model.encode([jd_embed_text], normalize_embeddings=True,
                          convert_to_numpy=True, show_progress_bar=False)[0]
    semantic_similarity_score = compute_semantic_score(
        cv_vec.tolist() if hasattr(cv_vec, "tolist") else list(cv_vec),
        jd_vec.tolist() if hasattr(jd_vec, "tolist") else list(jd_vec),
    )
    logger.info(f"Semantic Similarity: {semantic_similarity_score:.3f}")

    # ── Step 9: AI CV Review ────────────────────────────────────────────────
    extra_skills = [s for s in candidate_skills if s not in jd_skills]
    ai_recommendation: Optional[dict] = generate_jd_recommendation(
        candidate_profile=candidate_profile,
        jd_text=jd_text,
        jd_position=jd_position,
        jd_skills=jd_skills,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        extra_skills=extra_skills,
        semantic_similarity_score=semantic_similarity_score,
        weighted_skill_score=weighted_skill_score,
        coverage_pct=coverage_pct,
    )
    if ai_recommendation is None:
        ai_recommendation = {}

    # ── Step 10: Build response ─────────────────────────────────────────────
    candidate_profile_dict = {
        **candidate_profile.to_dict(),
        "raw_text": candidate_profile.raw_text,
    }
    return {
        "jd_filename": jd_filename,
        "jd_position": jd_position or "(không xác định được)",
        "jd_skills": jd_skills,
        "jd_text_preview": jd_text_preview,
        "semantic_similarity_score": float(semantic_similarity_score),
        "weighted_skill_score": float(weighted_skill_score),
        "coverage_pct": float(coverage_pct),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "candidate_profile": candidate_profile_dict,
        "ai_recommendation": ai_recommendation,
        # cv_review là alias của ai_recommendation cho JD mode (cùng schema 6 phần) —
        # routes.py map cả 2 field của JDComparisonResponse.
        "cv_review": ai_recommendation,
    }


def _rebuild_context(
    candidate_profile: dict,
    semantic_similarity_score: float,
    weighted_skill_score: float,
    matched_skills: list[str],
    missing_skills: list[str],
) -> tuple[CandidateProfile, ScoreBreakdown, SkillGap]:
    """Dựng lại CandidateProfile/ScoreBreakdown/SkillGap từ dict đã tính sẵn (gửi
    ngược từ frontend) — dùng chung cho cả 2 hàm sinh nội dung bổ trợ dưới đây."""
    profile = CandidateProfile(
        skills=candidate_profile.get("skills", []),
        experience=candidate_profile.get("experience", []),
        projects=candidate_profile.get("projects", []),
        education=candidate_profile.get("education", []),
        raw_text=candidate_profile.get("raw_text", ""),
    )
    scores = ScoreBreakdown(
        semantic_similarity_score=semantic_similarity_score,
        weighted_skill_score=weighted_skill_score,
    )
    skill_gap = SkillGap(matched_skills=matched_skills, missing_skills=missing_skills)
    return profile, scores, skill_gap


def generate_cv_improvement_for_jd(
    candidate_profile: dict,
    jd_position: str,
    jd_skills: list[str],
    semantic_similarity_score: float,
    weighted_skill_score: float,
    matched_skills: list[str],
    missing_skills: list[str],
) -> Optional[dict]:
    """
    Sinh AI CV Improvement cho JD Comparison, dùng lại profile + điểm số đã tính.

    Args:
        candidate_profile: dict (skills/experience/projects/education/raw_text) —
            từ kết quả compare_cv_with_jd()["candidate_profile"].
        jd_position, jd_skills: bối cảnh JD đã trích ở bước so sánh.
    """
    from src.online.cv_improvement.jd_improver import generate_jd_cv_improvement

    profile, scores, skill_gap = _rebuild_context(
        candidate_profile, semantic_similarity_score, weighted_skill_score,
        matched_skills, missing_skills,
    )
    return generate_jd_cv_improvement(
        jd_position=jd_position,
        jd_skills=jd_skills,
        scores=scores,
        candidate_profile=profile,
        skill_gap=skill_gap,
    )


def generate_application_email_for_jd(
    candidate_profile: dict,
    jd_position: str,
    jd_skills: list[str],
    jd_text_preview: str,
    semantic_similarity_score: float,
    weighted_skill_score: float,
    matched_skills: list[str],
    missing_skills: list[str],
    cv_review: Optional[dict] = None,
) -> Optional[dict]:
    """
    Sinh Application Email cho JD Comparison, dùng lại profile + điểm số + AI CV
    Review đã tính (nếu có).

    Args:
        candidate_profile: dict — từ compare_cv_with_jd()["candidate_profile"].
        jd_position, jd_skills, jd_text_preview: bối cảnh JD đã trích.
        cv_review: AI CV Review đã sinh trước đó (bối cảnh, có thể None).
    """
    from src.online.email_generation.jd_email_generator import generate_jd_application_email

    profile, scores, skill_gap = _rebuild_context(
        candidate_profile, semantic_similarity_score, weighted_skill_score,
        matched_skills, missing_skills,
    )
    return generate_jd_application_email(
        jd_position=jd_position,
        jd_skills=jd_skills,
        jd_text_preview=jd_text_preview,
        scores=scores,
        candidate_profile=profile,
        skill_gap=skill_gap,
        cv_review=cv_review,
    )
