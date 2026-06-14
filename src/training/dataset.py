"""
dataset.py – Chuẩn bị dataset huấn luyện từ job_resume_fit.csv.

Chức năng:
  - Load và clean dữ liệu
  - Normalize ai_match_score từ [0,100] → [0,1]
  - Truncate texts dài (resume có thể tới 38K chars)
  - Tạo train/val split stratified theo score bucket
  - Trả về List[InputExample] cho CosineSimilarityLoss

CosineSimilarityLoss nhận:
    InputExample(texts=[text_a, text_b], label=float ∈ [0,1])
    và học để cosine_sim(emb_a, emb_b) → label
"""

import logging
import math
from pathlib import Path
from typing import Optional

import pandas as pd
from sentence_transformers import InputExample

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.config import (
    RESUME_FIT_FILE,
    RESUME_TEXT_COL,
    JOB_TEXT_COL,
    MATCH_SCORE_COL,
)
from src.offline.preprocessing.text_cleaner import clean_text

logger = logging.getLogger(__name__)

# Độ dài tối đa của text (ký tự) trước khi đưa vào model
# gte-multilingual-base max token = 8192, ~4 chars/token → 8192*3 = 24K chars an toàn
MAX_RESUME_CHARS = 8000   # resume dài, truncate hợp lý
MAX_JOB_CHARS    = 4000   # JD ngắn hơn, giữ gần full


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text về max_chars ký tự."""
    return text[:max_chars] if len(text) > max_chars else text


def _score_bucket(score: float, n_buckets: int = 5) -> int:
    """Chia score [0,1] thành n_buckets để stratify."""
    bucket = int(score * n_buckets)
    return min(bucket, n_buckets - 1)


def load_training_data(
    path: Path = RESUME_FIT_FILE,
    val_ratio: float = 0.1,
    seed: int = 42,
    clean: bool = True,
) -> tuple[list[InputExample], list[InputExample]]:
    """
    Load và chuẩn bị dataset huấn luyện.

    Args:
        path:      Đường dẫn tới job_resume_fit.csv.
        val_ratio: Tỷ lệ validation split (default 0.1 = 10%).
        seed:      Random seed cho reproducibility.
        clean:     Có áp dụng text_cleaner không (default True).

    Returns:
        (train_examples, val_examples) mỗi là List[InputExample].
    """
    logger.info(f"Đang load dataset từ: {path}")
    df = pd.read_csv(path, low_memory=False)
    initial = len(df)

    # Drop thiếu dữ liệu
    df = df.dropna(subset=[RESUME_TEXT_COL, JOB_TEXT_COL, MATCH_SCORE_COL])
    df = df[df[MATCH_SCORE_COL].between(0, 100)].reset_index(drop=True)
    logger.info(f"Sau lọc: {initial} → {len(df)} hàng")

    # Normalize score → [0, 1]
    df["label"] = df[MATCH_SCORE_COL] / 100.0

    # Stratified split theo score bucket
    df["_bucket"] = df["label"].apply(_score_bucket)
    val_idx = (
        df.groupby("_bucket", group_keys=False)
          .apply(lambda g: g.sample(frac=val_ratio, random_state=seed))
          .index
    )
    val_df   = df.loc[val_idx].reset_index(drop=True)
    train_df = df.drop(index=val_idx).reset_index(drop=True)

    logger.info(
        f"Split: train={len(train_df)}, val={len(val_df)} "
        f"(val_ratio={val_ratio:.0%})"
    )

    # Tạo InputExample
    def _make_examples(sub_df: pd.DataFrame) -> list[InputExample]:
        examples = []
        for _, row in sub_df.iterrows():
            resume = str(row[RESUME_TEXT_COL])
            job    = str(row[JOB_TEXT_COL])

            if clean:
                resume = clean_text(resume)
                job    = clean_text(job)

            resume = _truncate(resume, MAX_RESUME_CHARS)
            job    = _truncate(job,    MAX_JOB_CHARS)

            if not resume.strip() or not job.strip():
                continue

            examples.append(InputExample(
                texts=[resume, job],
                label=float(row["label"]),
            ))
        return examples

    train_examples = _make_examples(train_df)
    val_examples   = _make_examples(val_df)

    logger.info(
        f"InputExample: train={len(train_examples)}, val={len(val_examples)}"
    )
    return train_examples, val_examples


def log_score_distribution(examples: list[InputExample], name: str = "dataset") -> None:
    """In phân phối score để kiểm tra dataset."""
    labels = [e.label for e in examples]
    buckets = [0] * 5
    for lbl in labels:
        buckets[_score_bucket(lbl)] += 1
    total = len(labels)
    print(f"\n  {name} distribution (n={total}):")
    ranges = ["[0.0,0.2)", "[0.2,0.4)", "[0.4,0.6)", "[0.6,0.8)", "[0.8,1.0]"]
    for rng, cnt in zip(ranges, buckets):
        bar = "█" * int(cnt / total * 40)
        print(f"    {rng}  {cnt:>4} ({cnt/total*100:>5.1f}%)  {bar}")
    print(f"  mean={sum(labels)/total:.3f}")


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    )

    train_ex, val_ex = load_training_data()

    log_score_distribution(train_ex, "train")
    log_score_distribution(val_ex,   "val")

    print(f"\nSample train[0]:")
    ex = train_ex[0]
    print(f"  label : {ex.label:.3f}")
    print(f"  resume: {ex.texts[0][:150]}...")
    print(f"  job   : {ex.texts[1][:150]}...")
