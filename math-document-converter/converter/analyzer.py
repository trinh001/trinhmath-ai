from __future__ import annotations

from pathlib import Path


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def analyze_file(path: Path) -> tuple[str, list[dict]]:
    """Phân loại ở mức trang: trích text trước, OCR sau."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "IMAGE", [{"number": 1, "classification": "SCAN_PAGE", "text": ""}]
    if suffix == ".docx":
        # Converter V1 không OCR Word; TrinhMath đã có luồng đọc OOXML trực tiếp.
        return "DOCX", [{"number": 1, "classification": "TEXT_PAGE", "text": "DOCX sẽ được trích trực tiếp ở Milestone 2."}]
    if suffix != ".pdf":
        raise ValueError("Chỉ hỗ trợ PDF, DOCX, PNG, JPG, JPEG và WebP.")
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError("Thiếu pypdf. Hãy chạy CAI_DAT_CONVERTER.bat.") from error
    reader = PdfReader(str(path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        # Một đoạn text đủ dài được giữ nguyên, không rasterize/OCR lại.
        classification = "TEXT_PAGE" if len(text) >= 40 else "SCAN_PAGE"
        pages.append({"number": index, "classification": classification, "text": text})
    return "PDF", pages


def collect_supported_files(folder: Path) -> list[Path]:
    return [path for path in Path(folder).rglob("*") if path.is_file() and path.suffix.lower() in {".pdf", ".docx", *IMAGE_SUFFIXES}]
