"""
email_generator.py – AI Application Email Generator.

Chỉ được gọi khi người dùng CHỦ ĐỘNG bấm nút "Tạo email ứng tuyển" (tiết kiệm chi
phí LLM) — KHÁC với AI CV Review/AI CV Improvement (tự động). Email luôn sinh cho
đúng nghề (Occupation Profile) mà người dùng đang xem, tái dùng Candidate Profile,
scores, matched/missing skills và (nếu có) AI CV Review đã sinh trước đó.

Trước khi soạn email, LLM phải tự xác định "Matching Highlights" — các điểm mạnh
trong CV khớp nhất với vị trí — CHỈ từ kỹ năng/kinh nghiệm/dự án THỰC SỰ có trong CV.

Thiếu OPENAI_API_KEY hoặc CV quá sơ sài để cá nhân hóa → trả None.
"""

from __future__ import annotations

import logging
from typing import Optional

from src.models import CandidateProfile, ScoreBreakdown, SkillGap
from src.online.recommendation_step11.llm_client import LLMClient, get_llm_client

logger = logging.getLogger(__name__)

# Giới hạn ký tự CV gốc đưa vào prompt (đủ để tìm tên ứng viên, tránh tốn token).
_MAX_RAW_CV_CHARS = 3000

_SYSTEM_PROMPT = (
    "Bạn là chuyên gia viết email ứng tuyển (career mentor), đang soạn email ứng "
    "tuyển CÁ NHÂN HÓA cho một ứng viên gửi tới nhà tuyển dụng.\n"
    "RÀNG BUỘC BẮT BUỘC:\n"
    "1. CHỈ được dùng kỹ năng, kinh nghiệm, dự án THỰC SỰ có trong hồ sơ ứng viên "
    "được cung cấp. TUYỆT ĐỐI không bịa thêm thành tích, số liệu, công nghệ hay kinh "
    "nghiệm không xuất hiện trong CV.\n"
    "2. Trước khi viết email, xác định 'matching_highlights' — các điểm mạnh trong CV "
    "phù hợp NHẤT với vị trí này (dựa trên matched skills + kinh nghiệm/dự án liên "
    "quan) và ưu tiên nhấn mạnh các điểm đó trong email.\n"
    "3. Email PHẢI: chuyên nghiệp, ngắn gọn (150-250 từ phần body), tự nhiên, KHÔNG "
    "dùng mẫu email cứng nhắc/rập khuôn — viết như một người thật đang ứng tuyển.\n"
    "4. Email cần có đủ: lời chào, giới thiệu ngắn gọn về bản thân, vị trí ứng tuyển, "
    "liên hệ trực tiếp giữa kinh nghiệm/dự án/kỹ năng trong CV với yêu cầu vị trí, "
    "mong muốn được trao đổi trong buổi phỏng vấn, và lời cảm ơn.\n"
    "5. Nếu hồ sơ không đủ thông tin để viết một phần nào đó (vd không có dự án), hãy "
    "BỎ QUA phần đó thay vì suy diễn hay bịa thêm.\n"
    "6. 'Trách nhiệm công việc' trong Occupation Profile là dữ liệu TỔNG HỢP từ RẤT "
    "NHIỀU tin tuyển dụng của NHIỀU công ty khác nhau (không phải 1 công ty cụ thể). "
    "Đoạn text đó có thể VÔ TÌNH chứa tên riêng của một công ty nào đó — TUYỆT ĐỐI "
    "KHÔNG được coi đó là công ty ứng viên đang ứng tuyển và KHÔNG được nêu tên công "
    "ty cụ thể nào trong email. Luôn xưng hô chung chung, vd 'Kính gửi Bộ phận Tuyển "
    "dụng' hoặc 'Kính gửi Quý công ty'.\n"
    "7. Thân thư PHẢI kết thúc bằng ĐÚNG hai chữ 'Trân trọng.' và DỪNG LẠI ở đó. "
    "TUYỆT ĐỐI KHÔNG thêm khối chữ ký sau đó: không ghi tên ứng viên, email, số điện "
    "thoại, chức danh hay bất kỳ thông tin liên hệ nào ở cuối thư.\n"
    "8. Tìm TÊN THẬT của ứng viên trong 'Nội dung CV gốc' bên dưới (thường ở đầu CV, "
    "phần tiêu đề/liên hệ) để đưa vào TIÊU ĐỀ email theo đúng mẫu: "
    "'Ứng tuyển vị trí [Tên vị trí] - {tên ứng viên}'. "
    "TUYỆT ĐỐI KHÔNG bịa ra một cái tên (vd không dùng tên ví dụ như 'Nguyễn Văn A' "
    "nếu đó không phải tên thật trong CV). Nếu CV không có tên rõ ràng, tiêu đề chỉ "
    "ghi 'Ứng tuyển vị trí [Tên vị trí]'.\n"
    "9. Trả về DUY NHẤT một JSON hợp lệ theo schema yêu cầu, bằng tiếng Việt."
)

_JSON_SCHEMA_HINT = """Trả về JSON với đúng các khóa sau:
{
  "subject": "string — tiêu đề email theo đúng mẫu 'Ứng tuyển vị trí {occupation} - {tên ứng viên}'",
  "body": "string — nội dung email, bắt đầu bằng lời chào và KẾT THÚC bằng 'Trân trọng.' (KHÔNG có chữ ký/tên/email/SĐT sau đó), CÓ xuống dòng \\n giữa các đoạn",
  "matching_highlights": ["string — điểm mạnh trong CV khớp nhất với vị trí, CHỈ từ kỹ năng/kinh nghiệm/dự án có thật trong CV"]
}"""

_USER_TEMPLATE = """Hãy soạn email ứng tuyển cho vị trí "{occupation}".

## Tín hiệu điểm số (THANG 0-100, chỉ để tham khảo — KHÔNG nhắc số điểm trong email)
- Semantic Similarity: {semantic:.0f}
- Weighted Skill Score: {weighted:.0f}

## Yêu cầu của vị trí (Occupation Profile — TỔNG HỢP từ nhiều tin tuyển dụng, KHÔNG phải 1 công ty cụ thể; nếu thấy tên công ty trong đây thì bỏ qua, không đưa vào email)
- Kỹ năng cốt lõi (core): {core_skills}
- Trách nhiệm công việc: {responsibilities}

## Hồ sơ ứng viên (NGUỒN SỰ THẬT DUY NHẤT — không được vượt ra ngoài)
- Kỹ năng: {cand_skills}
- Kinh nghiệm:
{cand_exp}
- Dự án:
{cand_proj}
- Học vấn: {cand_edu}

## Đối chiếu kỹ năng
- Đã đáp ứng (matched): {matched}
- Còn thiếu (missing, KHÔNG nhắc trong email): {missing}

## AI CV Review đã sinh trước đó (bối cảnh, không copy nguyên văn vào email)
{cv_review_summary}

## Nội dung CV gốc (dùng để LẤY ĐÚNG TÊN ứng viên — xem ràng buộc 7)
\"\"\"
{raw_text}
\"\"\"

{schema}

Chỉ trả về JSON, không kèm văn bản ngoài JSON."""


def _fmt_inline(items: list[str], limit: int = 25) -> str:
    if not items:
        return "(không có)"
    shown = items[:limit]
    suffix = f" … (+{len(items) - limit})" if len(items) > limit else ""
    return ", ".join(shown) + suffix


def _fmt_bullets(items: list[str], limit: int = 8) -> str:
    if not items:
        return "  (không có)"
    return "\n".join(f"  - {it}" for it in items[:limit])


def _fmt_cv_review_summary(cv_review: Optional[dict]) -> str:
    """Tóm tắt ngắn AI CV Review để LLM có bối cảnh, không đưa toàn bộ để tiết kiệm token."""
    if not cv_review or cv_review.get("_sparse"):
        return "(chưa có)"
    overall = cv_review.get("overall_assessment", "")
    strengths = cv_review.get("strengths", [])[:5]
    parts = []
    if overall:
        parts.append(f"Đánh giá tổng quan: {overall}")
    if strengths:
        parts.append("Điểm mạnh đã ghi nhận: " + "; ".join(strengths))
    return "\n".join(parts) if parts else "(chưa có)"


def _normalize_email(raw: dict) -> Optional[dict]:
    """Đảm bảo đủ 3 khóa; trả None nếu thiếu subject/body (không có gì để hiển thị)."""
    subject = str(raw.get("subject") or "").strip()
    body = str(raw.get("body") or "").strip()
    if not subject or not body:
        return None

    highlights_raw = raw.get("matching_highlights") or []
    highlights: list[str] = []
    if isinstance(highlights_raw, list):
        highlights = [str(h).strip() for h in highlights_raw if str(h).strip()]
    elif isinstance(highlights_raw, str) and highlights_raw.strip():
        highlights = [highlights_raw.strip()]

    return {"subject": subject, "body": body, "matching_highlights": highlights}


def generate_application_email(
    occupation_display: str,
    occupation_profile: dict,
    scores: ScoreBreakdown,
    candidate_profile: CandidateProfile,
    skill_gap: SkillGap,
    cv_review: Optional[dict] = None,
    llm: Optional[LLMClient] = None,
) -> Optional[dict]:
    """
    Sinh Application Email cá nhân hóa cho 1 nghề (chỉ khi người dùng bấm nút).

    Returns:
        dict {"subject", "body", "matching_highlights"}, hoặc None nếu LLM không khả
        dụng, lỗi, hoặc hồ sơ quá sơ sài để cá nhân hóa (tránh email chung chung/bịa).
    """
    from src.online.validation.profile_completeness import assess_profile_completeness

    is_sparse, _missing = assess_profile_completeness(candidate_profile)
    if is_sparse:
        logger.info("CV sơ sài → bỏ qua Application Email (tránh nội dung chung chung).")
        return None

    llm = llm or get_llm_client()
    if not llm.is_available():
        logger.warning("LLM không khả dụng → bỏ qua Application Email.")
        return None

    core_skills = list(occupation_profile.get("core_skills", {}).keys())
    responsibilities = occupation_profile.get("responsibilities", [])
    if isinstance(responsibilities, dict):
        responsibilities = list(responsibilities.keys())

    user_prompt = _USER_TEMPLATE.format(
        occupation=occupation_display,
        semantic=scores.semantic_similarity_score * 100,
        weighted=scores.weighted_skill_score * 100,
        core_skills=_fmt_inline(core_skills, 20),
        responsibilities=_fmt_inline(list(responsibilities), 12),
        cand_skills=_fmt_inline(candidate_profile.skills, 30),
        cand_exp=_fmt_bullets(candidate_profile.experience, 8),
        cand_proj=_fmt_bullets(candidate_profile.projects, 8),
        cand_edu=_fmt_inline(candidate_profile.education, 5),
        matched=_fmt_inline(skill_gap.matched_skills, 30),
        missing=_fmt_inline(skill_gap.missing_skills, 25),
        cv_review_summary=_fmt_cv_review_summary(cv_review),
        raw_text=(candidate_profile.raw_text or "")[:_MAX_RAW_CV_CHARS],
        schema=_JSON_SCHEMA_HINT,
    )

    raw = llm.chat_json(_SYSTEM_PROMPT, user_prompt, temperature=0.4, max_tokens=1200)
    if not raw:
        logger.warning("Application Email: LLM trả rỗng/parse lỗi.")
        return None

    email = _normalize_email(raw)
    if email:
        logger.info(f"Application Email sinh thành công (subject='{email['subject']}').")
    else:
        logger.warning("Application Email: JSON trả về thiếu subject/body.")
    return email
