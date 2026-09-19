from pathlib import Path

from app import rendered_pdf_page_image_path


def test_detects_two_digit_poppler_page_suffix(tmp_path):
    prefix = tmp_path / "page_render"
    two_digit = Path(f"{prefix}-01.png")
    two_digit.write_bytes(b"x" * 513)

    assert rendered_pdf_page_image_path(prefix, 1) == two_digit


def test_prefers_three_digit_suffix_and_rejects_tiny_output(tmp_path):
    prefix = tmp_path / "page_render"
    three_digit = Path(f"{prefix}-001.png")
    two_digit = Path(f"{prefix}-01.png")
    three_digit.write_bytes(b"x" * 513)
    two_digit.write_bytes(b"x")

    assert rendered_pdf_page_image_path(prefix, 1) == three_digit
