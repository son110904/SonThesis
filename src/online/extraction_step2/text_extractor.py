"""
text_extractor.py – Trích xuất văn bản thô từ CV (PDF hoặc DOCX).

Bước 2 của Online Pipeline.

Output: raw_text (str)
"""

from __future__ import annotations

import io
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: set[str] = {".pdf", ".docx", ".md"}


def _looks_char_spaced(line: str) -> bool:
    """
    True nếu dòng bị "giãn ký tự" — mỗi chữ cái cách nhau 1 space
    (vd 'P y t h o n'), thường gặp ở PDF xuất từ Canva/Figma.

    Heuristic: ≥45% token (tách bởi 1 space) là ký tự đơn.
    """
    tokens = [t for t in line.split(" ") if t != ""]
    if len(tokens) < 8:
        return False
    single = sum(1 for t in tokens if len(t) == 1)
    return single / len(tokens) >= 0.45


def _repair_char_spacing(text: str) -> str:
    """
    Sửa text bị giãn ký tự. Quy luật của loại PDF này:
        - trong 1 TỪ: các ký tự cách nhau 1 space  → 'P y t h o n'
        - giữa 2 TỪ : cách nhau 2+ space           → 'P y t h o n   F a s t A P I'
    Nên: tách dòng theo run 2+ space (ranh giới từ), rồi bỏ space đơn bên trong.
    Chỉ áp dụng cho dòng thực sự bị giãn, dòng bình thường giữ nguyên.
    """
    out: list[str] = []
    fixed_any = False
    for line in text.split("\n"):
        if _looks_char_spaced(line):
            words = re.split(r" {2,}", line.strip())
            words = [w.replace(" ", "") for w in words]
            out.append(" ".join(w for w in words if w))
            fixed_any = True
        else:
            out.append(line)
    if fixed_any:
        logger.info("Phát hiện & sửa PDF bị giãn ký tự (char-spaced).")
    return "\n".join(out)


class UnsupportedFileType(ValueError):
    """Raise khi file không phải PDF/DOCX."""


def _extract_pdf(data: bytes) -> str:
    """Trích text từ PDF bytes bằng pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception as e:  # noqa: BLE001 - 1 page lỗi không nên hỏng cả file
            logger.warning(f"Lỗi trích 1 trang PDF: {e}")
    return "\n".join(pages)


def _extract_md(data: bytes) -> str:
    """
    Trích text từ Markdown bytes. Bỏ cú pháp MD cơ bản để regex skill chạy sạch
    (heading #, bullet -/*, bold **, code `, link [text](url) → text).
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("latin-1", errors="ignore")

    # [text](url) → text  ; ![alt](url) → alt
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # bỏ ký tự cú pháp đầu/giữa dòng, giữ nội dung
    text = re.sub(r"^[ \t]*#{1,6}\s*", "", text, flags=re.MULTILINE)  # heading
    text = re.sub(r"^[ \t]*[-*+]\s+", "", text, flags=re.MULTILINE)   # bullet
    text = re.sub(r"^[ \t]*>\s?", "", text, flags=re.MULTILINE)        # blockquote
    text = text.replace("**", "").replace("__", "").replace("`", "")
    return text


def _extract_docx(data: bytes) -> str:
    """Trích text từ DOCX bytes bằng python-docx (cả paragraph + bảng)."""
    from docx import Document

    doc = Document(io.BytesIO(data))
    parts: list[str] = [p.text for p in doc.paragraphs if p.text.strip()]

    # Lấy thêm text trong bảng (CV hay dùng bảng để layout)
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))

    return "\n".join(parts)


def extract_text_from_bytes(data: bytes, filename: str) -> str:
    """
    Trích văn bản thô từ nội dung file (bytes).

    Args:
        data:     Nội dung file dạng bytes.
        filename: Tên file (để xác định loại qua phần mở rộng).

    Returns:
        Văn bản thô đã trích, đã strip.

    Raises:
        UnsupportedFileType: Nếu không phải PDF/DOCX.
    """
    ext = Path(filename).suffix.lower()
    if ext == ".doc":
        # .doc (Word nhị phân cũ) không đọc được bằng Python thuần → hướng dẫn chuyển đổi.
        raise UnsupportedFileType(
            "Định dạng .doc (Word cũ) không được hỗ trợ. "
            "Vui lòng lưu lại dưới dạng .docx, PDF hoặc .md rồi tải lên."
        )
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileType(
            f"Định dạng '{ext}' không hỗ trợ. Chỉ chấp nhận: PDF, DOCX, Markdown (.md)."
        )

    if ext == ".pdf":
        text = _extract_pdf(data)
        text = _repair_char_spacing(text)  # vá PDF giãn ký tự (Canva/Figma…)
    elif ext == ".md":
        text = _extract_md(data)
    else:
        text = _extract_docx(data)

    text = text.strip()
    logger.info(f"Trích xuất '{filename}' ({ext}) → {len(text)} ký tự")
    if not text:
        logger.warning(f"File '{filename}' trích ra rỗng — có thể là PDF scan ảnh.")
    return text


def extract_text(file_path: str | Path) -> str:
    """
    Trích văn bản thô từ đường dẫn file trên đĩa.

    Args:
        file_path: Đường dẫn tới file PDF/DOCX.

    Returns:
        Văn bản thô đã trích.

    Raises:
        FileNotFoundError:   Nếu file không tồn tại.
        UnsupportedFileType: Nếu không phải PDF/DOCX.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {path}")
    data = path.read_bytes()
    return extract_text_from_bytes(data, path.name)
