"""
show_kb_stats.py – Tra cứu số liệu THỰC TẾ của cơ sở tri thức nghề nghiệp.

Dùng khi bảo vệ: thay vì trả lời chung chung "hệ thống tổng hợp từ hàng nghìn
tin tuyển dụng", chạy script này để đưa ra tên nghề + số JD + kỹ năng cụ thể.

Không nạp mô hình embedding nên chạy tức thì (<1 giây).

Cách dùng:
    py -3.12 scripts/show_kb_stats.py                  # tổng quan + 2 ví dụ mẫu
    py -3.12 scripts/show_kb_stats.py marketing        # tra 1 nghề theo từ khóa
    py -3.12 scripts/show_kb_stats.py backend
    py -3.12 scripts/show_kb_stats.py --all            # bảng đầy đủ 103 hồ sơ
"""

from __future__ import annotations

import glob
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "data" / "occupation_profiles"

# Số liệu pipeline tiền xử lý (khớp src/config.py: MAX_EXPERIENCE_MONTHS = 12)
TOTAL_JD_RAW = 48_092
TOTAL_JD_FILTERED = 30_135
N_CATEGORIES = 16

W = 78


def _w(v):
    """Profile lưu weight dạng số, hoặc dict {'weight': ...} tùy phiên bản."""
    return v["weight"] if isinstance(v, dict) else v


def _fold(s: str) -> str:
    """Bỏ dấu tiếng Việt + lowercase để tìm kiếm không cần gõ dấu."""
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").replace("_", " ")


def load_all() -> list[dict]:
    out = []
    for p in sorted(glob.glob(str(PROFILES / "*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        meta = d.get("_meta", {})
        out.append({
            "file": Path(p).stem,
            "name": d["occupation"],
            "jd_count": meta.get("jd_count", 0),
            "level": "lĩnh vực" if meta.get("granularity") != "sub_occupation" else "vị trí",
            "core": d.get("core_skills", {}),
            "optional": d.get("optional_skills", {}),
            "resp": d.get("responsibilities", []),
        })
    return out


def print_overview(profiles: list[dict]) -> None:
    counts = sorted(p["jd_count"] for p in profiles)
    n = len(counts)
    median = counts[n // 2]
    n_field = sum(1 for p in profiles if p["level"] == "lĩnh vực")

    print("=" * W)
    print("  CƠ SỞ TRI THỨC NGHỀ NGHIỆP — SỐ LIỆU THỰC TẾ")
    print("=" * W)
    print("\n[1] Quy mô dữ liệu đầu vào")
    print(f"    Tin tuyển dụng thu thập được       : {TOTAL_JD_RAW:>7,}".replace(",", "."))
    print(f"    Sau lọc kinh nghiệm <= 12 tháng    : {TOTAL_JD_FILTERED:>7,}".replace(",", ".")
          + f"  ({TOTAL_JD_FILTERED/TOTAL_JD_RAW*100:.1f}%)")
    print(f"    Số nhóm ngành bao phủ              : {N_CATEGORIES:>7}")

    print("\n[2] Hồ sơ nghề đã xây dựng")
    print(f"    Tổng số hồ sơ                      : {n:>7}")
    print(f"      - cấp lĩnh vực                   : {n_field:>7}")
    print(f"      - cấp vị trí việc làm cụ thể     : {n - n_field:>7}")

    print("\n[3] Số tin tuyển dụng dùng cho mỗi hồ sơ")
    print(f"    Nhiều nhất                         : {counts[-1]:>7,}".replace(",", "."))
    print(f"    Trung vị                           : {median:>7}")
    print(f"    Ít nhất                            : {counts[0]:>7}")
    print(f"    Số hồ sơ xây từ dưới 30 tin        : {sum(1 for c in counts if c < 30):>7} / {n}")


def print_profile(p: dict, n_skill: int = 8, n_resp: int = 4) -> None:
    print("\n" + "-" * W)
    print(f"  {p['name']}")
    print("-" * W)
    print(f"    Cấp độ                : {p['level']}")
    print(f"    Số tin tuyển dụng     : {p['jd_count']:,}".replace(",", "."))
    print(f"    Kỹ năng cốt lõi       : {len(p['core'])}")
    print(f"    Kỹ năng bổ trợ        : {len(p['optional'])}")
    print(f"    Trách nhiệm công việc : {len(p['resp'])}")

    core = sorted(p["core"].items(), key=lambda kv: -_w(kv[1]))[:n_skill]
    if core:
        print("\n    KỸ NĂNG CỐT LÕI (weight >= 0,35):")
        for k, v in core:
            bar = "#" * max(1, round(_w(v) * 28))
            print(f"      {_w(v):.3f}  {bar:<28}  {k}")

    opt = sorted(p["optional"].items(), key=lambda kv: -_w(kv[1]))[:5]
    if opt:
        print("\n    KỸ NĂNG BỔ TRỢ (5 cao nhất):")
        print("      " + " · ".join(f"{k} ({_w(v):.2f})" for k, v in opt))

    if p["resp"]:
        print(f"\n    TRÁCH NHIỆM CÔNG VIỆC ({n_resp}/{len(p['resp'])} mục đầu):")
        for r in p["resp"][:n_resp]:
            r = r.strip()
            print(f"      - {r[:88]}{'…' if len(r) > 88 else ''}")


def print_table(profiles: list[dict]) -> None:
    print("\n" + "=" * W)
    print(f"  TOÀN BỘ {len(profiles)} HỒ SƠ NGHỀ (sắp theo số tin tuyển dụng)")
    print("=" * W)
    print(f"  {'#JD':>6}  {'core':>4} {'opt':>4}  {'cấp':<9} {'tên nghề'}")
    print("-" * W)
    for p in sorted(profiles, key=lambda x: -x["jd_count"]):
        print(f"  {p['jd_count']:>6,}".replace(",", ".")
              + f"  {len(p['core']):>4} {len(p['optional']):>4}"
              + f"  {p['level']:<9} {p['name'][:44]}")


def main() -> None:
    profiles = load_all()
    if not profiles:
        raise SystemExit(f"Không tìm thấy hồ sơ nghề trong {PROFILES}")

    args = [a for a in sys.argv[1:] if a.strip()]

    if args and args[0] == "--all":
        print_overview(profiles)
        print_table(profiles)
        return

    if args:
        q = _fold(" ".join(args))
        hits = [p for p in profiles if q in _fold(p["file"]) or q in _fold(p["name"])]
        if not hits:
            print(f"Không có hồ sơ nghề nào khớp từ khóa: {' '.join(args)!r}")
            print("Gợi ý: marketing · backend · thiet ke · logistics · giao duc · ke toan")
            return
        for p in sorted(hits, key=lambda x: -x["jd_count"])[:3]:
            print_profile(p)
        if len(hits) > 3:
            print(f"\n  (còn {len(hits) - 3} hồ sơ khác khớp từ khóa này)")
        return

    # Mặc định: tổng quan + 2 ví dụ tương phản
    #   Marketing  — cỡ mẫu lớn (gần 4.000 tin), kỹ năng đặc trưng rõ ràng
    #   Backend    — cỡ mẫu nhỏ hơn nhưng cho thấy tầng vị trí cụ thể chính xác
    print_overview(profiles)
    print("\n" + "=" * W)
    print("  VÍ DỤ CỤ THỂ")
    print("=" * W)
    for key in ("marketing_truyen_thong", "backend developer"):
        q = _fold(key)
        hit = next((p for p in profiles if q in _fold(p["file"])), None)
        if hit:
            print_profile(hit)
    print("\n" + "=" * W)
    print("  Tra nghề khác:  py -3.12 scripts/show_kb_stats.py <từ khóa>")
    print("  Bảng đầy đủ  :  py -3.12 scripts/show_kb_stats.py --all")
    print("=" * W)


if __name__ == "__main__":
    main()
