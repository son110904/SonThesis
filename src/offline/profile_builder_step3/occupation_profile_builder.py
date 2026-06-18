"""
occupation_profile_builder.py – Xây dựng Occupation Profile từ kết quả trích xuất.

Chức năng:
  - Gom tất cả JD cùng nghề (occupation)
  - Hợp nhất danh sách skills (đếm tần suất theo số JD)
  - Hợp nhất danh sách responsibilities (dedup)
  - Output chuẩn theo định dạng yêu cầu

Output mỗi occupation:
    {
        "occupation": str,
        "skills": List[str],            # skills sắp xếp theo tần suất giảm dần
        "skill_counts": Dict[str,int],  # số JD xuất hiện mỗi skill
        "responsibilities": List[str],  # top responsibilities dedup
        "jd_count": int                 # tổng số JD của nghề này
    }
"""

import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

logger = logging.getLogger(__name__)

MAX_RESPONSIBILITIES = 50
MIN_SKILL_OCCURRENCES = 2       # Skill cần xuất hiện trong ít nhất 2 JD


def _normalize_occupation_key(name: str) -> str:
    """Chuẩn hóa tên occupation thành key."""
    return name.strip().lower().replace(" ", "_")


def build_occupation_profiles(extracted_records: list[dict]) -> dict[str, dict]:
    """
    Xây dựng Occupation Profile từ danh sách kết quả trích xuất.

    Args:
        extracted_records: List[dict] từ extractor.extract_all()
                           Keys: occupation, skills, responsibilities.

    Returns:
        Dict[occupation_key → profile_dict]
    """
    logger.info(f"Đang xây dựng Occupation Profile từ {len(extracted_records)} bản ghi...")

    # Mỗi JD: đếm skill xuất hiện theo số JD (không đếm trùng trong 1 JD)
    skill_counters: dict[str, Counter] = defaultdict(Counter)
    resp_pool: dict[str, dict[str, int]] = defaultdict(dict)
    jd_counts: dict[str, int] = defaultdict(int)
    occupation_display: dict[str, str] = {}

    for record in extracted_records:
        occ_raw = record.get("occupation", "unknown")
        if not occ_raw or occ_raw in ("unknown", ""):
            continue

        occ_key = _normalize_occupation_key(occ_raw)
        occupation_display[occ_key] = occ_raw
        jd_counts[occ_key] += 1

        # Đếm skill: mỗi skill chỉ đếm 1 lần/JD (dùng set với lowercase key)
        # Đồng thời chuẩn hóa: giữ form capitalize đầu tiên gặp, loại bỏ trùng lặp case
        seen_in_jd: set[str] = set()
        for orig in record.get("skills", []):
            if not orig or len(orig.strip()) < 2:
                continue
            skill_lower = orig.strip().lower()
            if skill_lower not in seen_in_jd:
                seen_in_jd.add(skill_lower)
                # Dùng title-case đầu tiên làm canonical form
                canonical = orig.strip()
                skill_counters[occ_key][canonical] += 1

        # Hợp nhất responsibilities (giữ thứ tự xuất hiện đầu tiên)
        for resp in record.get("responsibilities", []):
            if resp and len(resp) >= 15:
                dedup_key = resp.strip().lower()[:80]
                if dedup_key not in resp_pool[occ_key]:
                    resp_pool[occ_key][dedup_key] = (
                        len(resp_pool[occ_key]),
                        resp.strip(),
                    )

    # Xây dựng profile cho từng occupation
    profiles: dict[str, dict] = {}

    for occ_key in sorted(jd_counts.keys()):
        total_jd = jd_counts[occ_key]
        counter = skill_counters[occ_key]

        # Lọc skill có đủ lần xuất hiện tối thiểu
        min_occ = max(MIN_SKILL_OCCURRENCES, max(1, int(total_jd * 0.01)))
        filtered = {
            skill: count
            for skill, count in counter.items()
            if count >= min_occ
        }

        # Sắp xếp theo tần suất
        sorted_skills = sorted(filtered.items(), key=lambda x: x[1], reverse=True)

        # Responsibilities: sắp xếp theo thứ tự xuất hiện, lấy text gốc
        resp_ordered = sorted(resp_pool[occ_key].values(), key=lambda x: x[0])
        responsibilities = [text for _, text in resp_ordered[:MAX_RESPONSIBILITIES]]

        profiles[occ_key] = {
            "occupation": occupation_display[occ_key],
            "skills": [skill for skill, _ in sorted_skills],
            "skill_counts": {skill: count for skill, count in sorted_skills},
            "responsibilities": responsibilities,
            "jd_count": total_jd,
        }

    total_skills_avg = (
        sum(len(p["skills"]) for p in profiles.values()) / max(len(profiles), 1)
    )
    logger.info(
        f"Đã xây dựng {len(profiles)} Occupation Profile "
        f"(avg {total_skills_avg:.1f} skills/occupation)"
    )
    return profiles


def build_from_dataframe(
    df_clean: pd.DataFrame,
    extracted_records: Optional[list[dict]] = None,
) -> dict[str, dict]:
    """
    Pipeline hoàn chỉnh: DataFrame đã làm sạch → Occupation Profiles.

    Args:
        df_clean: DataFrame JD sau clean_jd_dataframe.
        extracted_records: Kết quả extractor nếu đã có (để tránh chạy lại).

    Returns:
        Dict occupation profiles.
    """
    if extracted_records is None:
        from src.offline.skill_extraction_step2.extractor import extract_all
        extracted_records = extract_all(df_clean)
    return build_occupation_profiles(extracted_records)


def profiles_to_dataframe(profiles: dict[str, dict]) -> pd.DataFrame:
    """
    Chuyển dict profiles sang DataFrame tóm tắt.

    Returns:
        DataFrame: occupation, jd_count, skill_count, top_5_skills.
    """
    rows = []
    for occ_key, p in profiles.items():
        rows.append({
            "occupation_key":        occ_key,
            "occupation":            p["occupation"],
            "jd_count":              p["jd_count"],
            "unique_skills":         len(p["skills"]),
            "responsibility_count":  len(p["responsibilities"]),
            "top_5_skills":          ", ".join(p["skills"][:5]),
        })
    df = (
        pd.DataFrame(rows)
        .sort_values("jd_count", ascending=False)
        .reset_index(drop=True)
    )
    return df


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    )

    from src.offline.preprocessing_step1.data_loader import load_jd_dataset
    from src.offline.preprocessing_step1.text_cleaner import clean_jd_dataframe
    from src.offline.skill_extraction_step2.extractor import extract_all

    df_raw  = load_jd_dataset()
    df_clean = clean_jd_dataframe(df_raw)
    records = extract_all(df_clean)
    profiles = build_occupation_profiles(records)

    df_summary = profiles_to_dataframe(profiles)
    print("\n=== Occupation Profiles Summary ===")
    print(df_summary.to_string(index=False))

    # Chi tiết IT
    it_key = next((k for k in profiles if "công_nghệ" in k), None)
    if it_key:
        p = profiles[it_key]
        print(f"\n=== Chi tiết: {p['occupation']} ===")
        print(f"  jd_count   : {p['jd_count']}")
        print(f"  skills ({len(p['skills'])}): {p['skills'][:15]}")
        print(f"  top skill_counts: {dict(list(p['skill_counts'].items())[:10])}")
        print(f"  responsibilities ({len(p['responsibilities'])}):")
        for r in p['responsibilities'][:5]:
            print(f"    • {r[:100]}")
