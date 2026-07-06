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

    def _pill(s: str) -> str:
        return f"<span class='badge {cls}'>{html.escape(str(s))}</span>"

    if max_items and len(skills) > max_items:
        shown, rest = skills[:max_items], skills[max_items:]
    else:
        shown, rest = skills, []

    pills = "".join(_pill(s) for s in shown)

    # Phần dư gói trong <details> — badge "+N" trở thành nút bấm xổ ra (native HTML,
    # không cần JS), click để hiện toàn bộ kỹ năng còn lại.
    more = ""
    if rest:
        rest_pills = "".join(_pill(s) for s in rest)
        more = (
            "<details class='badge-more'>"
            f"<summary class='badge badge-more-toggle'>+{len(rest)} kỹ năng khác</summary>"
            f"<div class='badge-wrap' style='margin-top:.55rem'>{rest_pills}</div>"
            "</details>"
        )

    st.markdown(f"<div class='badge-wrap'>{pills}</div>{more}", unsafe_allow_html=True)
