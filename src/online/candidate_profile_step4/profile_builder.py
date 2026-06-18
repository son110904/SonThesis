"""
profile_builder.py – Dựng Candidate Profile từ văn bản CV.

Bước 3-4 của Online Pipeline. Chiến lược LAI:
    - skills:                regex extractor (nhất quán với Occupation Profile)
    - experience/projects/education: LLM (GPT-4o Mini) trích có cấu trúc

Nếu LLM không khả dụng (thiếu key) → 3 trường LLM trả [] nhưng skills vẫn có,
đủ cho semantic matching + weighted skill scoring.
"""

from __future__ import annotations

import logging
from typing import Optional

from src.config import MAX_CV_CHARS
from src.models import CandidateProfile
from src.online.skill_extraction_step3 import extract_candidate_skills
from src.online.recommendation_step11.llm_client import LLMClient, get_llm_client

logger = logging.getLogger(__name__)

_EXTRACTION_SYSTEM_PROMPT = (
    "Bạn là trợ lý trích xuất thông tin từ CV. Đọc CV và trả về JSON đúng schema, "
    "không thêm giải thích. Mỗi mục là một chuỗi ngắn gọn. Nếu không có thông tin, "
    "trả về mảng rỗng. Giữ nguyên ngôn ngữ gốc trong CV."
)

_EXTRACTION_USER_TEMPLATE = (
    "Trích xuất từ CV dưới đây thành JSON với đúng các khóa sau:\n"
    '{{\n'
    '  "experience": ["mỗi phần tử là 1 mục kinh nghiệm: vị trí - công ty - thời gian - mô tả ngắn"],\n'
    '  "projects":   ["mỗi phần tử là 1 dự án: tên - vai trò - công nghệ - kết quả"],\n'
    '  "education":  ["mỗi phần tử là 1 mục học vấn: bằng cấp - trường - chuyên ngành - năm"]\n'
    '}}\n\n'
    "CV:\n\"\"\"\n{cv_text}\n\"\"\""
)


def _extract_structured_sections(
    raw_text: str,
    llm: LLMClient,
) -> dict[str, list[str]]:
    """Dùng LLM trích experience/projects/education. Trả dict rỗng nếu lỗi/thiếu key."""
    empty = {"experience": [], "projects": [], "education": []}
    if not llm.is_available():
        return empty

    user_prompt = _EXTRACTION_USER_TEMPLATE.format(cv_text=raw_text[:MAX_CV_CHARS])
    data = llm.chat_json(_EXTRACTION_SYSTEM_PROMPT, user_prompt)
    if not data:
        return empty

    result: dict[str, list[str]] = {}
    for key in ("experience", "projects", "education"):
        value = data.get(key, [])
        if isinstance(value, list):
            result[key] = [str(v).strip() for v in value if str(v).strip()]
        elif isinstance(value, str) and value.strip():
            result[key] = [value.strip()]
        else:
            result[key] = []
    logger.info(
        f"LLM trích: experience={len(result['experience'])}, "
        f"projects={len(result['projects'])}, education={len(result['education'])}"
    )
    return result


def build_candidate_profile(
    raw_text: str,
    llm: Optional[LLMClient] = None,
) -> CandidateProfile:
    """
    Dựng Candidate Profile từ văn bản CV.

    Args:
        raw_text: Văn bản CV thô (từ text_extractor).
        llm:      LLMClient (None → dùng client mặc định).

    Returns:
        CandidateProfile với skills (regex) + experience/projects/education (LLM).
    """
    llm = llm or get_llm_client()

    skills = extract_candidate_skills(raw_text)
    sections = _extract_structured_sections(raw_text, llm)

    profile = CandidateProfile(
        skills=skills,
        experience=sections["experience"],
        projects=sections["projects"],
        education=sections["education"],
        raw_text=raw_text,
    )
    logger.info(f"Candidate Profile: {len(skills)} skills")
    return profile
