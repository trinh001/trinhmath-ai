"""Tính độ phủ chương trình và hàng ưu tiên phát triển kho từ dữ liệu đã duyệt."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable


def _normalize_text(value: object) -> str:
    text = str(value or "")
    return "".join(
        char for char in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(char) != "Mn"
    ).replace("đ", "d")


def curriculum_lesson_key(lesson: object) -> str:
    """Khóa bài học ổn định khi tên có thêm/bớt mô tả sau số bài."""
    text = _normalize_text(lesson)
    number = re.search(r"\bbai\s*(\d+)\b", text)
    return f"bai-{number.group(1)}" if number else text


def build_curriculum_coverage(
    curriculum: Iterable[dict],
    grade: str,
    candidates: Iterable[dict],
    approved_metadata: Iterable[dict],
    ready_metadata: Iterable[dict],
) -> dict[str, object]:
    """Đếm nguyên liệu, câu đã duyệt và câu phát hành mà không sửa đầu vào."""
    rows = []
    for chapter_data in curriculum or []:
        for lesson in chapter_data.get("lessons", []) or []:
            rows.append({
                "chapter": chapter_data.get("chapter", "Chưa phân loại"),
                "lesson": lesson,
                "key": curriculum_lesson_key(lesson),
                "candidates": 0,
                "approved": 0,
                "ready": 0,
            })
    by_key = {row["key"]: row for row in rows}
    for candidate in candidates or []:
        if candidate.get("grade") == grade:
            row = by_key.get(curriculum_lesson_key(candidate.get("lesson")))
            if row:
                row["candidates"] += 1
    for metadata in approved_metadata or []:
        if metadata.get("grade") == grade:
            row = by_key.get(curriculum_lesson_key(metadata.get("lesson")))
            if row:
                row["approved"] += 1
    unmapped_ready = 0
    for metadata in ready_metadata or []:
        if metadata.get("grade") != grade:
            continue
        row = by_key.get(curriculum_lesson_key(metadata.get("lesson")))
        if row:
            row["ready"] += 1
        else:
            unmapped_ready += 1
    for row in rows:
        if row["ready"] >= 3:
            row["coverage"] = "Có thể luyện ngắn"
        elif row["ready"]:
            row["coverage"] = "Cần thêm câu đã duyệt"
        elif row["approved"] or row["candidates"]:
            row["coverage"] = "Có nguyên liệu, chưa phát hành"
        else:
            row["coverage"] = "Chưa có dữ liệu"
    return {"grade": grade, "lessons": rows, "unmapped_ready": unmapped_ready}


def build_development_queue(
    coverage: dict,
    candidates: Iterable[dict],
    safe_text_candidate_ids: set[str],
    limit: int = 10,
) -> list[dict]:
    """Ưu tiên phát hành câu đã duyệt trước rồi mới tới nguyên liệu an toàn."""
    candidates_by_lesson: dict[str, list[dict]] = {}
    for candidate in candidates or []:
        candidates_by_lesson.setdefault(curriculum_lesson_key(candidate.get("lesson")), []).append(candidate)
    queue = []
    for lesson_row in coverage.get("lessons", []) or []:
        if lesson_row["ready"] >= 3:
            continue
        lesson_candidates = candidates_by_lesson.get(lesson_row["key"], [])
        safe_count = sum(1 for item in lesson_candidates if item.get("candidate_id") in safe_text_candidate_ids)
        if lesson_row["approved"] > lesson_row["ready"]:
            priority, action = 0, "Kiểm tra/đóng gói các câu đã duyệt còn chưa phát hành"
        elif safe_count:
            priority, action = 1, "Tạo bản nháp từ câu chữ đã đủ dữ kiện, rồi giáo viên duyệt"
        elif lesson_candidates:
            priority, action = 2, "Xác minh hình, công thức hoặc ranh giới trước khi tạo bản nháp"
        else:
            priority, action = 3, "Bổ sung đề mẫu hoặc tài liệu đúng bài học"
        queue.append({
            "chapter": lesson_row["chapter"],
            "lesson": lesson_row["lesson"],
            "ready": lesson_row["ready"],
            "approved": lesson_row["approved"],
            "candidates": lesson_row["candidates"],
            "safe_text_candidates": safe_count,
            "action": action,
            "priority": priority,
        })
    return sorted(
        queue,
        key=lambda item: (item["priority"], -item["approved"], -item["safe_text_candidates"], -item["candidates"], item["lesson"]),
    )[:max(1, int(limit))]
