"""
calibrate_short_skills.py – Bổ sung cho calibrate_skill_threshold.py: kiểm chứng
cosine-embedding KHÔNG đáng tin khi so khớp TÊN KỸ NĂNG NGẮN (token/cụm rất ngắn),
khác với các cụm mô tả dài.

Câu hỏi phản biện: "Đã có embedding model, sao không dùng semantic cho skill?"
calibrate_skill_threshold.py dùng các cụm dài (vd 'Quản lý dự án' ~ 'Project
Management') và cho thấy TÁCH ĐƯỢC. Nhưng skill thực tế trong CV/JD phần lớn là
tên công nghệ ngắn (FastAPI, Redis, React...). Với các token ngắn này, embedding
câu bị anisotropy nặng: các cặp CÙNG NHÓM nhưng KHÁC NGHĨA (Java~JavaScript,
Docker~Kubernetes) lại có cosine CAO hơn cả các cặp đồng nghĩa/kéo theo thật sự
(FastAPI~REST API, Photoshop~UI Design). Hai phân phối đảo ngược → không ngưỡng
nào tách được → cosine gây false-positive "báo ứng viên CÓ Redis" khi họ chỉ có
PostgreSQL. Đây là cơ sở định lượng cho quyết định dùng exact-match + LLM equivalence.

Chạy:  <python3.12> run_calibrate_gpu.py   (đã trỏ launcher) hoặc trực tiếp qua
launcher tương tự run_eval_gpu.py để tránh tràn stack import trên pythoncore-3.12.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Cặp NÊN khớp: đồng nghĩa hoặc quan hệ kéo theo (framework ⟹ khái niệm/chuẩn).
SHOULD_MATCH = [
    ("FastAPI", "REST API"),
    ("Node.js", "JavaScript"),
    ("scikit-learn", "Machine Learning"),
    ("Photoshop", "UI Design"),
    ("Google Ads", "Digital Marketing"),
    ("PyTorch", "Deep Learning"),
]
# Cặp KHÔNG nên khớp: cùng miền/nhóm nhưng là công nghệ riêng biệt, không thay thế nhau.
SHOULD_NOT_MATCH = [
    ("Redis", "PostgreSQL"),
    ("Java", "JavaScript"),
    ("jQuery", "HTML"),
    ("Docker", "Kubernetes"),
    ("React", "Angular"),
    ("MySQL", "MongoDB"),
]


def _eval(use_finetuned: bool) -> None:
    from src.offline.embedding_step7.embedder import load_model

    model = load_model(use_finetuned=use_finetuned)
    model.max_seq_length = 64

    def sim(a: str, b: str) -> float:
        e = model.encode([a, b], normalize_embeddings=True, convert_to_numpy=True,
                         show_progress_bar=False)
        return float(e[0] @ e[1])

    pos = [(a, b, sim(a, b)) for a, b in SHOULD_MATCH]
    neg = [(a, b, sim(a, b)) for a, b in SHOULD_NOT_MATCH]

    tag = "FINE-TUNED" if use_finetuned else "BASE"
    print(f"\n===== {tag} gte (short skill tokens) =====")
    print(" NÊN khớp (muốn CAO):")
    for a, b, s in sorted(pos, key=lambda x: -x[2]):
        print(f"   {s:.3f}  {a}  ~  {b}")
    print(" KHÔNG nên khớp (muốn THẤP):")
    for a, b, s in sorted(neg, key=lambda x: -x[2]):
        print(f"   {s:.3f}  {a}  ~  {b}")

    ps = np.array([s for *_, s in pos])
    ns = np.array([s for *_, s in neg])
    min_pos, max_neg = ps.min(), ns.max()
    overlap = int((ns >= min_pos).sum())
    print(f"\n  min(nên khớp)     = {min_pos:.3f}")
    print(f"  max(không nên khớp)= {max_neg:.3f}")
    if max_neg < min_pos:
        print(f"  → tách được ở ngưỡng ≈ {(max_neg + min_pos) / 2:.3f}")
    else:
        print(f"  → KHÔNG tách được: {overlap}/{len(ns)} cặp không-nên-khớp có cosine ≥ "
              f"min(nên khớp). Phân phối đảo ngược → cosine không dùng được cho skill ngắn.")


def main() -> None:
    _eval(use_finetuned=True)


if __name__ == "__main__":
    main()
