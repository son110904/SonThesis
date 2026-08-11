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
  7. Skill Score = số kỹ năng khớp / số kỹ năng JD yêu cầu
  8. AI CV Review cho JD context (jd_recommender)

Vì sao KHÔNG dùng trọng số ở chế độ này: trọng số kỹ năng trong Occupation
Profile được tính từ tần suất thật trên hàng chục nghìn tin tuyển dụng. Với MỘT
tin tuyển dụng đơn lẻ thì không có dữ liệu thống kê nào để suy ra trọng số, nên
mọi cách gán trọng số ở đây đều là phỏng đoán. Bản trước dùng bảng regex gán
cứng 4 mức, kết quả gần như trùng hoàn toàn với tỉ lệ khớp đơn thuần
(tương quan ~0,999) trong khi thứ tự trọng số lại sai (Python bị chấm thấp hơn
"Machine Learning"). Vì vậy chế độ này dùng thẳng tỉ lệ khớp — trung thực về
mức thông tin thực có, và người dùng đọc hiểu ngay.

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

# JD lưu từ website thường có thanh menu điều hướng ở đầu file ("Về chúng tôi
# Dịch vụ Giải pháp ... Tuyển dụng"). Trước đây bước dự phòng lấy luôn dòng đầu
# có ≥2 từ nên nhận nhầm menu này làm tên vị trí, kéo theo nội dung sai vào cả
# tiêu đề email ứng tuyển. Chặn bằng 2 tín hiệu: quá nhiều từ + chứa từ khóa menu.
_MAX_TITLE_WORDS = 8
_NAV_MENU_RE = re.compile(
    r"trang\s*chủ|về\s*chúng\s*tôi|giới\s*thiệu|liên\s*hệ|dịch\s*vụ|tin\s*tức|"
    r"giải\s*pháp|sản\s*phẩm|khách\s*hàng|home\s|about\s*us|contact|services",
    re.IGNORECASE,
)


def _extract_position_hint(jd_text: str) -> str:
    """
    Trích tên vị trí tuyển dụng từ JD text.

    Trả "" khi không chắc chắn — nơi gọi sẽ hiển thị "(không xác định được)".
    Thà không biết còn hơn đoán sai, vì giá trị này được đưa thẳng vào lời nhắc
    LLM (AI Review / góp ý CV / email ứng tuyển).
    """
    lines = jd_text.splitlines()
    # Ưu tiên 10 dòng đầu
    head = "\n".join(lines[:10])
    for pat in _POSITION_PATTERNS:
        m = pat.search(head)
        if m:
            # Pattern khớp chức danh (backend/devops/...) KHÔNG có nhóm bắt →
            # phải dùng group(0), nếu không sẽ IndexError làm hỏng cả request.
            result = (m.group(1) if m.groups() else m.group(0)).strip()
            if len(result) >= 3:
                return result

    # Dự phòng: dòng đầu tiên trông GIỐNG một chức danh (ngắn, không phải menu).
    for line in lines[:5]:
        line = line.strip()
        if not (2 <= len(line.split()) <= _MAX_TITLE_WORDS) or len(line) > 80:
            continue
        if _NAV_MENU_RE.search(line):
            continue
        if any(line.lower().startswith(k) for k in ("job", "position", "title", "mô tả")):
            continue
        return line

    return ""


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
    jd_file_bytes: Optional[bytes] = None,
    jd_filename: str = "",
    jd_text: Optional[str] = None,
) -> dict:
    """
    So sánh trực tiếp CV với Job Description.

    JD nhận theo MỘT trong hai cách (ưu tiên `jd_text` nếu có cả hai):
      - `jd_text`: nội dung JD người dùng dán/gõ trực tiếp — nhiều tin tuyển dụng
        chỉ tồn tại trên web, không có file để tải về.
      - `jd_file_bytes` + `jd_filename`: file JD (PDF/DOCX/MD).

    Args:
        cv_file_bytes:  Nội dung file CV (PDF/DOCX/MD).
        cv_filename:   Tên file CV (để detect format).
        jd_file_bytes:  Nội dung file JD, bỏ trống nếu dùng `jd_text`.
        jd_filename:    Tên file JD (để detect format).
        jd_text:        Nội dung JD dạng văn bản thuần.

    Returns:
        dict với keys:
          jd_filename, jd_position, jd_skills, jd_text_preview,
          semantic_similarity_score, coverage_pct,
          matched_skills, missing_skills, candidate_profile,
          ai_recommendation

    Raises:
        ValueError: thiếu cả hai nguồn JD, hoặc không trích được văn bản.
    """
    from src.online.extraction_step2.text_extractor import extract_text_from_bytes
    from src.online.skill_extraction_step3.candidate_skill_extractor import (
        extract_candidate_skills,
    )
    from src.online.skill_extraction_step3.llm_skill_extractor import extract_jd_skills
    from src.online.candidate_profile_step4.profile_builder import (
        build_candidate_profile,
    )
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

    # ── Step 2: Lấy JD text (từ ô dán trực tiếp HOẶC từ file) ────────────────
    if jd_text and jd_text.strip():
        jd_text = jd_text.strip()
        jd_filename = jd_filename or "JD dán trực tiếp"
        logger.info(f"JD Comparison: dùng JD dán trực tiếp ({len(jd_text)} chars)")
    elif jd_file_bytes:
        logger.info(f"JD Comparison: extract JD from '{jd_filename}'")
        jd_text = extract_text_from_bytes(jd_file_bytes, jd_filename)
        if not jd_text or not jd_text.strip():
            raise ValueError("Không trích được văn bản từ file JD.")
    else:
        raise ValueError("Vui lòng tải lên file JD hoặc dán nội dung JD.")

    jd_text_preview = jd_text[:2000]
    logger.info(f"JD text length: {len(jd_text)} chars")

    # ── Step 3: Extract JD position ────────────────────────────────────────
    jd_position = _extract_position_hint(jd_text)
    logger.info(f"JD position hint: '{jd_position}'")

    # ── Step 4: Extract JD skills (hybrid regex + LLM) ──────────────────────
    # Dùng CÙNG cơ chế hybrid như phía CV. Trước đây JD chỉ trích bằng regex nên
    # phụ thuộc hoàn toàn vào việc từ khóa có sẵn trong tập mẫu hay không — JD
    # ngành hẹp bị bỏ sót phần lớn yêu cầu, khiến điểm khớp sai lệch.
    jd_skills = extract_jd_skills(jd_text)
    logger.info(f"Trích {len(jd_skills)} skills từ JD")

    # ── Step 5: Candidate profile ────────────────────────────────────────────
    candidate_skills = extract_candidate_skills(cv_text)
    candidate_profile: CandidateProfile = build_candidate_profile(cv_text)
    # Override skills với hybrid-extracted list.
    # PHẢI giữ raw_text: email ứng tuyển dựa vào nội dung CV gốc để lấy ĐÚNG tên
    # ứng viên ký cuối thư; thiếu nó thì chữ ký chỉ ra chung chung "Ứng viên".
    candidate_profile = CandidateProfile(
        skills=candidate_skills,
        experience=candidate_profile.experience,
        projects=candidate_profile.projects,
        education=candidate_profile.education,
        raw_text=candidate_profile.raw_text or cv_text,
    )
    logger.info(f"Candidate skills (hybrid): {len(candidate_skills)}")

    # ── Step 6: Match skills ───────────────────────────────────────────────
    matched_skills, missing_skills = _match_skills(candidate_skills, jd_skills)
    logger.info(
        f"JD skill match: {len(matched_skills)} matched / {len(missing_skills)} missing "
        f"({len(jd_skills)} total JD skills)"
    )

    # ── Step 7: Skill Score = số kỹ năng khớp / số kỹ năng JD yêu cầu ───────
    coverage_pct = len(matched_skills) / len(jd_skills) if jd_skills else 0.0
    logger.info(
        f"Skill Score: {len(matched_skills)}/{len(jd_skills)} = {coverage_pct:.1%}"
    )

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
    coverage_pct: float,
    matched_skills: list[str],
    missing_skills: list[str],
) -> tuple[CandidateProfile, ScoreBreakdown, SkillGap]:
    """Dựng lại CandidateProfile/ScoreBreakdown/SkillGap từ dict đã tính sẵn (gửi
    ngược từ frontend) — dùng chung cho cả 2 hàm sinh nội dung bổ trợ dưới đây.

    Lưu ý: ScoreBreakdown là kiểu dùng CHUNG với chế độ chọn nghề (nơi chỉ số thứ
    hai đúng là weighted_skill_score tính từ trọng số thật). Ở chế độ JD, ô đó
    mang coverage_pct (tỉ lệ khớp) — các prompt LLM cho JD gọi đúng tên "Skill
    Score" nên không gây hiểu nhầm cho mô hình.
    """
    profile = CandidateProfile(
        skills=candidate_profile.get("skills", []),
        experience=candidate_profile.get("experience", []),
        projects=candidate_profile.get("projects", []),
        education=candidate_profile.get("education", []),
        raw_text=candidate_profile.get("raw_text", ""),
    )
    scores = ScoreBreakdown(
        semantic_similarity_score=semantic_similarity_score,
        weighted_skill_score=coverage_pct,
    )
    skill_gap = SkillGap(matched_skills=matched_skills, missing_skills=missing_skills)
    return profile, scores, skill_gap


def generate_cv_improvement_for_jd(
    candidate_profile: dict,
    jd_position: str,
    jd_skills: list[str],
    semantic_similarity_score: float,
    coverage_pct: float,
    matched_skills: list[str],
    missing_skills: list[str],
) -> Optional[dict]:
    """
    Sinh AI CV Improvement cho JD Comparison, dùng lại profile + điểm số đã tính.

    Args:
        candidate_profile: dict (skills/experience/projects/education/raw_text) —
            từ kết quả compare_cv_with_jd()["candidate_profile"].
        jd_position, jd_skills: bối cảnh JD đã trích ở bước so sánh.
        coverage_pct: tỉ lệ kỹ năng JD mà ứng viên đáp ứng (matched/total).
    """
    from src.online.cv_improvement.jd_improver import generate_jd_cv_improvement

    profile, scores, skill_gap = _rebuild_context(
        candidate_profile, semantic_similarity_score, coverage_pct,
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
    jd_skills: list[str],
    jd_text_preview: str,
    semantic_similarity_score: float,
    coverage_pct: float,
    matched_skills: list[str],
    missing_skills: list[str],
    cv_review: Optional[dict] = None,
) -> Optional[dict]:
    """
    Sinh Application Email cho JD Comparison, dùng lại profile + điểm số + AI CV
    Review đã tính (nếu có).

    KHÔNG nhận `jd_position`: tên vị trí là kết quả đoán bằng heuristic nên có thể
    sai, mà đây là thư gửi thật cho nhà tuyển dụng. LLM tự đọc `jd_text_preview`
    để nắm vị trí (xem jd_email_generator).

    Args:
        candidate_profile: dict — từ compare_cv_with_jd()["candidate_profile"].
        jd_skills, jd_text_preview: bối cảnh JD đã trích.
        cv_review: AI CV Review đã sinh trước đó (bối cảnh, có thể None).
    """
    from src.online.email_generation.jd_email_generator import generate_jd_application_email

    profile, scores, skill_gap = _rebuild_context(
        candidate_profile, semantic_similarity_score, coverage_pct,
        matched_skills, missing_skills,
    )
    return generate_jd_application_email(
        jd_skills=jd_skills,
        jd_text_preview=jd_text_preview,
        scores=scores,
        candidate_profile=profile,
        skill_gap=skill_gap,
        cv_review=cv_review,
    )
