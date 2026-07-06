"""
clean_occupation_profiles.py – Dọn biến thể skill trùng trong 16 profile có sẵn.

Xử lý "Lỗ hổng chất lượng data": gộp 'REST API'/'REST API API'/'REST API APIs',
'Node.js'/'Node.JavaScript', 'erp'/'erP'/'ERP', và các biến thể hoa/thường
tiếng Việt ('Kế toán'/'kế toán'/'Kế Toán') về một entry duy nhất.

Cách làm:
    1. Backup toàn bộ profile sang data/occupation_profiles_backup/ (1 lần).
    2. Học display chuẩn từ TẦN SUẤT xuất hiện trên cả 16 profile (data-driven).
    3. Với mỗi profile: dedupe core_skills & optional_skills (giữ weight lớn nhất),
       gỡ skill đã nằm trong core ra khỏi optional, cập nhật _meta đếm lại.
    4. Ghi đè file (KHÔNG đụng `embedding`).

LƯU Ý: core_skills đổi → văn bản embed đổi nhẹ. Sau khi chạy script này nên chạy
    `python reembed_occupations.py` để đồng bộ lại occupation_embedding.

Chạy:  python scripts/clean_occupation_profiles.py
       python scripts/clean_occupation_profiles.py --dry-run   (chỉ in, không ghi)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import OCCUPATION_PROFILES_DIR
from src.offline.skill_normalize import build_display_preference, dedupe_weighted_skills


def _load_profiles(profiles_dir: Path) -> dict[Path, dict]:
    return {
        f: json.load(open(f, encoding="utf-8"))
        for f in sorted(profiles_dir.glob("*.json"))
    }


def clean_profile(profile: dict, display_pref: dict[str, str]) -> tuple[dict, dict]:
    """
    Dedupe core/optional của 1 profile. Trả (profile_đã_sửa, thống_kê).
    """
    core_raw = profile.get("core_skills", {})
    opt_raw = profile.get("optional_skills", {})

    core = dedupe_weighted_skills(core_raw, display_pref, merge="max")
    opt = dedupe_weighted_skills(opt_raw, display_pref, merge="max")

    # Skill đã là core thì bỏ khỏi optional (core quan trọng hơn).
    core_lower = {k.lower() for k in core}
    opt = {k: v for k, v in opt.items() if k.lower() not in core_lower}

    stats = {
        "core_before": len(core_raw), "core_after": len(core),
        "opt_before": len(opt_raw), "opt_after": len(opt),
    }

    profile["core_skills"] = core
    profile["optional_skills"] = opt
    meta = profile.setdefault("_meta", {})
    meta["core_skill_count"] = len(core)
    meta["optional_skill_count"] = len(opt)
    meta["cleaned"] = True
    return profile, stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Chỉ in, không ghi file")
    args = parser.parse_args()

    profiles_dir = Path(OCCUPATION_PROFILES_DIR)
    raw = _load_profiles(profiles_dir)
    if not raw:
        print(f"Không tìm thấy profile trong {profiles_dir}")
        return

    # Backup 1 lần (không ghi đè backup cũ để giữ bản gốc đầu tiên).
    backup_dir = profiles_dir.parent / "occupation_profiles_backup"
    if not args.dry_run and not backup_dir.exists():
        shutil.copytree(profiles_dir, backup_dir)
        print(f"Đã backup → {backup_dir}")

    # Học display chuẩn từ cả corpus (core + optional của mọi profile).
    skill_iterables = []
    for d in raw.values():
        skill_iterables.append(list(d.get("core_skills", {})) + list(d.get("optional_skills", {})))
    display_pref = build_display_preference(skill_iterables)

    total_removed = 0
    for f, d in raw.items():
        cleaned, st = clean_profile(d, display_pref)
        removed = (st["core_before"] + st["opt_before"]) - (st["core_after"] + st["opt_after"])
        total_removed += removed
        flag = "" if removed == 0 else f"  (-{removed} biến thể trùng)"
        print(
            f"  {f.name:55} core {st['core_before']:>3}->{st['core_after']:<3} "
            f"opt {st['opt_before']:>3}->{st['opt_after']:<3}{flag}"
        )
        if not args.dry_run:
            json.dump(cleaned, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"\nTổng biến thể trùng đã gộp: {total_removed}")
    if args.dry_run:
        print("(dry-run — chưa ghi file nào)")
    else:
        print("Xong. Nên chạy tiếp:  python reembed_occupations.py  để đồng bộ embedding.")


if __name__ == "__main__":
    main()
