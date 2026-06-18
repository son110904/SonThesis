"""
knowledge_base_builder.py – Xây dựng và lưu Occupation Knowledge Base.

Gộp toàn bộ output từ Bước 1-7 thành các file JSON theo định dạng chuẩn:

    {
        "occupation":      "công_nghệ_thông_tin_kỹ_thuật_số",
        "core_skills":     {"Python": 0.621, "SQL": 0.753, ...},
        "optional_skills": {"Redis": 0.089, "Kafka": 0.071, ...},
        "responsibilities": ["Phát triển API backend...", ...],
        "embedding":       [0.011, -0.038, ...]   ← vector 768 chiều
    }

Lưu tại:
    data/occupation_profiles/<occupation_key>.json

Có thể chạy toàn bộ offline pipeline từ đầu, hoặc nhận input
đã tính sẵn từ các bước trước để tránh tính lại.

Bước 9 có 2 chế độ:
  - build_from_scratch(): Chạy toàn bộ pipeline 1→7, lưu JSON.
  - build_from_inputs():  Nhận enriched_profiles + occ_embeddings đã có, chỉ lưu JSON.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.config import OCCUPATION_PROFILES_DIR, FINE_TUNED_MODEL_DIR

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _occupation_to_filename(occupation_key: str) -> str:
    """
    Chuyển occupation key thành tên file an toàn.

    Ví dụ:
        'công_nghệ_thông_tin_kỹ_thuật_số' → 'cong_nghe_thong_tin_ky_thuat_so.json'
    """
    import unicodedata

    # Normalize unicode → tách dấu
    nfkd = unicodedata.normalize("NFKD", occupation_key)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))

    # Lowercase, thay ký tự không phải alnum/underscore bằng _
    safe = re.sub(r"[^\w]", "_", ascii_str.lower())
    safe = re.sub(r"_+", "_", safe).strip("_")
    return f"{safe}.json"


def _build_knowledge_entry(
    occ_key: str,
    enriched_profile: dict,
    embedding: list[float],
) -> dict:
    """
    Tạo một entry Knowledge Base đúng định dạng spec.

    Args:
        occ_key:          Key của occupation (snake_case).
        enriched_profile: Output từ weight_result_to_profile_format().
        embedding:        Vector embedding list[float] từ embedder.

    Returns:
        Dict theo định dạng Knowledge Base spec.
    """
    return {
        "occupation":      enriched_profile["occupation"],
        "core_skills":     enriched_profile["core_skills"],
        "optional_skills": enriched_profile["optional_skills"],
        "responsibilities": enriched_profile["responsibilities"],
        "embedding":       embedding,
        # Metadata bổ sung
        "_meta": {
            "occupation_key": occ_key,
            "jd_count":       enriched_profile.get("jd_count", 0),
            "core_skill_count":     len(enriched_profile["core_skills"]),
            "optional_skill_count": len(enriched_profile["optional_skills"]),
            "embedding_dim":  len(embedding),
            "model_source":   (
                "fine-tuned" if FINE_TUNED_MODEL_DIR.exists() else "pretrained"
            ),
            "built_at": datetime.now().isoformat(timespec="seconds"),
        },
    }


# ── Core build functions ──────────────────────────────────────────────────────

def build_from_inputs(
    enriched_profiles: dict[str, dict],
    occ_embeddings: dict[str, list[float]],
    output_dir: Path = OCCUPATION_PROFILES_DIR,
    overwrite: bool = True,
) -> dict[str, Path]:
    """
    Lưu Knowledge Base từ enriched_profiles + embeddings đã có.

    Dùng khi đã chạy pipeline Bước 1-7 và muốn chỉ lưu kết quả.

    Args:
        enriched_profiles: Output weight_result_to_profile_format().
        occ_embeddings:    Output embed_occupation_profiles().
        output_dir:        Thư mục lưu JSON files.
        overwrite:         Ghi đè nếu file đã tồn tại.

    Returns:
        Dict[occupation_key → Path file đã lưu].
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved: dict[str, Path] = {}
    skipped = 0

    for occ_key, profile in enriched_profiles.items():
        if occ_key not in occ_embeddings:
            logger.warning(f"Không có embedding cho '{occ_key}', bỏ qua.")
            continue

        embedding = occ_embeddings[occ_key]
        entry = _build_knowledge_entry(occ_key, profile, embedding)

        filename = _occupation_to_filename(occ_key)
        filepath = output_dir / filename

        if filepath.exists() and not overwrite:
            logger.debug(f"Bỏ qua (đã tồn tại): {filename}")
            skipped += 1
            saved[occ_key] = filepath
            continue

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)

        saved[occ_key] = filepath
        logger.debug(f"Đã lưu: {filename}")

    logger.info(
        f"Knowledge Base: {len(saved)} files lưu tại {output_dir} "
        f"({skipped} giữ nguyên)"
    )
    return saved


def build_from_scratch(
    output_dir: Path = OCCUPATION_PROFILES_DIR,
    use_finetuned: bool = True,
    overwrite: bool = True,
) -> dict[str, Path]:
    """
    Chạy toàn bộ offline pipeline Bước 1-7 rồi lưu Knowledge Base.

    Args:
        output_dir:    Thư mục lưu JSON.
        use_finetuned: Dùng fine-tuned model cho embedding (yêu cầu Bước 8 đã xong).
        overwrite:     Ghi đè file đã tồn tại.

    Returns:
        Dict[occupation_key → Path file đã lưu].
    """
    logger.info("=== Bước 9: Build Occupation Knowledge Base (from scratch) ===")

    # Bước 1: Load + clean
    from src.offline.preprocessing_step1.data_loader import load_jd_dataset
    from src.offline.preprocessing_step1.text_cleaner import clean_jd_dataframe
    df_clean = clean_jd_dataframe(load_jd_dataset())

    # Bước 2: Extract
    from src.offline.skill_extraction_step2.extractor import extract_all
    records = extract_all(df_clean)

    # Bước 3: Build profiles
    from src.offline.profile_builder_step3.occupation_profile_builder import build_occupation_profiles
    profiles = build_occupation_profiles(records)

    # Bước 4: Frequency
    from src.offline.frequency_analysis_step4.frequency_analyzer import compute_frequency
    freq_result = compute_frequency(profiles)

    # Bước 5: TF-IDF
    from src.offline.tfidf_analysis_step5.tfidf_analyzer import compute_tfidf
    tfidf_result = compute_tfidf(profiles, freq_result)

    # Bước 6: Skill weight
    from src.offline.skill_weight_step6.skill_weight_calculator import (
        compute_skill_weights, weight_result_to_profile_format
    )
    weight_result = compute_skill_weights(freq_result, tfidf_result)
    enriched = weight_result_to_profile_format(weight_result, profiles)

    # Bước 7: Embed
    from src.offline.embedding_step7.embedder import load_model, embed_occupation_profiles
    model = load_model(use_finetuned=use_finetuned)
    occ_embeddings = embed_occupation_profiles(enriched, model=model)

    # Bước 9: Lưu
    return build_from_inputs(enriched, occ_embeddings, output_dir, overwrite)


# ── Load helpers ──────────────────────────────────────────────────────────────

def load_knowledge_base(
    output_dir: Path = OCCUPATION_PROFILES_DIR,
) -> dict[str, dict]:
    """
    Load toàn bộ Knowledge Base từ thư mục JSON.

    Returns:
        Dict[occupation_key → knowledge_entry]
    """
    output_dir = Path(output_dir)
    if not output_dir.exists():
        raise FileNotFoundError(
            f"Knowledge Base chưa được tạo tại: {output_dir}\n"
            f"Hãy chạy knowledge_base_builder.py trước."
        )

    kb: dict[str, dict] = {}
    json_files = sorted(output_dir.glob("*.json"))

    if not json_files:
        raise FileNotFoundError(f"Không tìm thấy file JSON nào trong: {output_dir}")

    for filepath in json_files:
        with open(filepath, "r", encoding="utf-8") as f:
            entry = json.load(f)
        occ_key = entry.get("_meta", {}).get("occupation_key", filepath.stem)
        kb[occ_key] = entry

    logger.info(f"Loaded {len(kb)} occupation profiles từ {output_dir}")
    return kb


def get_all_embeddings(kb: dict[str, dict]) -> dict[str, list[float]]:
    """
    Trích xuất tất cả embedding vectors từ Knowledge Base đã load.

    Returns:
        Dict[occupation_key → embedding vector]
    """
    return {
        occ_key: entry["embedding"]
        for occ_key, entry in kb.items()
        if "embedding" in entry
    }


def summarize_knowledge_base(kb: dict[str, dict]) -> None:
    """In tóm tắt Knowledge Base."""
    print(f"\n{'='*65}")
    print(f"OCCUPATION KNOWLEDGE BASE — {len(kb)} occupations")
    print(f"{'='*65}")
    print(f"  {'Occupation':<50} {'Core':>5}  {'Opt':>5}  {'JDs':>6}")
    print(f"  {'-'*50} {'-'*5}  {'-'*5}  {'-'*6}")
    for occ_key, entry in sorted(kb.items()):
        meta = entry.get("_meta", {})
        print(
            f"  {entry['occupation']:<50} "
            f"{meta.get('core_skill_count', len(entry['core_skills'])):>5}  "
            f"{meta.get('optional_skill_count', len(entry['optional_skills'])):>5}  "
            f"{meta.get('jd_count', 0):>6}"
        )
    print(f"{'='*65}")


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    )

    import argparse
    parser = argparse.ArgumentParser(description="Build Occupation Knowledge Base")
    parser.add_argument(
        "--use-finetuned", action="store_true", default=True,
        help="Dùng fine-tuned model (default: True, yêu cầu Bước 8 đã xong)"
    )
    parser.add_argument(
        "--use-pretrained", dest="use_finetuned", action="store_false",
        help="Dùng pretrained model (bỏ qua Bước 8)"
    )
    parser.add_argument(
        "--output-dir", type=str, default=str(OCCUPATION_PROFILES_DIR),
        help=f"Thư mục lưu JSON (default: {OCCUPATION_PROFILES_DIR})"
    )
    parser.add_argument(
        "--no-overwrite", action="store_false", dest="overwrite",
        help="Không ghi đè file đã tồn tại"
    )
    args = parser.parse_args()

    saved = build_from_scratch(
        output_dir=Path(args.output_dir),
        use_finetuned=args.use_finetuned,
        overwrite=args.overwrite,
    )

    # Load lại và hiển thị tóm tắt
    kb = load_knowledge_base(Path(args.output_dir))
    summarize_knowledge_base(kb)

    print(f"\n✅ Knowledge Base hoàn chỉnh: {len(saved)} files")
    for occ_key, path in sorted(saved.items()):
        print(f"   {path.name}")
