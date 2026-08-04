"""
improver.py – AI CV Improvement.

Sinh THÊM một báo cáo cải thiện CV ngay sau khi AI CV Review hoàn thành (Bước 11).
KHÔNG phải một mô hình khác — tái dùng đúng Candidate Profile, Occupation Profile,
Match Score và LLM client dùng chung với AI CV Review.

Đầu ra gồm 4 phần:
    - structure_review     : Bố cục CV — MỖI nhận xét phải chỉ rõ vị trí trong CV.
    - writing_review        : Chất lượng diễn đạt — MỖI vấn đề phải giải thích lý do.
    - grammar_review        : Lỗi chính tả/ngữ pháp/viết hoa/dấu câu/định dạng.
    - rewrite_suggestions   : Viết lại từng bullet yếu — CHỈ dùng thông tin đã có
                              trong CV, KHÔNG bịa thêm thành tích hay số liệu.

Thiếu OPENAI_API_KEY hoặc CV quá sơ sài → trả None (tầng trên bỏ qua, không hiển thị).
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from src.models import CandidateProfile, ScoreBreakdown, SkillGap
from src.online.recommendation_step11.llm_client import LLMClient, get_llm_client

logger = logging.getLogger(__name__)

# Giới hạn ký tự CV gốc đưa vào prompt (đủ để đánh giá bố cục/chính tả, tránh tốn token).
_MAX_RAW_CV_CHARS = 6000

# Heuristic phát hiện ngôn ngữ CV: đếm MẬT ĐỘ ký tự có dấu tiếng Việt trên tổng số
# ký tự chữ cái. Dùng mật độ (không phải "có/không") để tránh nhận nhầm 1 CV tiếng
# Anh có TÊN người Việt (vd "Phạm Hồng Sơn" xuất hiện 1-2 lần) thành CV tiếng Việt.
_VN_DIACRITIC_RE = re.compile(
    "[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]",
    re.IGNORECASE,
)
_ALPHA_RE = re.compile(r"[^\W\d_]", re.UNICODE)
_VN_DENSITY_THRESHOLD = 0.05


def _detect_cv_language(raw_text: str) -> str:
    """'vi' nếu CV chủ yếu viết tiếng Việt, ngược lại 'en' (mặc định khi mơ hồ/rỗng)."""
    if not raw_text:
        return "en"
    alpha_count = len(_ALPHA_RE.findall(raw_text))
    if alpha_count == 0:
        return "en"
    vn_count = len(_VN_DIACRITIC_RE.findall(raw_text))
    return "vi" if (vn_count / alpha_count) >= _VN_DENSITY_THRESHOLD else "en"

_SYSTEM_PROMPT = (
    "Bạn là chuyên gia tư vấn viết CV (CV writing coach), đang rà soát lại một CV đã "
    "được review sơ bộ để đưa ra góp ý CẢI THIỆN cụ thể.\n"
    "RÀNG BUỘC BẮT BUỘC:\n"
    "1. Chỉ dùng NỘI DUNG THỰC TẾ có trong CV gốc và hồ sơ ứng viên được cung cấp. "
    "TUYỆT ĐỐI không bịa thêm kỹ năng, kinh nghiệm, dự án, thành tích hay số liệu.\n"
    "2. Mục 'structure_review' (bố cục): CHỈ ghi nhận khi THỰC SỰ thiếu một mục QUAN "
    "TRỌNG (Education, Experience, Projects). TUYỆT ĐỐI không nhận xét hay đề xuất đảo "
    "thứ tự Contact, Skills, Education, Experience, Projects — mỗi ngành/nhà tuyển dụng "
    "có convention riêng. Coi các tên gọi ĐỒNG NGHĨA là cùng một mục ĐÃ CÓ: "
    "Summary/Objective/Profile/About Me/Introduction/Giới thiệu/Mục tiêu nghề nghiệp; "
    "Skills/Kỹ năng; Experience/Kinh nghiệm; Education/Học vấn; Projects/Dự án. "
    "Nếu bố cục hợp lý, trả về mảng rỗng. Không nhận xét chung chung.\n"
    "3. Mục 'writing_review' (diễn đạt): mỗi vấn đề phát hiện PHẢI giải thích lý do "
    "(vd 'Bullet dự án X chỉ có 4 từ, chưa nêu công nghệ/kết quả nên nhà tuyển dụng "
    "không đánh giá được đóng góp thực tế').\n"
    "4. Mục 'grammar_review': chỉ liệt kê lỗi chính tả/ngữ pháp/viết hoa/dấu câu/định "
    "dạng THỰC SỰ tìm thấy trong CV gốc, đánh giá theo ĐÚNG ngôn ngữ CV được nêu ở "
    "cuối prompt. Nếu KHÔNG tìm thấy lỗi nào, trả về mảng CHỨA ĐÚNG 1 chuỗi theo ngôn "
    "ngữ đó (xem hướng dẫn cuối prompt).\n"
    "5. Mục 'rewrite_suggestions' là QUAN TRỌNG NHẤT: chọn các bullet kinh nghiệm/dự án "
    "còn yếu (ngắn, chung chung, thiếu động từ hành động, thiếu số liệu, chưa nêu vai "
    "trò/kết quả) và viết lại rõ ràng, chuyên nghiệp hơn. 'current' PHẢI trích gần "
    "đúng nguyên văn từ hồ sơ ứng viên. 'rewrite' CHỈ được diễn đạt lại/làm rõ thông "
    "tin ĐÃ CÓ — TUYỆT ĐỐI không thêm số liệu, công nghệ hay kết quả không xuất hiện "
    "trong CV, và PHẢI viết bằng ĐÚNG ngôn ngữ của bullet gốc ('current') — TUYỆT ĐỐI "
    "KHÔNG dịch sang ngôn ngữ khác, vì ứng viên cần dán thẳng 'rewrite' vào lại CV của "
    "họ. Nếu một bullet đã đủ tốt, đừng đưa vào danh sách này.\n"
    "6. 'structure_review' và 'writing_review' LUÔN viết bằng tiếng Việt (đây là nhận "
    "xét cho người dùng đọc trên ứng dụng, không phải nội dung dán lại vào CV) — chỉ "
    "riêng 'rewrite_suggestions' và câu 'không có lỗi' trong 'grammar_review' mới theo "
    "ngôn ngữ CV như ràng buộc 4-5.\n"
    "7. Trả về DUY NHẤT một JSON hợp lệ theo schema yêu cầu."
)

_JSON_SCHEMA_HINT = """Trả về JSON với đúng các khóa sau:
{
  "structure_review": ["string (tiếng Việt) — nhận xét bố cục, PHẢI chỉ rõ vị trí trong CV"],
  "writing_review": ["string (tiếng Việt) — nhận xét diễn đạt, PHẢI giải thích lý do"],
  "grammar_review": ["string (theo NGÔN NGỮ CV) — lỗi chính tả/ngữ pháp cụ thể, hoặc đúng 1 phần tử là câu 'không có lỗi' theo ngôn ngữ CV nếu không phát hiện lỗi"],
  "rewrite_suggestions": [
    {"current": "string — bullet gốc trích từ CV", "rewrite": "string (CÙNG ngôn ngữ với 'current') — bản viết lại, KHÔNG bịa thêm thông tin"}
  ]
}"""

# Câu "không có lỗi" mặc định theo từng ngôn ngữ — LLM được yêu cầu dùng nguyên văn
# 1 trong 2 câu này (xem ràng buộc 4), và đây cũng là fallback nếu LLM trả rỗng.
_NO_GRAMMAR_ISSUES_TEXT: dict[str, str] = {
    "vi": "Không phát hiện lỗi chính tả/ngữ pháp đáng kể.",
    "en": "No major grammar issues detected.",
}

_USER_TEMPLATE = """Đây là bước tiếp theo SAU KHI đã review CV cho vị trí "{occupation}". Hãy đưa ra góp ý CẢI THIỆN CV.

## Tín hiệu điểm số (THANG 0-100, chỉ để tham khảo)
- Match Score tổng: {match_score:.0f}
- Semantic Similarity: {semantic:.0f}
- Weighted Skill Score: {weighted:.0f}

## Yêu cầu của vị trí (Occupation Profile)
- Kỹ năng cốt lõi (core): {core_skills}

## Hồ sơ ứng viên đã trích xuất (kinh nghiệm/dự án là các "bullet" hiện tại trong CV)
- Kỹ năng: {cand_skills}
- Kinh nghiệm:
{cand_exp}
- Dự án:
{cand_proj}
- Học vấn: {cand_edu}

## Đối chiếu kỹ năng
- Đã đáp ứng (matched): {matched}
- Còn thiếu (missing): {missing}

## Nội dung CV gốc (để đánh giá bố cục thứ tự các mục + chính tả/ngữ pháp)
\"\"\"
{raw_text}
\"\"\"

{schema}

## Ngôn ngữ của CV: {cv_language_label}
'rewrite_suggestions' và câu "không có lỗi" trong 'grammar_review' PHẢI dùng ĐÚNG ngôn
ngữ này. Nếu không phát hiện lỗi, dùng NGUYÊN VĂN câu sau: "{no_grammar_issues_text}"

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


def _coerce_str_list(value) -> list[str]:
    """Chuẩn hóa giá trị LLM về list[str] (LLM đôi khi trả string đơn)."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


def _normalize_improvement(raw: dict, cv_language: str) -> dict:
    """Đảm bảo đủ 4 khóa, đúng kiểu — phòng khi LLM lệch schema."""
    rewrites_raw = raw.get("rewrite_suggestions") or []
    rewrites: list[dict] = []
    if isinstance(rewrites_raw, list):
        for item in rewrites_raw:
            if isinstance(item, dict):
                current = str(item.get("current") or "").strip()
                rewrite = str(item.get("rewrite") or "").strip()
                if current and rewrite:
                    rewrites.append({"current": current, "rewrite": rewrite})

    grammar = _coerce_str_list(raw.get("grammar_review"))
    if not grammar:
        grammar = [_NO_GRAMMAR_ISSUES_TEXT[cv_language]]

    return {
        "structure_review": _coerce_str_list(raw.get("structure_review")),
        "writing_review": _coerce_str_list(raw.get("writing_review")),
        "grammar_review": grammar,
        "rewrite_suggestions": rewrites,
    }


def generate_cv_improvement(
    occupation_display: str,
    occupation_profile: dict,
    scores: ScoreBreakdown,
    candidate_profile: CandidateProfile,
    skill_gap: SkillGap,
    llm: Optional[LLMClient] = None,
) -> Optional[dict]:
    """
    Sinh AI CV Improvement (4 phần) — tiếp nối AI CV Review.

    Returns:
        dict 4 khóa (xem _normalize_improvement), hoặc None nếu LLM không khả dụng,
        lỗi, hoặc CV quá sơ sài để góp ý có căn cứ (dùng chung ngưỡng với AI CV Review).
    """
    # CV quá sơ sài → AI CV Review đã hiển thị cảnh báo riêng; không tốn thêm 1 lần
    # gọi LLM để góp ý cải thiện thiếu căn cứ trên hồ sơ gần như trống.
    from src.online.validation.profile_completeness import assess_profile_completeness

    is_sparse, _missing = assess_profile_completeness(candidate_profile)
    if is_sparse:
        logger.info("CV sơ sài → bỏ qua AI CV Improvement.")
        return None

    llm = llm or get_llm_client()
    if not llm.is_available():
        logger.warning("LLM không khả dụng → bỏ qua AI CV Improvement.")
        return None

    core_skills = list(occupation_profile.get("core_skills", {}).keys())
    cv_language = _detect_cv_language(candidate_profile.raw_text)
    cv_language_label = "tiếng Việt" if cv_language == "vi" else "tiếng Anh (English)"

    user_prompt = _USER_TEMPLATE.format(
        occupation=occupation_display,
        match_score=scores.match_score * 100,
        semantic=scores.semantic_similarity_score * 100,
        weighted=scores.weighted_skill_score * 100,
        core_skills=_fmt_inline(core_skills, 20),
        cand_skills=_fmt_inline(candidate_profile.skills, 30),
        cand_exp=_fmt_bullets(candidate_profile.experience, 8),
        cand_proj=_fmt_bullets(candidate_profile.projects, 8),
        cand_edu=_fmt_inline(candidate_profile.education, 5),
        matched=_fmt_inline(skill_gap.matched_skills, 30),
        missing=_fmt_inline(skill_gap.missing_skills, 25),
        raw_text=(candidate_profile.raw_text or "")[:_MAX_RAW_CV_CHARS],
        schema=_JSON_SCHEMA_HINT,
        cv_language_label=cv_language_label,
        no_grammar_issues_text=_NO_GRAMMAR_ISSUES_TEXT[cv_language],
    )

    raw = llm.chat_json(_SYSTEM_PROMPT, user_prompt, temperature=0.3, max_tokens=2000)
    if not raw:
        logger.warning("AI CV Improvement: LLM trả rỗng/parse lỗi.")
        return None

    improvement = _normalize_improvement(raw, cv_language)
    logger.info(
        f"AI CV Improvement sinh thành công "
        f"(structure={len(improvement['structure_review'])}, "
        f"writing={len(improvement['writing_review'])}, "
        f"rewrites={len(improvement['rewrite_suggestions'])})"
    )
    return improvement
