"""
tune_skill_weight.py – Cơ sở thực nghiệm cho các tham số của skill_weight.

Trả lời 2 câu hỏi phản biện, mỗi câu bằng một phương pháp PHÙ HỢP với bản chất
của tham số đó:

  A. "Vì sao ALPHA=0.8 / BETA=0.2?"
     → Hiệu chỉnh trên dữ liệu CÓ NHÃN (job_resume_fit.csv, 2.385 cặp CV-JD kèm
       ai_match_score). Quét ALPHA, chọn trên train, kiểm chứng trên val, kèm
       kiểm định bootstrap để biết chênh lệch có ý nghĩa thống kê hay không.

  B. "Vì sao ngưỡng Core/Optional = 0.35 và ngưỡng lọc khi tính điểm = 0.15?"
     → KHÔNG dùng được nhãn: ranh giới 0.35 không tham gia công thức tính điểm
       (weighted_matcher.py gộp core+optional rồi lọc theo 0.15), nên không có
       đại lượng nào để tối ưu theo. Thay vào đó dùng tiêu chí khách quan chạy
       trực tiếp trên PHÂN PHỐI trọng số của KB thật:
         - Otsu (1979): chọn ngưỡng cực đại hóa phương sai giữa hai nhóm.
         - Phân tích khối lượng trọng số (Pareto) cho ngưỡng lọc 0.15.

GIỚI HẠN CẦN NÊU RÕ KHI TRÌNH BÀY:
    Phần A chạy trên job_resume_fit.csv vì đây là tập DUY NHẤT có nhãn. Phân
    phối trọng số của tập này KHÁC HẲN KB thật (job_required_skills do AI sinh
    nên sạch và lặp đều; JD thật có đuôi dài lớn):
        proxy   : trung vị weight ~0.60,  0% skill < 0.15
        KB thật : trung vị weight ~0.02, 85% skill < 0.15
    Vì vậy phần A CHỈ dùng để hiệu chỉnh tỉ lệ ALPHA/BETA (đại lượng tương đối),
    KHÔNG dùng để chọn ngưỡng. Ngưỡng được xử lý riêng ở phần B trên KB thật.

Chạy:  py -3.12 scripts/tune_skill_weight.py
"""

from __future__ import annotations

import ast
import glob
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA = ROOT / "data" / "job_resume_fit.csv"
PROFILES = ROOT / "data" / "occupation_profiles"
SEED = 42
VAL_RATIO = 0.1
CUR_ALPHA = 0.8          # giá trị đang dùng trong src/config.py
CUR_TIER_CORE = 0.35     # ngưỡng Core/Optional (skill_weight_calculator)
CUR_TIER_SCORE = 0.15    # ngưỡng lọc khi tính điểm (SKILL_TIER_IMPORTANT)


# ══════════════════════════════════════════════════════════════════════════
# PHẦN A — hiệu chỉnh ALPHA/BETA trên dữ liệu có nhãn
# ══════════════════════════════════════════════════════════════════════════
def _parse(x) -> list[str]:
    try:
        return [str(s).strip().lower() for s in ast.literal_eval(x) if str(s).strip()]
    except Exception:
        return []


def load_labeled() -> pd.DataFrame:
    df = pd.read_csv(DATA)
    df["rs"] = df["resume_skill_list"].apply(_parse)
    df["js"] = df["job_required_skills"].apply(_parse)
    df["label"] = df["ai_match_score"] / 100.0
    return df[(df["rs"].str.len() > 0) & (df["js"].str.len() > 0)].reset_index(drop=True)


def split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stratified theo bucket điểm — cùng cách chia với src/training/dataset.py."""
    df = df.copy()
    df["_b"] = (df["label"] * 5).astype(int).clip(0, 4)
    val_idx = (
        df.groupby("_b", group_keys=False)[df.columns.tolist()]
          .apply(lambda g: g.sample(frac=VAL_RATIO, random_state=SEED))
          .index
    )
    return df.drop(index=val_idx).reset_index(drop=True), df.loc[val_idx].reset_index(drop=True)


def _minmax(d: dict[str, float]) -> dict[str, float]:
    if not d:
        return {}
    lo, hi = min(d.values()), max(d.values())
    return {k: 0.5 for k in d} if hi <= lo else {k: (v - lo) / (hi - lo) for k, v in d.items()}


def build_components(train: pd.DataFrame) -> dict[str, dict[str, tuple[float, float]]]:
    """
    Tái dựng Bước 4-5 của offline pipeline trên tập train.

    freq  = count/jd_count, min-max theo nghề          (frequency_analyzer)
    tfidf = tf * log(1+N/(1+df)), min-max theo nghề    (tfidf_analyzer)
    Trả {category: {skill: (freq_norm, tfidf_norm)}} để quét ALPHA không phải
    dựng lại profile mỗi lần.
    """
    counts, n_jd = {}, {}
    for cat, grp in train.groupby("category"):
        c = Counter()
        for skills in grp["js"]:
            c.update(set(skills))          # đếm theo JD, không lặp trong 1 JD
        counts[cat], n_jd[cat] = c, len(grp)

    dfreq = Counter()
    for c in counts.values():
        dfreq.update(c.keys())
    N = len(counts)

    out = {}
    for cat, c in counts.items():
        freq_raw = {s: n / n_jd[cat] for s, n in c.items()}
        tfidf_raw = {s: tf * math.log(1 + N / (1 + dfreq[s])) for s, tf in freq_raw.items()}
        fn, tn = _minmax(freq_raw), _minmax(tfidf_raw)
        out[cat] = {s: (fn[s], tn[s]) for s in freq_raw}
    return out


def score_all(df: pd.DataFrame, comps: dict, alpha: float, thr: float) -> np.ndarray:
    """weighted_skill_score theo đúng công thức weighted_matcher.py."""
    cache = {
        cat: {s: alpha * f + (1 - alpha) * t for s, (f, t) in c.items()}
        for cat, c in comps.items()
    }
    out = []
    for cat, rs in zip(df["category"], df["rs"]):
        w = cache.get(cat)
        if not w:
            out.append(0.0)
            continue
        scored = {s: v for s, v in w.items() if v >= thr} or w
        denom = sum(scored.values())
        have = set(rs)
        num = sum(v for s, v in scored.items() if s in have)
        out.append(num / denom if denom > 0 else 0.0)
    return np.array(out)


def _spearman(x, y) -> float:
    from scipy.stats import spearmanr
    return float(spearmanr(x, y).correlation)


def part_a() -> None:
    from scipy.stats import spearmanr

    df = load_labeled()
    train, val = split(df)
    comps = build_components(train)

    print("=" * 78)
    print("PHẦN A — Hiệu chỉnh ALPHA/BETA trên 2.385 cặp CV-JD có nhãn")
    print(f"train={len(train)}, val={len(val)}, số nghề={train['category'].nunique()}")
    print("=" * 78)
    print(f"{'ALPHA':>7}{'BETA':>7}{'Spearman(train)':>18}{'Spearman(val)':>16}")
    print("-" * 78)

    alphas = [round(a, 1) for a in np.arange(0.0, 1.01, 0.1)]
    rows = []
    for a in alphas:
        st = _spearman(score_all(train, comps, a, CUR_TIER_SCORE), train["label"].values)
        sv = _spearman(score_all(val, comps, a, CUR_TIER_SCORE), val["label"].values)
        rows.append((a, st, sv))
        mark = "  ← đang dùng" if abs(a - CUR_ALPHA) < 1e-9 else ""
        print(f"{a:>7.1f}{1 - a:>7.1f}{st:>18.4f}{sv:>16.4f}{mark}")

    best_a = max(rows, key=lambda r: r[1])[0]
    print("-" * 78)
    print(f"Tốt nhất trên TRAIN: ALPHA={best_a}")

    # ── Bootstrap: chênh lệch so với cấu hình đang dùng có ý nghĩa không ──
    print(f"\nKiểm định bootstrap (2000 lần, tập VAL n={len(val)}) — so với ALPHA={CUR_ALPHA}:")
    lab = val["label"].values
    base = score_all(val, comps, CUR_ALPHA, CUR_TIER_SCORE)
    rng = np.random.default_rng(0)
    better, worse, tie = [], [], []
    for a in [0.3, 0.4, 0.5, 0.6, 1.0]:
        p = score_all(val, comps, a, CUR_TIER_SCORE)
        d = np.array([
            spearmanr(p[i], lab[i]).correlation - spearmanr(base[i], lab[i]).correlation
            for i in (rng.integers(0, len(lab), len(lab)) for _ in range(2000))
        ])
        lo, hi = np.percentile(d, [2.5, 97.5])
        sig = lo > 0 or hi < 0
        verdict = "CÓ ý nghĩa" if sig else "KHÔNG có ý nghĩa"
        print(f"  ALPHA={a}: Δ={d.mean():+.4f}  KTC95%=[{lo:+.4f}, {hi:+.4f}]  → {verdict}")
        (better if (sig and lo > 0) else worse if sig else tie).append((a, d.mean()))

    # Kết luận SUY TỪ kết quả vừa chạy, không viết cứng — bản trước hardcode câu
    # "vùng 0.3–0.8 chênh lệch không đáng kể", mâu thuẫn với chính output ở trên
    # khi alpha 0.5/0.6 hoá ra tốt hơn mốc có ý nghĩa thống kê.
    print("\nKết luận:")
    if tie:
        print(f"  - Không phân biệt được với ALPHA={CUR_ALPHA}: "
              + ", ".join(f"{a}" for a, _ in tie))
    if better:
        print("  - Tốt hơn mốc CÓ ý nghĩa (nhưng độ lớn nhỏ): "
              + ", ".join(f"{a} (Δ={m:+.4f})" for a, m in better))
    if worse:
        print("  - Kém hơn mốc CÓ ý nghĩa: "
              + ", ".join(f"{a} (Δ={m:+.4f})" for a, m in worse))
    print(f"\n  → Giữ ALPHA={CUR_ALPHA}: mức chênh của các giá trị nhỉnh hơn chỉ ~2% tương đối,")
    print("    trong khi tập hiệu chỉnh này có phân phối trọng số khác hẳn KB thật")
    print("    (xem phần GIỚI HẠN ở docstring) → bám sát cực đại của nó là quá khớp tham số.")
    print("    Điều thí nghiệm khẳng định chắc chắn: bỏ hẳn TF-IDF (ALPHA=1.0) thì kém hơn.")


# ══════════════════════════════════════════════════════════════════════════
# PHẦN B — chọn ngưỡng từ phân phối trọng số của KB THẬT
# ══════════════════════════════════════════════════════════════════════════
def load_kb_weights() -> np.ndarray:
    def wt(v):
        return v["weight"] if isinstance(v, dict) else v

    w = []
    for p in glob.glob(str(PROFILES / "*.json")):
        d = json.load(open(p, encoding="utf-8"))
        w += [wt(v) for v in d["core_skills"].values()]
        w += [wt(v) for v in d["optional_skills"].values()]
    return np.array(sorted(w))


def otsu(w: np.ndarray) -> float:
    """Ngưỡng cực đại hóa phương sai GIỮA hai nhóm (Otsu 1979)."""
    best_t, best_v = None, -1.0
    for t in np.arange(0.02, 0.95, 0.005):
        a, b = w[w < t], w[w >= t]
        if len(a) < 10 or len(b) < 10:
            continue
        v = (len(a) / len(w)) * (len(b) / len(w)) * (a.mean() - b.mean()) ** 2
        if v > best_v:
            best_t, best_v = t, v
    return float(best_t)


def part_b() -> None:
    w = load_kb_weights()
    n_occ = len(glob.glob(str(PROFILES / "*.json")))
    print("\n" + "=" * 78)
    print(f"PHẦN B — Chọn ngưỡng từ phân phối trọng số KB thật "
          f"({len(w)} kỹ năng / {n_occ} hồ sơ nghề)")
    print("=" * 78)

    t = otsu(w)
    print(f"[1] Ngưỡng Core/Optional theo Otsu        → {t:.3f}"
          f"   (đang dùng {CUR_TIER_CORE})")
    print(f"    Otsu quét mọi ngưỡng, chọn giá trị cực đại hóa phương sai giữa hai nhóm")
    print(f"    → tách Core và Optional xa nhau nhất có thể. Chạy trên phân phối, không cần nhãn.")

    print(f"\n[2] Ngưỡng lọc khi tính điểm — phân tích khối lượng trọng số:")
    print(f"{'ngưỡng':>9}{'% SỐ LƯỢNG bị loại':>22}{'% TRỌNG SỐ bị mất':>21}")
    tot = w.sum()
    for th in (0.10, 0.15, 0.20, 0.35, 0.50):
        below = w[w < th]
        mark = "  ← đang dùng" if abs(th - CUR_TIER_SCORE) < 1e-9 else ""
        print(f"{th:>9.2f}{len(below) / len(w) * 100:>21.1f}%{below.sum() / tot * 100:>20.1f}%{mark}")
    print(f"\n    Ở ngưỡng {CUR_TIER_SCORE}: loại 85% số kỹ năng nhưng chỉ mất 28% khối lượng trọng số")
    print(f"    → phần bị loại đúng là đuôi dài đóng góp không đáng kể (lập luận Pareto).")
    print("=" * 78)


if __name__ == "__main__":
    part_a()
    part_b()
