"""
candidate_skill_extractor.py – Trích kỹ năng ứng viên từ văn bản CV.

Bước 3 (phần skills) của Online Pipeline.

Dùng LẠI regex extractor của offline (extract_skills_from_text) để đảm bảo
skill của ứng viên và skill trong Occupation Profile cùng một "từ điển" →
weighted_skill_score so khớp chính xác.
"""

from __future__ import annotations

import logging

from src.offline.preprocessing.text_cleaner import clean_text
from src.offline.skill_extraction.extractor import extract_skills_from_text

logger = logging.getLogger(__name__)


def extract_candidate_skills(raw_text: str) -> list[str]:
    """
    Trích danh sách kỹ năng từ CV.

    Args:
        raw_text: Văn bản CV thô (từ text_extractor).

    Returns:
        List kỹ năng không trùng, đã lọc stop-skills, cùng định dạng với
        skill trong Occupation Profile.
    """
    if not raw_text or not raw_text.strip():
        return []

    cleaned = clean_text(raw_text)
    skills = extract_skills_from_text(cleaned)
    logger.info(f"Trích {len(skills)} kỹ năng từ CV (regex)")
    return skills
