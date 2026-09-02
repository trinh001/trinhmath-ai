"""Kiểm định cấu trúc và liên kết dữ liệu cho Toán THPT AI.

Mô-đun này không phụ thuộc Streamlit để có thể chạy độc lập trong self_check.py.
Mọi thay đổi có ảnh hưởng dữ liệu nên đi qua các kiểm tra ở đây.
"""

import json
import re
from pathlib import Path


CURRICULUM_EXPECTATIONS = {
    "Lớp 10": (9, 27),
    "Lớp 11": (9, 33),
    "Lớp 12": (6, 19),
}


def validate_curricula(load_curriculum):
    """Trả danh sách lỗi thay vì dừng app khi chương/bài bị thiếu hoặc trùng."""
    errors = []
    for grade, (expected_chapters, last_lesson) in CURRICULUM_EXPECTATIONS.items():
        curriculum = load_curriculum(grade)
        numbers = [
            int(number)
            for chapter in curriculum
            for number in re.findall(r"Bài ([0-9]+)", " ".join(chapter.get("lessons", [])))
        ]
        if len(curriculum) != expected_chapters:
            errors.append(f"{grade}: có {len(curriculum)} chương, cần {expected_chapters}.")
        if sorted(set(numbers)) != list(range(1, last_lesson + 1)):
            errors.append(f"{grade}: danh sách Bài không liên tục từ 1 đến {last_lesson}.")
    return errors


def audit_data_links(sources, candidates, variants, sources_dir):
    """Kiểm tra quan hệ nguồn → câu đã tách → biến thể phát hành."""
    source_files = {item.get("file_name") for item in sources}
    candidate_ids = {item.get("candidate_id") for item in candidates}
    missing_source_files = [item.get("file_name") for item in sources if not (Path(sources_dir) / item.get("file_name", "")).exists()]
    orphan_candidates = [item.get("candidate_id") for item in candidates if item.get("source_file") not in source_files]
    orphan_variants = [candidate_id for candidate_id in variants if candidate_id not in candidate_ids]
    invalid_ready = []
    for candidate_id, record in variants.items():
        if record.get("status") != "Đã duyệt — sẵn sàng cho học sinh":
            continue
        try:
            question = json.loads(record.get("variant", ""))
            valid = bool(question.get("usable")) and not question.get("requires_teacher_review")
            if question.get("type") == "multiple_choice":
                valid = valid and len(question.get("options") or []) == 4
            elif question.get("type") == "short_answer":
                valid = valid and bool(str(question.get("correct_answer", "")).strip())
            else:
                valid = False
        except (TypeError, json.JSONDecodeError):
            valid = False
        if not valid:
            invalid_ready.append(candidate_id)
    return {
        "missing_source_files": missing_source_files,
        "orphan_candidates": orphan_candidates,
        "orphan_variants": orphan_variants,
        "invalid_ready": invalid_ready,
    }


def has_data_link_errors(audit):
    return any(audit.values())
