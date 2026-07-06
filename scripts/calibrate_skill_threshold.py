"""
calibrate_skill_threshold.py – Kiểm chứng vì sao KHÔNG dùng embedding-cosine để
                               so khớp skill ngắn (cơ sở cho quyết định ở Lỗ hổng 5).

Câu hỏi: "Đã có embedding model, sao không dùng semantic matching cho skill?"
Trả lời bằng số: đo cosine giữa các cặp skill ĐỒNG NGHĨA (muốn CAO) và KHÁC NGHĨA
(muốn THẤP). Nếu hai phân phối CHỒNG LẤN → không tồn tại ngưỡng tách bạch → cosine
trên cụm skill ngắn không đáng tin (hiện tượng anisotropy của embedding câu ngắn).

Script in: cosine từng cặp, ngưỡng tách tốt nhất, và độ chồng lấn (số cặp khác nghĩa
≥ min(synonym)). Chạy được cho cả base lẫn fine-tuned để so sánh.

Chạy:  python scripts/calibrate_skill_threshold.py            # base + fine-tuned
       python scripts/calibrate_skill_threshold.py --finetuned-only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Cặp skill gán nhãn thủ công (mở rộng tùy ý để khảo sát kỹ hơn).
SYNONYMS = [
    ("Machine Learning", "Học máy"),
    ("lập trình", "Coding"),
    ("Kế toán", "Accounting"),
    ("Quản lý dự án", "Project Management"),
    ("Kiểm thử phần mềm", "Software Testing"),
    ("An ninh mạng", "Cyber Security"),
    ("Phân tích dữ liệu", "Data Analysis"),
    ("Thiết kế đồ họa", "Graphic Design"),
]
NON_SYNONYMS = [
    ("Quản lý dự án", "Học máy"),
    ("Kế toán", "lập trình web"),
    ("Photoshop", "SQL"),
    ("Marketing", "Kế toán"),
    ("Docker", "Tuyển dụng"),
    ("Java", "Thiết kế đồ họa"),
    ("Kiểm toán", "Kubernetes"),
    ("SEO", "Cơ khí"),
]


def _eval_model(use_finetuned: bool) -> None:
    from src.offline.embedding_step7.embedder import load_model
    model = load_model(use_finetuned=use_finetuned)
    model.max_seq_length = 64

    def sim(a: str, b: str) -> float:
        e = model.encode([a, b], normalize_embeddings=True, convert_to_numpy=True,
                         show_progress_bar=False)
        return float(e[0] @ e[1])

    syn = [(a, b, sim(a, b)) for a, b in SYNONYMS]
    non = [(a, b, sim(a, b)) for a, b in NON_SYNONYMS]

    tag = "FINE-TUNED" if use_finetuned else "BASE"
    print(f"\n===== {tag} gte =====")
    print(" Đồng nghĩa (muốn CAO):")
    for a, b, s in sorted(syn, key=lambda x: -x[2]):
        print(f"   {s:.3f}  {a}  ~  {b}")
    print(" Khác nghĩa (muốn THẤP):")
    for a, b, s in sorted(non, key=lambda x: -x[2]):
        print(f"   {s:.3f}  {a}  ~  {b}")

    syn_s = np.array([s for *_, s in syn])
    non_s = np.array([s for *_, s in non])
    min_syn, max_non = syn_s.min(), non_s.max()
    overlap = int((non_s >= min_syn).sum())
    print(f"\n  min(synonym)   = {min_syn:.3f}")
    print(f"  max(non-synonym)= {max_non:.3f}")
    if max_non < min_syn:
        thr = (max_non + min_syn) / 2
        print(f"  → TÁCH ĐƯỢC bằng ngưỡng ≈ {thr:.3f}")
    else:
        print(f"  → KHÔNG tách được: {overlap}/{len(non_s)} cặp khác nghĩa có sim ≥ "
              f"min(synonym). Phân phối chồng lấn → embedding-cosine không đáng tin "
              f"cho skill ngắn. Dùng canonicalize + SYNONYM_MAP (deterministic) thay thế.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--finetuned-only", action="store_true")
    args = ap.parse_args()
    if not args.finetuned_only:
        _eval_model(use_finetuned=False)
    _eval_model(use_finetuned=True)


if __name__ == "__main__":
    main()
