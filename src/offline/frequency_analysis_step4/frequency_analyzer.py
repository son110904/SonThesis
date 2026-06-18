"""
frequency_analyzer.py – Tính tần suất xuất hiện của mỗi skill trong từng occupation.

Định nghĩa:
    frequency_score(skill, occupation) = count(skill trong occupation) / jd_count(occupation)

    Tỷ lệ này cho biết skill xuất hiện trong bao nhiêu phần trăm JD của nghề đó.
    Ví dụ: Python xuất hiện trong 199/1906 JD IT → frequency_score = 0.104

Output:
    {
        "công_nghệ_thông_tin_kỹ_thuật_số": {
            "Python": {"count": 199, "frequency": 0.104},
            "SQL":    {"count": 238, "frequency": 0.125},
            ...
        },
        ...
    }
"""

import logging
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

logger = logging.getLogger(__name__)


def compute_frequency(profiles: dict[str, dict]) -> dict[str, dict[str, dict]]:
    """
    Tính frequency_score cho từng skill trong từng occupation.

    frequency_score = skill_count / jd_count

    Args:
        profiles: Output của occupation_profile_builder.build_occupation_profiles().
                  Mỗi entry có keys: occupation, skills, skill_counts, jd_count.

    Returns:
        Dict[occupation_key → Dict[skill → {"count": int, "frequency": float}]]
    """
    logger.info(f"Đang tính frequency score cho {len(profiles)} occupation...")

    result: dict[str, dict[str, dict]] = {}

    for occ_key, profile in profiles.items():
        jd_count = profile["jd_count"]
        if jd_count == 0:
            logger.warning(f"  Bỏ qua '{occ_key}': jd_count = 0")
            continue

        skill_freq: dict[str, dict] = {}
        for skill, count in profile["skill_counts"].items():
            skill_freq[skill] = {
                "count": count,
                "frequency": round(count / jd_count, 6),
            }

        result[occ_key] = skill_freq

    total_skills = sum(len(v) for v in result.values())
    logger.info(
        f"Hoàn tất frequency analysis: "
        f"{len(result)} occupation, {total_skills} skill entries"
    )
    return result


def get_top_skills_by_frequency(
    freq_result: dict[str, dict[str, dict]],
    occupation_key: str,
    top_n: int = 20,
) -> list[tuple[str, float]]:
    """
    Lấy top-N skills theo frequency_score của một occupation.

    Args:
        freq_result: Output của compute_frequency().
        occupation_key: Key của occupation cần tra cứu.
        top_n: Số lượng skills trả về.

    Returns:
        List[(skill, frequency_score)] sắp xếp giảm dần.
    """
    if occupation_key not in freq_result:
        logger.warning(f"Không tìm thấy occupation: {occupation_key}")
        return []

    skills = freq_result[occupation_key]
    sorted_skills = sorted(skills.items(), key=lambda x: x[1]["frequency"], reverse=True)
    return [(skill, data["frequency"]) for skill, data in sorted_skills[:top_n]]


def summarize_frequency(freq_result: dict[str, dict[str, dict]]) -> dict[str, dict]:
    """
    Tóm tắt thống kê frequency cho mỗi occupation.

    Returns:
        Dict[occupation_key → {max_freq, min_freq, mean_freq, skill_count}]
    """
    summary: dict[str, dict] = {}
    for occ_key, skill_data in freq_result.items():
        freqs = [d["frequency"] for d in skill_data.values()]
        if not freqs:
            continue
        summary[occ_key] = {
            "skill_count": len(freqs),
            "max_frequency": round(max(freqs), 4),
            "min_frequency": round(min(freqs), 4),
            "mean_frequency": round(sum(freqs) / len(freqs), 4),
        }
    return summary


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    )

    from src.offline.preprocessing_step1.data_loader import load_jd_dataset
    from src.offline.preprocessing_step1.text_cleaner import clean_jd_dataframe
    from src.offline.skill_extraction_step2.extractor import extract_all
    from src.offline.profile_builder_step3.occupation_profile_builder import build_occupation_profiles

    df = clean_jd_dataframe(load_jd_dataset())
    records = extract_all(df)
    profiles = build_occupation_profiles(records)

    freq_result = compute_frequency(profiles)

    print("\n=== Top 15 skills theo frequency: IT ===")
    it_key = "công_nghệ_thông_tin_kỹ_thuật_số"
    for skill, freq in get_top_skills_by_frequency(freq_result, it_key, 15):
        bar = "█" * int(freq * 100)
        print(f"  {skill:<35} {freq:.3f}  {bar}")

    print("\n=== Top 10 skills theo frequency: Marketing ===")
    mkt_key = "marketing_truyền_thông_quảng_cáo_nội_dung"
    for skill, freq in get_top_skills_by_frequency(freq_result, mkt_key, 10):
        bar = "█" * int(freq * 100)
        print(f"  {skill:<35} {freq:.3f}  {bar}")

    print("\n=== Thống kê frequency theo occupation ===")
    summary = summarize_frequency(freq_result)
    for occ_key, stats in sorted(summary.items(), key=lambda x: -x[1]["max_frequency"]):
        print(
            f"  {occ_key:<55} "
            f"skills={stats['skill_count']:>4}  "
            f"max={stats['max_frequency']:.3f}  "
            f"mean={stats['mean_frequency']:.3f}"
        )
