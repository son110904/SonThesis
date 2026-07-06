"""
occupation_loader.py – Nạp & tra cứu Occupation Profile (Bước 6).

Đọc các file JSON trong data/occupation_profiles/. Key ổn định = tên file
(ASCII, an toàn cho HTTP), display name suy ra từ trường 'occupation'.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from src.config import OCCUPATION_PROFILES_DIR

logger = logging.getLogger(__name__)


class OccupationNotFound(KeyError):
    """Raise khi không tìm thấy occupation theo key."""


def _display_name(occupation_field: str) -> str:
    """'công_nghệ_thông_tin_kỹ_thuật_số' → 'Công nghệ thông tin kỹ thuật số'."""
    name = occupation_field.replace("_", " ").strip()
    return name[:1].upper() + name[1:] if name else occupation_field


@lru_cache(maxsize=1)
def _load_all() -> dict[str, dict]:
    """Nạp toàn bộ profile vào cache. Key = tên file (không đuôi)."""
    profiles_dir = Path(OCCUPATION_PROFILES_DIR)
    if not profiles_dir.exists():
        logger.error(f"Thư mục occupation profiles không tồn tại: {profiles_dir}")
        return {}

    result: dict[str, dict] = {}
    for path in sorted(profiles_dir.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            key = path.stem
            data["_key"] = key
            data["_display"] = _display_name(data.get("occupation", key))
            result[key] = data
        except Exception as e:  # noqa: BLE001
            logger.error(f"Lỗi đọc occupation profile {path.name}: {e}")

    logger.info(f"Nạp {len(result)} occupation profiles từ {profiles_dir}")
    return result


def list_occupations() -> list[dict]:
    """
    Danh sách nghề cho dropdown frontend (hỗ trợ 2 cấp: lĩnh vực → vị trí).

    Mỗi item có thêm:
        parent_key/parent_display: lĩnh vực cha. Với profile gốc (lĩnh vực) thì
            parent_key = chính nó. Với sub-occupation thì = `_parent`.
        sub_display: tên vị trí con (None nếu là lĩnh vực gốc).
        is_sub:      True nếu là vị trí con.

    Returns:
        List[dict] sắp theo display.
    """
    all_profiles = _load_all()
    items = []
    for key, prof in all_profiles.items():
        parent_key = prof.get("_parent")
        is_sub = bool(parent_key)
        if is_sub:
            parent_display = prof.get("_parent_display") or _display_name(parent_key)
            sub_display = prof.get("_sub_display") or prof["_display"]
        else:
            parent_key, parent_display, sub_display = key, prof["_display"], None
        items.append({
            "key": key,
            "display": prof["_display"],
            "core_skill_count": len(prof.get("core_skills", {})),
            "parent_key": parent_key,
            "parent_display": parent_display,
            "sub_display": sub_display,
            "is_sub": is_sub,
        })
    return sorted(items, key=lambda x: x["display"])


def get_occupation(key: str) -> dict:
    """
    Lấy 1 Occupation Profile theo key.

    Raises:
        OccupationNotFound: Nếu key không tồn tại.
    """
    profiles = _load_all()
    if key not in profiles:
        raise OccupationNotFound(
            f"Không tìm thấy occupation '{key}'. Có sẵn: {sorted(profiles.keys())}"
        )
    return profiles[key]
