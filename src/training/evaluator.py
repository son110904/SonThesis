"""
evaluator.py – Đánh giá model trong quá trình và sau khi huấn luyện.

Metrics:
  - Pearson correlation: cosine_sim vs label (đo linearity)
  - Spearman correlation: rank-based (robust hơn với outlier)
  - MSE: mean squared error giữa cosine_sim và label
  - Phân tích theo score bucket để phát hiện bias

Dùng EmbeddingSimilarityEvaluator của sentence-transformers
kết hợp thêm custom metrics.
"""

import logging
import math
from pathlib import Path
from typing import Optional

import numpy as np
from sentence_transformers import InputExample, SentenceTransformer
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

logger = logging.getLogger(__name__)


def make_evaluator(
    val_examples: list[InputExample],
    name: str = "val",
) -> EmbeddingSimilarityEvaluator:
    """
    Tạo EmbeddingSimilarityEvaluator từ validation examples.

    sentence-transformers sẽ gọi evaluator này sau mỗi eval_steps
    và lưu checkpoint khi score cải thiện.

    Args:
        val_examples: List[InputExample] từ dataset.load_training_data().
        name:         Tên prefix cho output files.

    Returns:
        EmbeddingSimilarityEvaluator instance.
    """
    sentences1 = [ex.texts[0] for ex in val_examples]
    sentences2 = [ex.texts[1] for ex in val_examples]
    scores     = [ex.label    for ex in val_examples]

    evaluator = EmbeddingSimilarityEvaluator(
        sentences1=sentences1,
        sentences2=sentences2,
        scores=scores,
        name=name,
        show_progress_bar=False,
        write_csv=True,
        precision=None,            # dùng float32 default
    )

    logger.info(f"Evaluator tạo xong: {len(val_examples)} val examples")
    return evaluator


def evaluate_model(
    model: SentenceTransformer,
    val_examples: list[InputExample],
    batch_size: int = 32,
) -> dict[str, float]:
    """
    Đánh giá model trên validation set, trả về metrics chi tiết.

    Args:
        model:        SentenceTransformer instance.
        val_examples: Validation examples.
        batch_size:   Batch size khi encode.

    Returns:
        Dict metrics: pearson, spearman, mse, rmse.
    """
    logger.info(f"Đang đánh giá model trên {len(val_examples)} val examples...")

    sentences1 = [ex.texts[0] for ex in val_examples]
    sentences2 = [ex.texts[1] for ex in val_examples]
    labels     = np.array([ex.label for ex in val_examples], dtype=np.float32)

    # Encode
    emb1 = model.encode(sentences1, batch_size=batch_size,
                         show_progress_bar=False, normalize_embeddings=True,
                         convert_to_numpy=True)
    emb2 = model.encode(sentences2, batch_size=batch_size,
                         show_progress_bar=False, normalize_embeddings=True,
                         convert_to_numpy=True)

    # Cosine similarity (L2-normalized → dot product)
    cosine_scores = np.sum(emb1 * emb2, axis=1)

    # MSE / RMSE
    mse  = float(np.mean((cosine_scores - labels) ** 2))
    rmse = math.sqrt(mse)

    # Pearson correlation
    def pearson(x, y):
        mx, my = x.mean(), y.mean()
        num = np.sum((x - mx) * (y - my))
        den = math.sqrt(np.sum((x - mx) ** 2) * np.sum((y - my) ** 2))
        return float(num / den) if den > 0 else 0.0

    # Spearman correlation
    def spearman(x, y):
        from scipy.stats import spearmanr
        corr, _ = spearmanr(x, y)
        return float(corr)

    pcc = pearson(cosine_scores, labels)
    try:
        scc = spearman(cosine_scores, labels)
    except ImportError:
        # scipy không có → dùng rank thủ công
        def rank_array(arr):
            order = np.argsort(arr)
            ranks = np.empty_like(order, dtype=float)
            ranks[order] = np.arange(len(arr))
            return ranks
        scc = pearson(rank_array(cosine_scores), rank_array(labels))

    metrics = {
        "pearson":  round(pcc,  4),
        "spearman": round(scc,  4),
        "mse":      round(mse,  4),
        "rmse":     round(rmse, 4),
    }

    # Phân tích theo bucket
    bucket_metrics: dict[str, dict] = {}
    for lo, hi, name in [
        (0.0, 0.2, "low"),
        (0.2, 0.4, "medium_low"),
        (0.4, 0.6, "medium"),
        (0.6, 0.8, "medium_high"),
        (0.8, 1.0, "high"),
    ]:
        mask = (labels >= lo) & (labels < hi + 1e-9)
        if mask.sum() > 0:
            bucket_mse = float(np.mean((cosine_scores[mask] - labels[mask]) ** 2))
            bucket_metrics[name] = {
                "n": int(mask.sum()),
                "mse": round(bucket_mse, 4),
                "pred_mean": round(float(cosine_scores[mask].mean()), 4),
                "label_mean": round(float(labels[mask].mean()), 4),
            }

    metrics["bucket_analysis"] = bucket_metrics  # type: ignore

    logger.info(
        f"Eval — Pearson: {pcc:.4f}  Spearman: {scc:.4f}  "
        f"RMSE: {rmse:.4f}  MSE: {mse:.4f}"
    )
    return metrics


def print_eval_report(metrics: dict) -> None:
    """In báo cáo đánh giá chi tiết."""
    print("\n" + "─" * 50)
    print("EVALUATION REPORT")
    print("─" * 50)
    print(f"  Pearson  : {metrics['pearson']:>7.4f}  (linearity)")
    print(f"  Spearman : {metrics['spearman']:>7.4f}  (rank correlation)")
    print(f"  RMSE     : {metrics['rmse']:>7.4f}")
    print(f"  MSE      : {metrics['mse']:>7.4f}")

    if "bucket_analysis" in metrics:
        print("\n  Score bucket analysis:")
        print(f"  {'Bucket':<15} {'N':>5}  {'Label_mean':>10}  {'Pred_mean':>9}  {'MSE':>7}")
        print(f"  {'-'*15} {'-'*5}  {'-'*10}  {'-'*9}  {'-'*7}")
        for bucket, bm in metrics["bucket_analysis"].items():
            print(
                f"  {bucket:<15} {bm['n']:>5}  "
                f"{bm['label_mean']:>10.3f}  {bm['pred_mean']:>9.3f}  "
                f"{bm['mse']:>7.4f}"
            )
    print("─" * 50)


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    )
    print("evaluator.py: import OK. Chạy trainer.py để test đầy đủ.")
