"""Chấm bài và tổng hợp kết quả theo chủ đề, không phụ thuộc giao diện Streamlit."""

from __future__ import annotations

import unicodedata
from collections.abc import Callable, Mapping


def _normalize_text(value: object) -> str:
    text = str(value or "")
    return "".join(
        char for char in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(char) != "Mn"
    ).replace("đ", "d")


def normalized_number(value: object) -> float | None:
    try:
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def short_answer_matches(submitted: object, expected: object) -> bool:
    """So khớp đáp án ngắn theo số trước, rồi theo LaTex đơn giản.

    Câu yêu cầu nhiều kết quả không thuộc loại được phép tạo qua luồng trả lời
    ngắn tự động, nên hàm này chỉ nhận một đáp án có thể đối chiếu rõ ràng.
    """
    submitted_number = normalized_number(submitted)
    expected_number = normalized_number(expected)
    if submitted_number is not None and expected_number is not None:
        return abs(submitted_number - expected_number) < 1e-8

    def compact_math(value: object) -> str:
        text = _normalize_text(value)
        for token in ("$", "\\left", "\\right", " ", "\t", "\n", "{"):
            text = text.replace(token, "")
        return text.replace("}", "")

    return bool(compact_math(submitted)) and compact_math(submitted) == compact_math(expected)


def grade(
    bank: Mapping[str, object],
    answers: Mapping[str, object],
    answer_display: Callable[[object], str],
    short_answer_matcher: Callable[[object, object], bool] = short_answer_matches,
) -> tuple[list[dict[str, object]], int, int, dict[str, list[int]]]:
    """Chấm kho câu đã được chuẩn hóa và trả dữ liệu dùng lại được cho UI/lưu trữ."""
    details: list[dict[str, object]] = []
    correct_count = 0
    total_items = 0
    topic_results: dict[str, list[int]] = {}

    def add_result(label, topic, user_answer, correct_answer, solution, is_correct):
        nonlocal correct_count, total_items
        total_items += 1
        correct_count += int(is_correct)
        topic_name = str(topic or "Chưa phân loại")
        topic_results.setdefault(topic_name, [0, 0])
        topic_results[topic_name][0] += int(is_correct)
        topic_results[topic_name][1] += 1
        details.append({
            "label": label,
            "topic": topic_name,
            "user": user_answer or "Chưa trả lời",
            "answer": correct_answer,
            "solution": solution,
            "correct": bool(is_correct),
        })

    for question in bank.get("multiple_choice", []) or []:
        question_id = question["id"]
        submitted = answers.get(question_id)
        expected = question["answer"]
        add_result(
            question_id,
            question.get("topic"),
            submitted,
            expected,
            question.get("solution", ""),
            submitted == answer_display(expected),
        )
    for question in bank.get("true_false", []) or []:
        for item in question.get("items", []) or []:
            item_id = item["id"]
            submitted = answers.get(item_id)
            add_result(
                item_id,
                question.get("topic"),
                submitted,
                item["answer"],
                item.get("solution", ""),
                submitted == item["answer"],
            )
    for question in bank.get("short_answer", []) or []:
        question_id = question["id"]
        submitted = answers.get(question_id)
        expected = question["answer"]
        add_result(
            question_id,
            question.get("topic"),
            submitted,
            expected,
            question.get("solution", ""),
            short_answer_matcher(submitted, expected),
        )
    return details, correct_count, total_items, topic_results
