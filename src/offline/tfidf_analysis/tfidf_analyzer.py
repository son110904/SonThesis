"""
tfidf_analyzer.py – Tính TF-IDF score của từng skill giữa các occupation.

Mục tiêu:
    Xác định mức độ ĐẶC TRƯNG của một skill đối với một nghề cụ thể.
    Skill xuất hiện nhiều ở MỌI nghề (vd: Photoshop) → TF-IDF thấp.
    Skill xuất hiện nhiều ở IT nhưng ít ở ngành khác (vd: Docker) → TF-IDF cao.

Định nghĩa (occupation-as-document model):
    Mỗi occupation là một "document".
    "Corpus" gồm 16 occupation documents.

    TF(skill, occupation)  = frequency_score(skill, occupation)
                           = count(skill, occ) / jd_count(occ)

    IDF(skill)             = log(1 + N / (1 + df(skill)))
        N   = tổng số occupation
        df  = số occupation có chứa skill đó (document frequency)
        +1  smoothing để tránh log(0)

    TF-IDF(skill, occ) = TF(skill, occ) × IDF(skill)

Sau đó normalize TF-IDF về [0, 1] trong phạm vi từng occupation
bằng MinMaxScaler để đồng nhất với frequency_score trước khi tính weight.

Output:
    {
        "công_nghệ_thông_tin_kỹ_thuật_số": {
            "Python": 0.823,
            "Docker": 0.751,
            "Photoshop": 0.112,   ← thấp vì xuất hiện ở nhiều ngành
            ...
        },
        ...
    }
"""

import logging
import math
from collections import defaultdict
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

logger = logging.getLogger(__name__)


def _compute_document_frequency(profiles: dict[str, dict]) -> dict[str, int]:
    """
    Tính df(skill): số occupation có chứa skill đó.

    Args:
        profiles: Output của build_occupation_profiles().

    Returns:
        Dict[skill_lower → document_frequency]
    """
    df: dict[str, int] = defaultdict(int)
    for profile in profiles.values():
        # Mỗi occupation chỉ đếm 1 lần dù skill xuất hiện nhiều
        skills_in_occ = set(s.lower() for s in profile["skill_counts"].keys())
        for skill_lower in skills_in_occ:
            df[skill_lower] += 1
    return dict(df)


def _build_skill_lower_map(profiles: dict[str, dict]) -> dict[str, str]:
    """
    Xây dựng map từ skill_lower → canonical form (form xuất hiện nhiều nhất).

    Dùng để đồng bộ key khi tính IDF xuyên occupation.
    """
    canonical: dict[str, str] = {}
    for profile in profiles.values():
        for skill in profile["skill_counts"].keys():
            lower = skill.lower()
            if lower not in canonical:
                canonical[lower] = skill
    return canonical


def compute_tfidf(
    profiles: dict[str, dict],
    freq_result: dict[str, dict[str, dict]],
) -> dict[str, dict[str, float]]:
    """
    Tính TF-IDF score cho từng skill trong từng occupation.

    TF  = frequency_score (từ freq_result)
    IDF = log(1 + N / (1 + df(skill)))
    Normalize per-occupation bằng min-max về [0, 1]

    Args:
        profiles: Output của build_occupation_profiles().
        freq_result: Output của compute_frequency().

    Returns:
        Dict[occupation_key → Dict[skill → tfidf_score_normalized ∈ [0,1]]]
    """
    logger.info(f"Đang tính TF-IDF cho {len(profiles)} occupation...")

    N = len(profiles)  # tổng số occupation (documents)

    # Bước 1: Tính document frequency cho mỗi skill
    df_map = _compute_document_frequency(profiles)

    # Bước 2: Tính raw TF-IDF per skill per occupation
    raw_tfidf: dict[str, dict[str, float]] = {}

    for occ_key, skill_freq_data in freq_result.items():
        occ_tfidf: dict[str, float] = {}

        for skill, data in skill_freq_data.items():
            tf = data["frequency"]
            skill_lower = skill.lower()
            df = df_map.get(skill_lower, 1)

            # IDF với smoothing +1
            idf = math.log(1 + N / (1 + df))

            occ_tfidf[skill] = tf * idf

        raw_tfidf[occ_key] = occ_tfidf

    # Bước 3: Normalize per-occupation về [0, 1] bằng MinMaxScaler
    normalized_tfidf: dict[str, dict[str, float]] = {}

    for occ_key, occ_tfidf in raw_tfidf.items():
        if not occ_tfidf:
            normalized_tfidf[occ_key] = {}
            continue

        values = list(occ_tfidf.values())
        min_val = min(values)
        max_val = max(values)
        value_range = max_val - min_val

        if value_range == 0:
            # Tất cả skills có cùng TF-IDF → gán đều 0.5
            normalized_tfidf[occ_key] = {s: 0.5 for s in occ_tfidf}
        else:
            normalized_tfidf[occ_key] = {
                skill: round((score - min_val) / value_range, 6)
                for skill, score in occ_tfidf.items()
            }

    total_entries = sum(len(v) for v in normalized_tfidf.values())
    logger.info(
        f"Hoàn tất TF-IDF: {len(normalized_tfidf)} occupation, "
        f"{total_entries} skill entries"
    )
    return normalized_tfidf


def get_top_skills_by_tfidf(
    tfidf_result: dict[str, dict[str, float]],
    occupation_key: str,
    top_n: int = 20,
) -> list[tuple[str, float]]:
    """
    Lấy top-N skills theo TF-IDF score của một occupation.

    Args:
        tfidf_result: Output của compute_tfidf().
        occupation_key: Key của occupation.
        top_n: Số skills trả về.

    Returns:
        List[(skill, tfidf_score)] sắp xếp giảm dần.
    """
    if occupation_key not in tfidf_result:
        logger.warning(f"Không tìm thấy occupation: {occupation_key}")
        return []

    skills = tfidf_result[occupation_key]
    sorted_skills = sorted(skills.items(), key=lambda x: x[1], reverse=True)
    return sorted_skills[:top_n]


def compare_skill_across_occupations(
    tfidf_result: dict[str, dict[str, float]],
    skill_name: str,
) -> list[tuple[str, float]]:
    """
    So sánh TF-IDF score của một skill xuyên các occupation.

    Dùng để kiểm tra mức độ đặc trưng của skill:
    - Score cao ở IT, thấp ở các ngành khác → đặc trưng
    - Score đều ở mọi ngành → không đặc trưng

    Args:
        tfidf_result: Output của compute_tfidf().
        skill_name: Tên skill cần so sánh (case-insensitive).

    Returns:
        List[(occupation_key, tfidf_score)] sắp xếp giảm dần.
    """
    skill_lower = skill_name.lower()
    results: list[tuple[str, float]] = []

    for occ_key, skill_data in tfidf_result.items():
        for skill, score in skill_data.items():
            if skill.lower() == skill_lower:
                results.append((occ_key, score))
                break

    return sorted(results, key=lambda x: x[1], reverse=True)


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    )

    from src.offline.preprocessing.data_loader import load_jd_dataset
    from src.offline.preprocessing.text_cleaner import clean_jd_dataframe
    from src.offline.skill_extraction.extractor import extract_all
    from src.offline.profile_builder.occupation_profile_builder import build_occupation_profiles
    from src.offline.frequency_analysis.frequency_analyzer import compute_frequency

    df = clean_jd_dataframe(load_jd_dataset())
    records = extract_all(df)
    profiles = build_occupation_profiles(records)
    freq_result = compute_frequency(profiles)

    tfidf_result = compute_tfidf(profiles, freq_result)

    it_key = "công_nghệ_thông_tin_kỹ_thuật_số"

    print("\n=== Top 15 skills theo TF-IDF: IT ===")
    for skill, score in get_top_skills_by_tfidf(tfidf_result, it_key, 15):
        bar = "█" * int(score * 30)
        print(f"  {skill:<35} {score:.4f}  {bar}")

    print("\n=== So sánh: Frequency vs TF-IDF (IT) ===")
    from src.offline.frequency_analysis.frequency_analyzer import get_top_skills_by_frequency
    freq_top = dict(get_top_skills_by_frequency(freq_result, it_key, 20))
    tfidf_top = dict(get_top_skills_by_tfidf(tfidf_result, it_key, 20))
    all_skills = sorted(set(list(freq_top.keys()) + list(tfidf_top.keys())))
    print(f"  {'Skill':<35} {'Freq':>7}  {'TF-IDF':>7}")
    print(f"  {'-'*35} {'-'*7}  {'-'*7}")
    for skill in all_skills:
        f = freq_top.get(skill, 0)
        t = tfidf_top.get(skill, 0)
        print(f"  {skill:<35} {f:>7.3f}  {t:>7.4f}")

    # Kiểm tra skills đặc trưng vs phổ thông
    print("\n=== Kiểm tra độ đặc trưng xuyên ngành ===")
    for check_skill in ["Python", "Photoshop", "SQL", "AutoCAD", "SEO"]:
        across = compare_skill_across_occupations(tfidf_result, check_skill)
        if across:
            top_occ, top_score = across[0]
            bottom_occ, bottom_score = across[-1]
            spread = top_score - bottom_score
            print(
                f"  {check_skill:<15} "
                f"max={top_score:.3f} ({top_occ[:25]:<25})  "
                f"min={bottom_score:.3f}  spread={spread:.3f}"
            )
