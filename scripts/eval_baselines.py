"""
eval_baselines.py – So sánh BASELINE để chứng minh fine-tuning có giá trị (Lỗ hổng 6)
                    và đo CALIBRATION điểm tuyệt đối (Lỗ hổng 2).

Hội đồng sẽ hỏi: "Fine-tune có hơn base model / cách đơn giản hơn không?" và
"val_spearman đo thứ hạng, nhưng hệ thống hiển thị '75% phù hợp' — điểm tuyệt đối
có đúng không?". Script này trả lời bằng số, trên CÙNG val split của lúc train.

Các phương pháp so sánh (dự đoán điểm match cho mỗi cặp resume–job trong val):
    1. Fine-tuned gte      – cosine embedding (mô hình đề xuất).
    2. Base gte            – cosine embedding (chưa fine-tune) → đo "fine-tune thêm gì".
    3. TF-IDF cosine       – vector hóa từ vựng cổ điển (sklearn).
    4. BM25                – xếp hạng truy hồi cổ điển (rank_bm25, nếu có).

Chỉ số:
    - Spearman / Pearson : tương quan THỨ HẠNG / TUYẾN TÍNH với ai_match_score.
    - RMSE / MAE         : sai số ĐIỂM TUYỆT ĐỐI (đưa cosine & label về cùng [0,1]).
      → RMSE/MAE chính là phần "calibration" mà val_spearman bỏ sót.

Chạy:  python scripts/eval_baselines.py
       python scripts/eval_baselines.py --max-pairs 300   (giới hạn cho nhanh)

Phụ thuộc tùy chọn: scikit-learn (TF-IDF), rank_bm25 (BM25), scipy (Spearman).
Thiếu cái nào → script báo và bỏ qua phương pháp đó, không vỡ.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ── Metrics ────────────────────────────────────────────────────────────────────
def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    mx, my = x.mean(), y.mean()
    den = math.sqrt(((x - mx) ** 2).sum() * ((y - my) ** 2).sum())
    return float(((x - mx) * (y - my)).sum() / den) if den > 0 else 0.0


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    try:
        from scipy.stats import spearmanr
        return float(spearmanr(x, y).correlation)
    except ImportError:
        def rank(a):
            o = np.argsort(a); r = np.empty_like(o, float); r[o] = np.arange(len(a)); return r
        return _pearson(rank(x), rank(y))


def _minmax(a: np.ndarray) -> np.ndarray:
    lo, hi = a.min(), a.max()
    return (a - lo) / (hi - lo) if hi > lo else np.full_like(a, 0.5)


def _report(name: str, pred: np.ndarray, label: np.ndarray) -> dict:
    """Pred & label đều ∈ [0,1]. RMSE/MAE đo trên thang [0,1]."""
    pred01 = _minmax(pred) if (pred.min() < 0 or pred.max() > 1) else pred
    rmse = math.sqrt(float(np.mean((pred01 - label) ** 2)))
    mae = float(np.mean(np.abs(pred01 - label)))
    row = {
        "method": name,
        "spearman": round(_spearman(pred, label), 4),
        "pearson": round(_pearson(pred, label), 4),
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
    }
    return row


# ── Predictors ─────────────────────────────────────────────────────────────────
def _embed_cosine(resumes, jobs, use_finetuned: bool, batch_size: int = 32) -> np.ndarray:
    from src.offline.embedding_step7.embedder import load_model
    model = load_model(use_finetuned=use_finetuned)
    model.max_seq_length = 256
    er = model.encode(resumes, batch_size=batch_size, normalize_embeddings=True,
                      convert_to_numpy=True, show_progress_bar=True)
    ej = model.encode(jobs, batch_size=batch_size, normalize_embeddings=True,
                      convert_to_numpy=True, show_progress_bar=True)
    return np.sum(er * ej, axis=1)


def _tfidf_cosine(resumes, jobs) -> np.ndarray | None:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        print("  [bỏ qua TF-IDF] chưa cài scikit-learn (pip install scikit-learn)")
        return None
    vec = TfidfVectorizer(max_features=20000, ngram_range=(1, 2))
    vec.fit(list(resumes) + list(jobs))
    R = vec.transform(resumes)
    J = vec.transform(jobs)
    # cosine theo hàng (cả hai đã l2-norm bởi TfidfVectorizer mặc định)
    return np.asarray(R.multiply(J).sum(axis=1)).ravel()


def _bm25(resumes, jobs) -> np.ndarray | None:
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        print("  [bỏ qua BM25] chưa cài rank_bm25 (pip install rank_bm25)")
        return None
    tok_jobs = [j.lower().split() for j in jobs]
    bm25 = BM25Okapi(tok_jobs)
    # Điểm BM25 của job_i với query = resume_i (chỉ lấy đường chéo).
    scores = np.array([
        bm25.get_scores(resumes[i].lower().split())[i] for i in range(len(resumes))
    ])
    return scores


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pairs", type=int, default=0, help="Giới hạn số cặp val (0=toàn bộ)")
    args = ap.parse_args()

    from src.training.dataset import load_training_data
    _, val = load_training_data()
    if args.max_pairs and len(val) > args.max_pairs:
        val = val[: args.max_pairs]

    resumes = [ex.texts[0] for ex in val]
    jobs = [ex.texts[1] for ex in val]
    labels = np.array([ex.label for ex in val], dtype=np.float64)
    print(f"Val pairs: {len(val)}  (label mean={labels.mean():.3f})\n")

    rows: list[dict] = []

    print("[1] Fine-tuned gte (cosine)...")
    rows.append(_report("Fine-tuned gte (cosine)", _embed_cosine(resumes, jobs, True), labels))

    print("[2] Base gte (cosine)...")
    rows.append(_report("Base gte (cosine)", _embed_cosine(resumes, jobs, False), labels))

    print("[3] TF-IDF cosine...")
    tf = _tfidf_cosine(resumes, jobs)
    if tf is not None:
        rows.append(_report("TF-IDF cosine", tf, labels))

    print("[4] BM25...")
    bm = _bm25(resumes, jobs)
    if bm is not None:
        rows.append(_report("BM25", bm, labels))

    # ── Bảng kết quả ──
    print("\n" + "=" * 72)
    print(f"{'Method':<26}{'Spearman':>10}{'Pearson':>10}{'RMSE':>9}{'MAE':>9}")
    print("-" * 72)
    for r in rows:
        print(f"{r['method']:<26}{r['spearman']:>10.4f}{r['pearson']:>10.4f}"
              f"{r['rmse']:>9.4f}{r['mae']:>9.4f}")
    print("=" * 72)
    print("Spearman/Pearson: cao = tốt | RMSE/MAE: thấp = tốt (đo calibration tuyệt đối).")
    print("So sánh dòng 1 vs 2 → fine-tuning đóng góp bao nhiêu. So với 3,4 → hơn baseline cổ điển.")


if __name__ == "__main__":
    main()
