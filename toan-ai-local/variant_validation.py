"""Các hàng rào thuần dữ liệu trước khi phát hành câu cho học sinh.

Module này không đọc file, không gọi AI và không thay đổi variant. Nhờ vậy nó có
thể được test độc lập, đồng thời `app.py` vẫn giữ các hàm public cũ để tương
thích với luồng hiện có.
"""

from __future__ import annotations

import re
import unicodedata


def normalize_text(value: object) -> str:
    """Chuẩn hóa tiếng Việt đủ để so khớp nội dung, không sửa dữ liệu gốc."""
    text = str(value or "")
    return "".join(
        char for char in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(char) != "Mn"
    ).replace("đ", "d")


def explicit_solution_answer_labels(solution: object) -> set[str]:
    """Đọc nhãn đáp án chỉ khi lời giải ghi theo mẫu rõ ràng, một dòng riêng."""
    matches = re.findall(
        r"(?im)(?:^|\n)\s*đáp\s*án(?:\s+đúng)?\s*[:\-]?\s*\(?([A-D])\)?\s*(?:[\.;:]|$)",
        str(solution or ""),
    )
    return {label.upper() for label in matches}


def validate_quiz_variant_for_student(variant: object) -> list[str]:
    """Trả về mọi lỗi cấu trúc khiến variant không được phát hành.

    Đây là kiểm tra phát hành, không phải chứng minh Toán học. Không tự sửa nội
    dung để tránh biến dữ liệu sai thành một câu có vẻ hợp lệ.
    """
    if not isinstance(variant, dict):
        return ["Biến thể không có dữ liệu câu hỏi hợp lệ."]

    errors: list[str] = []
    question_type = str(variant.get("type") or "").strip()
    question = str(variant.get("question") or "").strip()
    solution = str(variant.get("solution") or "").strip()
    if not bool(variant.get("usable")):
        errors.append("Biến thể chưa được đánh dấu là có thể dùng.")
    if variant.get("requires_teacher_review"):
        errors.append("Biến thể vẫn cần giáo viên kiểm tra.")
    if not question:
        errors.append("Thiếu đề bài.")
    if not solution:
        errors.append("Thiếu lời giải để học sinh đối chiếu.")
    if question_type not in {"multiple_choice", "short_answer"}:
        errors.append("Dạng câu chưa hỗ trợ chấm tự động.")
        return errors

    if question_type == "multiple_choice":
        options = variant.get("options")
        if not isinstance(options, list) or len(options) != 4:
            errors.append("Câu trắc nghiệm phải có đúng bốn lựa chọn.")
        else:
            cleaned = [str(option or "").strip() for option in options]
            if not all(cleaned):
                errors.append("Có lựa chọn trắc nghiệm đang rỗng.")
            normalized = [normalize_text(option) for option in cleaned]
            if len(set(normalized)) != len(normalized):
                errors.append("Các lựa chọn trắc nghiệm bị trùng nhau.")
        correct_label = str(variant.get("correct_answer") or "").strip().upper()
        if correct_label not in {"A", "B", "C", "D"}:
            errors.append("Đáp án trắc nghiệm phải là đúng một nhãn A, B, C hoặc D.")
        else:
            declared_labels = explicit_solution_answer_labels(solution)
            if len(declared_labels) == 1 and correct_label not in declared_labels:
                errors.append("Đáp án lưu và nhãn đáp án ghi rõ trong lời giải không khớp nhau.")
            elif len(declared_labels) > 1:
                errors.append("Lời giải ghi nhiều nhãn đáp án khác nhau, cần kiểm tra lại.")
    elif not str(variant.get("correct_answer") or "").strip():
        errors.append("Câu trả lời ngắn thiếu đáp án để chấm.")
    return errors
