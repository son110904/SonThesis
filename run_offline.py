"""
run_offline.py – Chạy toàn bộ Offline Pipeline từ Bước 1 đến Bước 9.

Thứ tự thực thi:
    Bước 1: Load data + Text cleaning
    Bước 2: Skill extraction
    Bước 3: Occupation profile building
    Bước 4: Frequency analysis
    Bước 5: TF-IDF analysis
    Bước 6: Skill weight calculation
    Bước 8: Fine-tune Semantic Matching Model  ← phải trước Bước 7
    Bước 7: Embedding occupation profiles      ← dùng fine-tuned model
    Bước 9: Build & save Knowledge Base

Cách chạy:
    python run_offline.py

Options:
    --skip-training     Bỏ qua Bước 8 nếu đã có fine-tuned model
    --use-pretrained    Dùng pretrained model (không cần Bước 8)
    --epochs N          Số epoch training (default: 3)
    --batch-size N      Batch size training (default: 16)
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Thêm root vào sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("offline_pipeline.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def run(skip_training: bool = False, use_pretrained: bool = False,
        epochs: int = 3, batch_size: int = 16) -> None:

    total_start = datetime.now()
    logger.info("=" * 65)
    logger.info("OFFLINE PIPELINE – BẮT ĐẦU")
    logger.info("=" * 65)

    # ── Bước 1: Load + Clean ──────────────────────────────────────────────────
    logger.info("\n[BƯỚC 1] Data Loading & Text Cleaning")
    from src.offline.preprocessing.data_loader import load_jd_dataset
    from src.offline.preprocessing.text_cleaner import clean_jd_dataframe

    df_jd_clean = clean_jd_dataframe(load_jd_dataset())
    logger.info(f"  ✓ JD dataset: {df_jd_clean.shape[0]} hàng")

    # ── Bước 2: Skill Extraction ──────────────────────────────────────────────
    logger.info("\n[BƯỚC 2] Skill Extraction")
    from src.offline.skill_extraction.extractor import extract_all

    records = extract_all(df_jd_clean)
    avg_skills = sum(len(r["skills"]) for r in records) / len(records)
    logger.info(f"  ✓ {len(records)} JD xử lý, avg {avg_skills:.1f} skills/JD")

    # ── Bước 3: Occupation Profile Builder ───────────────────────────────────
    logger.info("\n[BƯỚC 3] Occupation Profile Building")
    from src.offline.profile_builder.occupation_profile_builder import build_occupation_profiles

    profiles = build_occupation_profiles(records)
    logger.info(f"  ✓ {len(profiles)} occupation profiles")

    # ── Bước 4: Frequency Analysis ────────────────────────────────────────────
    logger.info("\n[BƯỚC 4] Frequency Analysis")
    from src.offline.frequency_analysis.frequency_analyzer import compute_frequency

    freq_result = compute_frequency(profiles)
    logger.info(f"  ✓ {sum(len(v) for v in freq_result.values())} skill entries")

    # ── Bước 5: TF-IDF Analysis ───────────────────────────────────────────────
    logger.info("\n[BƯỚC 5] TF-IDF Analysis")
    from src.offline.tfidf_analysis.tfidf_analyzer import compute_tfidf

    tfidf_result = compute_tfidf(profiles, freq_result)
    logger.info(f"  ✓ TF-IDF computed cho {len(tfidf_result)} occupation")

    # ── Bước 6: Skill Weight ──────────────────────────────────────────────────
    logger.info("\n[BƯỚC 6] Skill Weight Calculation")
    from src.offline.skill_weight.skill_weight_calculator import (
        compute_skill_weights, weight_result_to_profile_format
    )

    weight_result = compute_skill_weights(freq_result, tfidf_result)
    enriched = weight_result_to_profile_format(weight_result, profiles)
    n_core = sum(len(p["core_skills"]) for p in enriched.values())
    n_opt  = sum(len(p["optional_skills"]) for p in enriched.values())
    logger.info(f"  ✓ {n_core} core skills, {n_opt} optional skills")

    # ── Bước 8: Training ──────────────────────────────────────────────────────
    from src.config import FINE_TUNED_MODEL_DIR

    use_finetuned = not use_pretrained

    if use_pretrained:
        logger.info("\n[BƯỚC 8] Bỏ qua – dùng pretrained model")

    elif skip_training and FINE_TUNED_MODEL_DIR.exists():
        logger.info(f"\n[BƯỚC 8] Bỏ qua – đã có fine-tuned model tại {FINE_TUNED_MODEL_DIR}")

    else:
        if skip_training and not FINE_TUNED_MODEL_DIR.exists():
            logger.warning(
                f"  --skip-training được chỉ định nhưng không tìm thấy model tại "
                f"{FINE_TUNED_MODEL_DIR}. Tiến hành training..."
            )
        logger.info("\n[BƯỚC 8] Fine-tuning Semantic Matching Model")
        from src.training.trainer import train as run_training

        run_training(
            epochs=epochs,
            train_batch_size=batch_size,
        )
        logger.info(f"  ✓ Fine-tuned model lưu tại: {FINE_TUNED_MODEL_DIR}")

    # ── Bước 7: Embedding ─────────────────────────────────────────────────────
    logger.info("\n[BƯỚC 7] Embedding Occupation Profiles")
    from src.offline.embedding.embedder import load_model, embed_occupation_profiles

    model = load_model(use_finetuned=use_finetuned)
    occ_embeddings = embed_occupation_profiles(enriched, model=model)
    dim = len(next(iter(occ_embeddings.values())))
    logger.info(f"  ✓ {len(occ_embeddings)} occupation embedded, dim={dim}")

    # ── Bước 9: Knowledge Base ────────────────────────────────────────────────
    logger.info("\n[BƯỚC 9] Building Occupation Knowledge Base")
    from src.offline.knowledge_base.knowledge_base_builder import (
        build_from_inputs, load_knowledge_base, summarize_knowledge_base
    )

    saved = build_from_inputs(enriched, occ_embeddings)
    logger.info(f"  ✓ {len(saved)} JSON files lưu tại data/occupation_profiles/")

    # ── Tóm tắt ──────────────────────────────────────────────────────────────
    elapsed = datetime.now() - total_start
    logger.info("\n" + "=" * 65)
    logger.info(f"OFFLINE PIPELINE HOÀN CHỈNH – {elapsed}")
    logger.info("=" * 65)

    kb = load_knowledge_base()
    summarize_knowledge_base(kb)

    logger.info("\nCác file đã tạo:")
    for path in sorted(saved.values()):
        logger.info(f"  {path}")


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Chạy toàn bộ Offline Pipeline (Bước 1-9)"
    )
    parser.add_argument(
        "--skip-training", action="store_true",
        help="Bỏ qua Bước 8 nếu đã có fine-tuned model"
    )
    parser.add_argument(
        "--use-pretrained", action="store_true",
        help="Dùng pretrained model, không fine-tune (nhanh nhưng kém hơn)"
    )
    parser.add_argument(
        "--epochs", type=int, default=3,
        help="Số epoch training (default: 3)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=16,
        help="Batch size training (default: 16)"
    )
    args = parser.parse_args()

    run(
        skip_training=args.skip_training,
        use_pretrained=args.use_pretrained,
        epochs=args.epochs,
        batch_size=args.batch_size,
    )