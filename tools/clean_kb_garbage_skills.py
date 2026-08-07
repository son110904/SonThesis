"""
clean_kb_garbage_skills.py – Dọn skill rác khỏi Occupation Knowledge Base tại chỗ.

Bối cảnh:
    Các file data/occupation_profiles/*.json được build bằng bản regex CŨ của
    src/offline/skill_extraction_step2/extractor.py, khi đó nhiều SKILL_PATTERNS
    thiếu word boundary nên khớp cả substring nằm giữa từ khác:

        'vaS'   ← pattern VAS khớp "Ja(vaS)cript"
        'rf'    ← pattern RF  khớp "pe(rf)orm", "su(rf)ace"
        'cam'   ← pattern CAM khớp "(cam) kết", "(cam)era"

    Riêng 'tiện' và 'Hàn' là lỗi KHÁC: pattern đã có \\b sẵn, nhưng tiếng Việt
    viết rời từng âm tiết nên \\b vô tác dụng — "tiện" khớp trong "tiện ích /
    thuận tiện / tiện nghi", "Hàn" khớp trong "Hàn Quốc / tiếng Hàn".

    Ngoài ra 'Next.JavaScript' / 'Vue.JavaScript' là lỗi thay thế chuỗi "js"→
    "JavaScript" (đã có tiền lệ Node.JavaScript trong ALIAS_MAP) — đổi tên về
    dạng chuẩn thay vì xoá.

Script này CHỈ sửa core_skills / optional_skills và _meta đếm lại; KHÔNG đụng
tới `embedding` (re-embed cần Python 3.12 + torch lành lặn, xem README).

Chạy thử:  python tools/clean_kb_garbage_skills.py
Áp dụng:   python tools/clean_kb_garbage_skills.py --apply
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

KB_DIR = ROOT / "data" / "occupation_profiles"

# Khớp CHÍNH XÁC theo chuỗi (không lowercase) để không đụng nhầm biến thể viết
# hoa hợp lệ — vd 'LMS' của training_specialist, 'CAD' của cơ khí.
GARBAGE_KEYS: set[str] = {"cam", "vaS", "rf", "tiện", "Hàn"}

# Đổi tên về dạng chuẩn (giữ nguyên weight; nếu trùng đích thì lấy weight lớn hơn).
RENAME_KEYS: dict[str, str] = {
    "Next.JavaScript": "Next.js",
    "Vue.JavaScript": "Vue.js",
}


def clean_skill_dict(skills: dict) -> tuple[dict, list[str], list[str]]:
    """Trả về (dict đã dọn, danh sách key bị xoá, danh sách mô tả đổi tên)."""
    removed: list[str] = []
    renamed: list[str] = []
    out: dict = {}

    for key, weight in skills.items():
        if key in GARBAGE_KEYS:
            removed.append(f"{key}={weight:.3f}")
            continue
        target = RENAME_KEYS.get(key)
        if target:
            renamed.append(f"{key} -> {target}")
            # Trùng đích: giữ weight lớn hơn (cùng quy ước merge='max' của
            # dedupe_weighted_skills trong skill_normalize.py).
            out[target] = max(out.get(target, 0.0), weight)
            continue
        out[key] = max(out[key], weight) if key in out else weight

    # Giữ thứ tự giảm dần theo weight như file gốc.
    out = dict(sorted(out.items(), key=lambda kv: kv[1], reverse=True))
    return out, removed, renamed


def process(path: Path, apply: bool) -> dict | None:
    data = json.loads(path.read_text(encoding="utf-8"))

    core, core_rm, core_rn = clean_skill_dict(data.get("core_skills", {}))
    opt, opt_rm, opt_rn = clean_skill_dict(data.get("optional_skills", {}))

    if not (core_rm or opt_rm or core_rn or opt_rn):
        return None

    data["core_skills"] = core
    data["optional_skills"] = opt

    meta = data.setdefault("_meta", {})
    meta["core_skill_count"] = len(core)
    meta["optional_skill_count"] = len(opt)
    # Ghi dấu để lần sau biết file đã được vá thủ công, embedding CHƯA sinh lại.
    meta["skills_cleaned_at"] = "2026-08-06"
    meta["skills_cleaned_note"] = (
        "Xoá skill rác do regex thiếu word-boundary (cam/vaS/rf) và do âm tiết "
        "tiếng Việt trùng từ khoá (tiện/Hàn); chuẩn hoá Next/Vue.JavaScript. "
        "embedding GIỮ NGUYÊN — chạy lại offline pipeline để đồng bộ hoàn toàn."
    )

    if apply:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return {
        "file": path.name,
        "core_removed": core_rm,
        "opt_removed": opt_rm,
        "renamed": core_rn + opt_rn,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="Ghi thay đổi xuống file (mặc định chỉ chạy thử).")
    args = ap.parse_args()

    files = sorted(KB_DIR.glob("*.json"))
    if not files:
        raise SystemExit(f"Không tìm thấy profile nào trong {KB_DIR}")

    reports = [r for r in (process(f, args.apply) for f in files) if r]

    total_rm = sum(len(r["core_removed"]) + len(r["opt_removed"]) for r in reports)
    total_rn = sum(len(r["renamed"]) for r in reports)

    for r in reports:
        print(f"\n{r['file']}")
        for x in r["core_removed"]:
            print(f"    - CORE xoá : {x}")
        for x in r["opt_removed"]:
            print(f"    - opt  xoá : {x}")
        for x in r["renamed"]:
            print(f"    ~ đổi tên  : {x}")

    mode = "ĐÃ GHI" if args.apply else "CHẠY THỬ (chưa ghi)"
    print(f"\n=== {mode} ===")
    print(f"  Profile bị ảnh hưởng : {len(reports)}/{len(files)}")
    print(f"  Tổng skill xoá       : {total_rm}")
    print(f"  Tổng skill đổi tên   : {total_rn}")
    if not args.apply:
        print("\n  Chạy lại với --apply để ghi xuống file.")


if __name__ == "__main__":
    main()
