"""
ablation.py – Ablation cho trọng số MATCH_ALPHA / MATCH_BETA (Lỗ hổng 4).

Hội đồng sẽ hỏi: "Tại sao alpha=0.5? Không phải 0.6/0.4 hay 0.7/0.3?". Script này
quét α từ 0.0→1.0 (β = 1−α), đo tương quan của điểm tổng hợp với ai_match_score
trên val split → chọn α theo DỮ LIỆU thay vì gán tùy tiện.

Điểm tổng hợp cho mỗi cặp resume–job:
    combined = α · semantic + β · skill_overlap

    semantic     = cosine(fine-tuned embedding) ∈ [0,1]   (Bước 7)
    skill_overlap= |skill(resume) ∩ skill(job)| / |skill(job)|  (proxy của Bước 8;
                   job đóng vai "occupation", skill trích bằng cùng extractor, so
                   khớp đã qua canonicalize + SYNONYM_MAP nên đồng nghĩa vẫn khớp)

LƯU Ý phạm vi: đây là ablation cho TRỌNG SỐ KẾT HỢP (MATCH_ALPHA/BETA). Trọng số
skill-weight ALPHA/BETA (freq vs tf-idf) tác động ở tầng occupation profile, cần
ground-truth cấp nghề để đánh giá → để phần "Hướng phát triển".

Chạy:  python scripts/ablation.py
       python scripts/ablation.py --max-pairs 300
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _pearson(x, y):
    mx, my = x.mean(), y.mean()
    den = math.sqrt(((x - mx) ** 2).sum() * ((y - my) ** 2).sum())
    return float(((x - mx) * (y - my)).sum() / den) if den > 0 else 0.0


def _spearman(x, y):
    try:
        from scipy.stats import spearmanr
        return float(spearmanr(x, y).correlation)
    except ImportError:
        def rank(a):
            o = np.argsort(a); r = np.empty_like(o, float); r[o] = np.arange(len(a)); return r
        return _pearson(rank(x), rank(y))


def _skill_overlap(resumes, jobs) -> np.ndarray:
    """Tỷ lệ skill job được resume đáp ứng (đã canonicalize + synonym)."""
    from src.offline.skill_extraction_step2.extractor import extract_skills_from_text
    from src.online.semantic_skill_match import match_skills

    out = np.zeros(len(resumes), dtype=np.float64)
    for i, (r, j) in enumerate(zip(resumes, jobs)):
        job_skills = extract_skills_from_text(j)
        if not job_skills:
            continue
        res_skills = extract_skills_from_text(r)
        mr = match_skills(res_skills, job_skills, mode="exact")  # deterministic
        out[i] = len(mr.matched) / len(job_skills)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pairs", type=int, default=0)
    ap.add_argument("--step", type=float, default=0.1)
    args = ap.parse_args()

    from src.training.dataset import load_training_data
    from src.offline.embedding_step7.embedder import load_model

    _, val = load_training_data()
    if args.max_pairs and len(val) > args.max_pairs:
        val = val[: args.max_pairs]
    resumes = [ex.texts[0] for ex in val]
    jobs = [ex.texts[1] for ex in val]
    labels = np.array([ex.label for ex in val], dtype=np.float64)
    print(f"Val pairs: {len(val)}\n")

    print("Tính semantic (fine-tuned cosine)...")
    model = load_model(use_finetuned=True)
    model.max_seq_length = 256
    er = model.encode(resumes, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=True)
    ej = model.encode(jobs, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=True)
    semantic = np.clip(np.sum(er * ej, axis=1), 0.0, 1.0)

    print("Tính skill_overlap...")
    skill = _skill_overlap(resumes, jobs)

    print("\n" + "=" * 60)
    print(f"{'alpha':>6}{'beta':>6}{'Spearman':>11}{'Pearson':>10}{'RMSE':>9}")
    print("-" * 60)
    best = None
    a = 0.0
    while a <= 1.0001:
        b = 1.0 - a
        combined = a * semantic + b * skill
        sp = _spearman(combined, labels)
        pe = _pearson(combined, labels)
        rmse = math.sqrt(float(np.mean((np.clip(combined, 0, 1) - labels) ** 2)))
        marker = ""
        if best is None or sp > best[1]:
            best = (a, sp, pe, rmse)
        print(f"{a:>6.1f}{b:>6.1f}{sp:>11.4f}{pe:>10.4f}{rmse:>9.4f}{marker}")
        a += args.step
    print("=" * 60)
    print(f"α tối ưu theo Spearman: α={best[0]:.1f}, β={1-best[0]:.1f} "
          f"(Spearman={best[1]:.4f}, Pearson={best[2]:.4f}, RMSE={best[3]:.4f})")
    print("→ Dùng con số này để biện minh MATCH_ALPHA/MATCH_BETA thay vì 0.5/0.5 mặc định.")


if __name__ == "__main__":
    main()
