"""
clean_occupation_profiles.py – Dọn biến thể skill + lọc cross-domain noise.

Xử lý hai vấn đề:
    1. Biến thể trùng: gộp 'REST API'/'REST API API', 'Node.js'/'Node.JavaScript',
       'erp'/'erP'/'ERP', hoa/thường tiếng Việt về một entry duy nhất.
    2. Cross-domain noise: loại skill không liên quan domain (CNTT/software engineer
       không cần "Chăm sóc khách hàng", "CNC", "Kế toán", "Telesales"...).
       Blacklist nằm trong SKILL_BLACKLIST (skill_normalize.py).

Cách làm:
    1. Backup toàn bộ profile sang data/occupation_profiles_backup/ (1 lần).
    2. Học display chuẩn từ TẦN SUẤT xuất hiện trên corpus (data-driven).
    3. Với mỗi profile: lọc blacklist → dedupe core/optional → gỡ core khỏi optional.
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
from src.offline.skill_normalize import (
    is_blacklisted,
    build_display_preference,
    canonicalize_skill,
    dedupe_weighted_skills,
)


def _load_profiles(profiles_dir: Path) -> dict[Path, dict]:
    return {
        f: json.load(open(f, encoding="utf-8"))
        for f in sorted(profiles_dir.glob("*.json"))
    }


def clean_profile(profile: dict, display_pref: dict[str, str], domain_key: str = "") -> tuple[dict, dict]:
    """
    Lọc blacklist → dedupe core/optional của 1 profile. Trả (profile_đã_sửa, thống_kê).
    """
    core_orig = profile.get("core_skills", {})
    opt_orig = profile.get("optional_skills", {})

    # 1. Lọc blacklist (giữ weight, không thay đổi trọng số).
    core_raw = {k: v for k, v in core_orig.items() if not is_blacklisted(k, domain_key)}
    opt_raw = {k: v for k, v in opt_orig.items() if not is_blacklisted(k, domain_key)}

    # 2. Dedup
    core = dedupe_weighted_skills(core_raw, display_pref, merge="max")
    opt = dedupe_weighted_skills(opt_raw, display_pref, merge="max")

    # Skill đã là core thì bỏ khỏi optional (core quan trọng hơn).
    core_lower = {k.lower() for k in core}
    opt = {k: v for k, v in opt.items() if k.lower() not in core_lower}

    stats = {
        "core_before": len(core_orig), "core_after": len(core),
        "opt_before": len(opt_orig), "opt_after": len(opt),
        "blacklist_removed": (len(core_orig) - len(core_raw)) + (len(opt_orig) - len(opt_raw)),
    }

    profile["core_skills"] = core
    profile["optional_skills"] = opt
    meta = profile.setdefault("_meta", {})
    meta["core_skill_count"] = len(core)
    meta["optional_skill_count"] = len(opt)
    meta["cleaned"] = True
    return profile, stats


def main() -> None:
    # Windows CP1252 không encode được tiếng Việt → buộc stdout về UTF-8.
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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
        cleaned, st = clean_profile(d, display_pref, f.stem)
        removed = (st["core_before"] + st["opt_before"]) - (st["core_after"] + st["opt_after"])
        total_removed += removed
        bl = st.get("blacklist_removed", 0)
        flags = []
        if removed > 0:
            flags.append(f"-{removed} trùng")
        if bl > 0:
            flags.append(f"-{bl} blacklist")
        flag_str = "  (" + ", ".join(flags) + ")" if flags else ""
        print(
            f"  {f.name:55} core {st['core_before']:>3}->{st['core_after']:<3} "
            f"opt {st['opt_before']:>3}->{st['opt_after']:<3}{flag_str}"
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
