"""
dedupe_profile_skills.py – Gộp các biến thể trùng của cùng một kỹ năng trong
                           Occupation Profile đã build.

VẤN ĐỀ: occupation_profile_builder.py dùng CHUỖI THÔ làm khóa đếm tần suất
(dòng 83-84), nên "Kế toán" / "kế toán" / "Kế Toán" thành 3 mục riêng. Hệ quả:
danh sách kỹ năng hiển thị bị lặp, và trọng số của kỹ năng đó bị phân tán.

CÁCH SỬA Ở ĐÂY (vá tại chỗ, KHÔNG chạy lại offline pipeline):
    - Gom biến thể theo ĐÚNG khóa mà tầng đối sánh dùng:
      canonicalize_skill(x).lower()  —  xem semantic_skill_match._normalize
    - Trọng số sau gộp = MAX của các biến thể (không cộng dồn).
      Chọn max vì trọng số đã được min-max chuẩn hóa về [0,1]; cộng dồn sẽ
      vượt biên và làm lệch phân phối → hỏng luôn ngưỡng Otsu 0,35 đã công bố.
    - Phân lại Core/Optional theo ngưỡng 0,35 trên trọng số sau gộp.
    - KHÔNG đụng: embedding, responsibilities, occupation, _meta.

LƯU Ý: việc gộp làm mẫu số Weighted Skill Score nhỏ lại (hết đếm trùng), nên
điểm kỹ năng của ứng viên sẽ NHÍCH LÊN chút ít. Đây là sửa đúng, không phải
tác dụng phụ ngoài ý muốn.

Chạy:
    py -3.12 scripts/dedupe_profile_skills.py            # dry-run, chỉ báo cáo
    py -3.12 scripts/dedupe_profile_skills.py --apply    # ghi đè (có backup)
"""

from __future__ import annotations

import glob
import json
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.offline.skill_normalize import canonicalize_skill  # noqa: E402

PROFILES = ROOT / "data" / "occupation_profiles"
CORE_THRESHOLD = 0.35          # khớp _DEFAULT_THRESHOLD ở skill_weight_calculator


def _w(v):
    return v["weight"] if isinstance(v, dict) else v


def _pick_display(variants: list[str]) -> str:
    """Chọn dạng hiển thị: ưu tiên bản canonicalize có chữ hoa đầu."""
    forms = [canonicalize_skill(v) or v for v in variants]
    for f in forms:
        if f[:1].isupper():
            return f
    return forms[0]


def dedupe_profile(d: dict) -> tuple[dict, dict, list]:
    """Trả (core_mới, optional_mới, danh_sách_nhóm_đã_gộp)."""
    merged: dict[str, dict] = {}
    for src in (d.get("optional_skills", {}), d.get("core_skills", {})):
        for name, val in src.items():
            key = (canonicalize_skill(name) or name).strip().lower()
            slot = merged.setdefault(key, {"variants": [], "weight": 0.0})
            slot["variants"].append(name)
            slot["weight"] = max(slot["weight"], float(_w(val)))

    core, optional, groups = {}, {}, []
    for key, slot in merged.items():
        display = _pick_display(slot["variants"])
        weight = round(slot["weight"], 4)
        (core if weight >= CORE_THRESHOLD else optional)[display] = weight
        if len(slot["variants"]) > 1:
            groups.append((display, sorted(set(slot["variants"]))))

    srt = lambda dd: dict(sorted(dd.items(), key=lambda kv: -kv[1]))  # noqa: E731
    return srt(core), srt(optional), groups


def main() -> None:
    apply = "--apply" in sys.argv
    files = sorted(glob.glob(str(PROFILES / "*.json")))
    if not files:
        raise SystemExit(f"Không thấy hồ sơ nghề trong {PROFILES}")

    if apply:
        dest = PROFILES.parent / f"occupation_profiles_predupe_{datetime.now():%H%M%S}"
        shutil.copytree(PROFILES, dest)
        print(f"Đã backup {len(files)} file -> {dest}\n")

    tot_before = tot_after = 0
    changed_files = 0
    detail = []

    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        n_before = len(d.get("core_skills", {})) + len(d.get("optional_skills", {}))
        core, optional, groups = dedupe_profile(d)
        n_after = len(core) + len(optional)

        tot_before += n_before
        tot_after += n_after
        if groups:
            changed_files += 1
            detail.append((Path(f).stem, d["occupation"], n_before, n_after, groups))

        if apply and groups:
            d["core_skills"] = core
            d["optional_skills"] = optional
            d.setdefault("_meta", {})["core_skill_count"] = len(core)
            d["_meta"]["optional_skill_count"] = len(optional)
            json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("=" * 76)
    print("DRY-RUN — chưa ghi gì" if not apply else "ĐÃ ÁP DỤNG")
    print("=" * 76)
    print(f"Hồ sơ có kỹ năng trùng : {changed_files}/{len(files)}")
    print(f"Tổng mục kỹ năng       : {tot_before} -> {tot_after}  (giảm {tot_before - tot_after})")

    print("\n8 hồ sơ bị gộp nhiều nhất:")
    for stem, name, nb, na, groups in sorted(detail, key=lambda r: -(r[2] - r[3]))[:8]:
        print(f"\n  {name[:60]}   ({nb} -> {na})")
        for display, variants in groups[:5]:
            print(f"      {variants}  ->  {display!r}")
        if len(groups) > 5:
            print(f"      … còn {len(groups) - 5} nhóm nữa")

    if not apply:
        print("\n" + "=" * 76)
        print("Chạy lại với --apply để ghi đè (script tự backup trước).")


if __name__ == "__main__":
    main()
