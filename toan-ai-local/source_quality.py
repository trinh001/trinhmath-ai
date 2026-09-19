"""Phát hiện dấu hiệu Word/OCR làm mất dữ kiện trước khi tạo bản nháp cục bộ."""

from __future__ import annotations

import re


def source_content_quality_issues(candidate: object) -> list[str]:
    """Trả về cờ bảo thủ; không tự sửa hay suy đoán công thức đã mất."""
    if not isinstance(candidate, dict):
        return ["Candidate không đúng định dạng."]
    question = str(candidate.get("question_text") or "").strip()
    solution = str(candidate.get("solution_text") or "").strip()
    issues = []
    if not question:
        issues.append("Thiếu đề bài nguồn.")
    if not solution:
        issues.append("Thiếu lời giải nguồn.")
    if re.search(r"(?im)\b(?:gọi|ký hiệu)\s+(?:lần|số|các)\b", solution):
        issues.append("Lời giải có dấu hiệu mất biến hoặc ký hiệu sau từ 'Gọi/Ký hiệu'.")
    if re.search(r"(?im)\b(?:là|bằng)\s*\.\s*(?:$|\n)", solution):
        issues.append("Lời giải có chỗ kết thúc bằng 'là/bằng .' nghi mất công thức.")
    if re.search(r"(?im)\bta\s+có\s*:\s*[,.;…]+", solution):
        issues.append("Lời giải có dòng 'Ta có' không còn biểu thức theo sau.")
    if solution.count("\\left") != solution.count("\\right"):
        issues.append("Công thức LaTeX có cặp \\left/\\right không cân bằng.")
    if solution.count("$") % 2:
        issues.append("Công thức LaTeX có dấu $ không cân bằng.")
    return issues
