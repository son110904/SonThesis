"""
skill_weight_calculator.py – Tính trọng số kỹ năng và phân loại core/optional.

Công thức:
    weight = α × freq_normalized + β × tfidf_score

    Trong đó:
        freq_normalized: MinMaxScaler(frequency_score) về [0,1] per-occupation
        tfidf_score:     đã normalized [0,1] từ Bước 5
        α = 0.6, β = 0.4 (cấu hình trong config.py)

    KHÔNG normalize lần 2 — weight ở đây đã nằm trong [0,1] tự nhiên
    vì cả hai input đều là [0,1]. Double normalization sẽ ép mọi occupation
    có đúng 1 skill = 1.0 và phần lớn skills dồn về 0, làm mất thông tin.

Phân loại:
    weight >= CORE_SKILL_THRESHOLD (0.35) → core_skills
    weight <  CORE_SKILL_THRESHOLD        → optional_skills

Output mỗi occupation:
    {
        "Python":     {"weight": 0.621, "tier": "core"},
        "Docker":     {"weight": 0.467, "tier": "optional"},
        "Redis":      {"weight": 0.089, "tier": "optional"},
        ...
    }
"""

import logging
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.config import ALPHA, BETA, CORE_SKILL_THRESHOLD

logger = logging.getLogger(__name__)

# Override threshold về 0.35 (hợp lý hơn 0.5 khi không double-normalize)
_DEFAULT_THRESHOLD = 0.35


def _minmax_normalize(values: dict[str, float]) -> dict[str, float]:
    """MinMaxScaler về [0,1] cho một dict skill→score."""
    if not values:
        return {}
    v_list = list(values.values())
    v_min, v_max = min(v_list), max(v_list)
    span = v_max - v_min
    if span == 0:
        return {k: 0.5 for k in values}
    return {k: round((v - v_min) / span, 6) for k, v in values.items()}


def compute_skill_weights(
    freq_result: dict[str, dict[str, dict]],
    tfidf_result: dict[str, dict[str, float]],
    alpha: float = ALPHA,
    beta: float = BETA,
    threshold: float = _DEFAULT_THRESHOLD,
) -> dict[str, dict[str, dict]]:
    """
    Tính trọng số kỹ năng cho tất cả occupation.

    Bước:
      1. Normalize freq_score per-occupation về [0,1] bằng MinMaxScaler.
      2. Kết hợp: weight = α×freq_norm + β×tfidf  (kết quả ∈ [0,1]).
      3. Phân loại core / optional theo threshold.

    Args:
        freq_result:  Output compute_frequency()
        tfidf_result: Output compute_tfidf()
        alpha:        Trọng số frequency (default 0.6)
        beta:         Trọng số TF-IDF   (default 0.4)
        threshold:    Ngưỡng phân loại core skill (default 0.35)

    Returns:
        Dict[occ_key → Dict[skill → {"weight": float, "tier": str}]]
    """
    logger.info(
        f"Đang tính skill weight (α={alpha}, β={beta}, threshold={threshold}) "
        f"cho {len(freq_result)} occupation..."
    )

    result: dict[str, dict[str, dict]] = {}

    for occ_key, skill_freq_data in freq_result.items():
        # Bước 1: normalize freq per-occupation
        raw_freqs = {skill: d["frequency"] for skill, d in skill_freq_data.items()}
        freq_norm = _minmax_normalize(raw_freqs)

        # Bước 2: lấy TF-IDF (đã [0,1])
        occ_tfidf = tfidf_result.get(occ_key, {})

        # Bước 3: tính weight trên union skills
        all_skills = set(freq_norm.keys()) | set(occ_tfidf.keys())
        occ_result: dict[str, dict] = {}

        for skill in all_skills:
            f = freq_norm.get(skill, 0.0)
            t = occ_tfidf.get(skill, 0.0)
            weight = round(alpha * f + beta * t, 4)
            occ_result[skill] = {
                "weight": weight,
                "tier": "core" if weight >= threshold else "optional",
            }

        result[occ_key] = occ_result

    n_core = sum(1 for occ in result.values() for d in occ.values() if d["tier"] == "core")
    n_total = sum(len(occ) for occ in result.values())
    logger.info(
        f"Hoàn tất: {n_total} skill entries, "
        f"{n_core} core ({n_core/max(n_total,1)*100:.1f}%), "
        f"{n_total-n_core} optional"
    )
    return result


def split_core_optional(
    weight_result: dict[str, dict[str, dict]],
    occupation_key: str,
) -> tuple[dict[str, float], dict[str, float]]:
    """
    Tách core_skills và optional_skills của một occupation.

    Returns:
        (core_skills, optional_skills) mỗi là Dict[skill → weight],
        sắp xếp theo weight giảm dần.
    """
    if occupation_key not in weight_result:
        return {}, {}

    core: dict[str, float] = {}
    optional: dict[str, float] = {}

    for skill, data in weight_result[occupation_key].items():
        if data["tier"] == "core":
            core[skill] = data["weight"]
        else:
            optional[skill] = data["weight"]

    return (
        dict(sorted(core.items(),     key=lambda x: x[1], reverse=True)),
        dict(sorted(optional.items(), key=lambda x: x[1], reverse=True)),
    )


def weight_result_to_profile_format(
    weight_result: dict[str, dict[str, dict]],
    profiles: dict[str, dict],
) -> dict[str, dict]:
    """
    Gộp weight vào profile gốc, trả về format chuẩn cho Knowledge Base (Bước 9).

    Returns:
        Dict[occ_key → {occupation, core_skills, optional_skills,
                         responsibilities, jd_count}]
    """
    enriched: dict[str, dict] = {}
    for occ_key, profile in profiles.items():
        core, optional = split_core_optional(weight_result, occ_key)
        enriched[occ_key] = {
            "occupation":      profile["occupation"],
            "core_skills":     core,
            "optional_skills": optional,
            "responsibilities": profile["responsibilities"],
            "jd_count":        profile["jd_count"],
        }
    return enriched


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
    from src.offline.frequency_analysis_step4.frequency_analyzer import compute_frequency
    from src.offline.tfidf_analysis_step5.tfidf_analyzer import compute_tfidf

    df = clean_jd_dataframe(load_jd_dataset())
    records = extract_all(df)
    profiles = build_occupation_profiles(records)
    freq_result = compute_frequency(profiles)
    tfidf_result = compute_tfidf(profiles, freq_result)
    weight_result = compute_skill_weights(freq_result, tfidf_result)

    for occ_key in [
        "công_nghệ_thông_tin_kỹ_thuật_số",
        "marketing_truyền_thông_quảng_cáo_nội_dung",
        "tài_chính_kế_toán_ngân_hàng_bảo_hiểm",
    ]:
        core, optional = split_core_optional(weight_result, occ_key)
        print(f"\n=== {occ_key} ===")
        print(f"  Core ({len(core)}):")
        for skill, w in list(core.items())[:12]:
            bar = "█" * int(w * 20)
            print(f"    {skill:<35} {w:.4f}  {bar}")
        print(f"  Optional top 5 ({len(optional)} total):")
        for skill, w in list(optional.items())[:5]:
            print(f"    {skill:<35} {w:.4f}")

    # Kiểm tra format Knowledge Base
    enriched = weight_result_to_profile_format(weight_result, profiles)
    it = enriched["công_nghệ_thông_tin_kỹ_thuật_số"]
    print(f"\n=== Enriched profile IT ===")
    print(f"  keys: {list(it.keys())}")
    print(f"  core_skills  (top 5): {dict(list(it['core_skills'].items())[:5])}")
    print(f"  optional top 3: {dict(list(it['optional_skills'].items())[:3])}")
