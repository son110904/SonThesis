"""
badges.py – Badge kỹ năng (matched xanh / missing đỏ).

Theo spec: Matched Skills = badge xanh, Missing Skills = badge đỏ.
Dùng HTML + class CSS đã định nghĩa trong styling.py.
"""

from __future__ import annotations

import html

_KIND_CLASS = {
    "matched": "badge-matched",
    "missing": "badge-missing",
    "muted": "badge-muted",
}


def render_skill_badges(
    skills: list[str],
    kind: str = "matched",
    max_items: int | None = None,
    empty_text: str = "(không có)",
) -> None:
    """
    Render danh sách kỹ năng dạng badge pill.

    Args:
        skills:    Danh sách kỹ năng.
        kind:      'matched' | 'missing' | 'muted'.
        max_items: Giới hạn số badge hiển thị (None = tất cả).
        empty_text: Text khi rỗng.
    """
    import streamlit as st

    cls = _KIND_CLASS.get(kind, "badge-muted")

    if not skills:
        st.markdown(f"<span class='hint'>{html.escape(empty_text)}</span>", unsafe_allow_html=True)
        return

    shown = skills[:max_items] if max_items else skills
    pills = "".join(
        f"<span class='badge {cls}'>{html.escape(str(s))}</span>" for s in shown
    )
    extra = ""
    if max_items and len(skills) > max_items:
        extra = f"<span class='badge badge-muted'>+{len(skills) - max_items}</span>"

    st.markdown(f"<div class='badge-wrap'>{pills}{extra}</div>", unsafe_allow_html=True)
