from pathlib import Path

from src.online.extraction_step2.text_extractor import (
    UnsupportedFileType,
    _chars_to_lines,
    _find_gutter,
    _is_same_row_artifact,
    _looks_char_spaced,
    _order_lines,
    _repair_char_spacing,
    extract_text,
    extract_text_from_bytes,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _char(text, x0, top, size=10.0):
    return {"text": text, "x0": x0, "x1": x0 + size * 0.6, "top": top, "size": size}


def _line(text, x0, x1, top):
    return {"text": text, "x0": x0, "x1": x1, "top": top}


# ── _order_lines / _find_gutter: đúng bug gốc (bullet job B trước header) ──


def test_order_lines_reads_left_column_then_right_column():
    lines = [
        _line("Company A - Job 1", 250, 450, top=10),
        _line("CONTACT", 50, 100, top=15),
        _line("Bullet A1", 250, 480, top=25),
        _line("Email: x@y.com", 50, 150, top=30),
        _line("Bullet B1 (thuoc Company B nhung bi lech thu tu)", 250, 500, top=40),
        _line("Phone: 123", 50, 120, top=45),
        _line("Company B - Job 2", 250, 450, top=60),
        _line("Bullet B2", 250, 480, top=75),
        _line("Skills", 50, 100, top=90),
    ]
    ordered = _order_lines(lines, page_width=600)

    # Cột trái đọc hết trước cột phải.
    left_idx = [ordered.index(t) for t in ("CONTACT", "Email: x@y.com", "Phone: 123", "Skills")]
    right_idx = [
        ordered.index(t)
        for t in (
            "Company A - Job 1",
            "Bullet A1",
            "Bullet B1 (thuoc Company B nhung bi lech thu tu)",
            "Company B - Job 2",
            "Bullet B2",
        )
    ]
    assert max(left_idx) < min(right_idx)


def test_order_lines_falls_back_to_top_order_without_gutter():
    lines = [_line("Line 1", 50, 550, top=10), _line("Line 2", 50, 550, top=25)]
    assert _order_lines(lines, page_width=600) == ["Line 1", "Line 2"]


def test_order_lines_empty_input():
    assert _order_lines([], page_width=600) == []


def test_find_gutter_requires_minimum_lines_per_side():
    lines = [
        _line("Sidebar", 50, 150, top=10),
        _line("Main content that spans most of one column", 250, 500, top=10),
        _line("Main content 2", 250, 500, top=25),
        _line("Main content 3", 250, 500, top=40),
    ]
    assert _find_gutter(lines, page_width=600) is None


def test_find_gutter_rejects_same_row_date_badge_pattern():
    """
    Badge ngày tháng canh phải (vd 'Software Engineer .... June 2024') tạo ra
    nhiều dòng "hẹp" ở cả 2 phía cùng top với dòng bên kia — không phải cột
    thật, không nên bị coi là gutter (xem _is_same_row_artifact).
    """
    lines = []
    for i in range(5):
        top = 10 + i * 20
        lines.append(_line(f"Job title / bullet text {i}", 50, 300, top=top))
        lines.append(_line(f"Jun {2020+i} - Aug {2020+i}", 400, 500, top=top))
    assert _find_gutter(lines, page_width=600) is None


def test_is_same_row_artifact_true_for_paired_lines():
    left = [_line("a", 50, 100, top=t) for t in (10, 20, 30)]
    right = [_line("b", 400, 500, top=t) for t in (10, 20, 30)]
    assert _is_same_row_artifact(left, right) is True


def test_is_same_row_artifact_false_for_independent_columns():
    left = [_line("a", 50, 100, top=t) for t in (10, 20, 30, 40, 50)]
    right = [_line("b", 400, 500, top=t) for t in (16, 34, 56, 74, 95)]
    assert _is_same_row_artifact(left, right) is False


# ── _chars_to_lines: literal space vs gap-based word boundary ─────────────


def test_chars_to_lines_uses_literal_space_as_word_boundary():
    # Font "giãn ký tự": mọi khoảng cách bằng nhau (1.2pt), chỉ ký tự space
    # thật mới đánh dấu ranh giới từ — đây là mẫu tagline Canva/Figma thật.
    chars = []
    x = 50.0
    for ch in "AI ENGINEER":
        chars.append(_char(ch, x, top=10, size=12))
        x += 1.2 if ch == " " else 8.0
    lines = _chars_to_lines(chars)
    assert len(lines) == 1
    assert lines[0]["text"] == "AI ENGINEER"


def test_chars_to_lines_inserts_space_on_large_gap_without_literal_space():
    # PDF kiểu LaTeX/Overleaf: không có ký tự space thật, chỉ có khoảng
    # cách lớn hơn giữa 2 từ so với khoảng cách bình thường giữa các chữ.
    chars = [
        _char("o", 50, top=10, size=10),
        _char("f", 56, top=10, size=10),
        _char("W", 70, top=10, size=10),  # gap lớn (14pt) → ranh giới từ
        _char("a", 76, top=10, size=10),
    ]
    lines = _chars_to_lines(chars)
    assert lines[0]["text"] == "of Wa"


def test_chars_to_lines_splits_same_top_columns_into_separate_lines():
    chars = [_char(ch, 50 + i * 6, top=10, size=10) for i, ch in enumerate("CONTACT")]
    chars += [_char(ch, 300 + i * 6, top=10, size=10) for i, ch in enumerate("SUMMARY")]
    lines = _chars_to_lines(chars)
    texts = [l["text"] for l in lines]
    assert texts == ["CONTACT", "SUMMARY"]


def test_chars_to_lines_empty_input():
    assert _chars_to_lines([]) == []


# ── _looks_char_spaced / _repair_char_spacing ──────────────────────────────


def test_repair_char_spacing_fixes_genuinely_spaced_text():
    spaced = "A I  E N G I N E E R  |   D A T A  E N G I N E E R  |"
    assert _looks_char_spaced(spaced) is True
    assert _repair_char_spacing(spaced) == "AI ENGINEER | DATA ENGINEER |"


def test_looks_char_spaced_ignores_icon_glyph_lines():
    # Dòng contact info xen icon (Font Awesome, mỗi icon 1 ký tự đơn) không
    # phải char-spacing thật — trước đây bị heuristic cũ vá nhầm.
    icon_line = " Espoo, Finland  toducminh@proton.me  akihakune.com"
    assert _looks_char_spaced(icon_line) is False
    assert _repair_char_spacing(icon_line) == icon_line


def test_looks_char_spaced_requires_minimum_tokens():
    assert _looks_char_spaced("A B C") is False


# ── Integration: real PDF fixtures qua extract_text ────────────────────────


def test_two_column_pdf_reads_sidebar_then_main_column_in_order():
    text = extract_text(FIXTURES / "two_column_cv.pdf")

    # Header job B phải xuất hiện TRƯỚC bullet của job B (đây chính là bug
    # gốc: pypdf trả bullet job B trước header vì đọc theo content-stream
    # order thay vì vị trí hiển thị).
    assert text.index("Company B - Data Analyst") < text.index("Fixed bug B1")
    assert text.index("Company B - Data Analyst") < text.index("Fixed bug B2")

    # Cột trái (sidebar) đọc hết trước cột phải (nội dung chính).
    assert text.index("Docker") < text.index("PROFESSIONAL SUMMARY")


def test_single_column_pdf_keeps_natural_top_to_bottom_order():
    text = extract_text(FIXTURES / "single_column_cv.pdf")
    expected_order = [
        "JOHN DOE",
        "SUMMARY",
        "EXPERIENCE",
        "Acme Corp - Backend Engineer",
        "Globex Inc - Software Engineer",
    ]
    indices = [text.index(s) for s in expected_order]
    assert indices == sorted(indices)


def test_extract_text_from_bytes_rejects_unsupported_extension():
    try:
        extract_text_from_bytes(b"hello", "resume.doc")
        assert False, "phải raise UnsupportedFileType"
    except UnsupportedFileType:
        pass


def test_extract_text_from_bytes_handles_markdown():
    md = b"# John Doe\n\n- Python\n- SQL\n"
    text = extract_text_from_bytes(md, "resume.md")
    assert "John Doe" in text
    assert "#" not in text
