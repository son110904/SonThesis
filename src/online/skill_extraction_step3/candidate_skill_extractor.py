"""
candidate_skill_extractor.py – Trích kỹ năng ứng viên từ văn bản CV.

Bước 3 (phần skills) của Online Pipeline.

Hybrid approach (2026-08):
  1. Regex baseline: extract_skills_from_text trên toàn CV (nhanh, deterministic).
  2. LLM extraction: gọi 1 lần để bắt skill ẩn trong Experience/Projects.
  3. Hợp nhất + canonicalize qua ALIAS_MAP/SYNONYM_MAP.

Việc dùng LẠI regex extractor của offline đảm bảo skill của ứng viên và
skill trong Occupation Profile cùng một "từ điển" → weighted_skill_score
so khớp chính xác.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def extract_candidate_skills(raw_text: str) -> list[str]:
    """
    Trích danh sách kỹ năng từ CV (hybrid regex + LLM).

    Args:
        raw_text: Văn bản CV thô (từ text_extractor).

    Returns:
        List kỹ năng không trùng, đã canonicalize, cùng định dạng với
        skill trong Occupation Profile.
    """
    if not raw_text or not raw_text.strip():
        return []

    # Ưu tiên dùng hybrid extractor (regex + LLM cho Experience/Projects).
    # Fallback về regex-only nếu import thất bại (để tránh crash khi
    # online module được dùng mà không có đầy đủ dependencies).
    try:
        from src.online.skill_extraction_step3.llm_skill_extractor import (
            extract_skills_from_sections,
        )
        skills = extract_skills_from_sections(raw_text)
    except Exception:
        # Fallback: regex-only
        from src.offline.preprocessing_step1.text_cleaner import clean_text
        from src.offline.skill_extraction_step2.extractor import (
            extract_skills_from_text,
        )
        from src.offline.skill_normalize import canonicalize_skill

        cleaned = clean_text(raw_text)
        raw_skills = extract_skills_from_text(cleaned)
        seen: set[str] = set()
        skills = []
        for s in raw_skills:
            cs = canonicalize_skill(s)
            if cs and cs.lower() not in seen:
                seen.add(cs.lower())
                skills.append(cs)
        logger.info(f"Fallback regex-only: trích {len(skills)} kỹ năng từ CV")

    logger.info(f"Trích {len(skills)} kỹ năng từ CV (hybrid)")
    return skills
