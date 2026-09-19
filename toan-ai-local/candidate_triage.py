"""Phân nhóm candidate bảo thủ để tăng throughput mà không hạ hàng rào an toàn."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from source_quality import source_content_quality_issues


GROUP_LABELS = {
    "A": "A — chữ, đáp án và lời giải rõ",
    "B": "B — chữ/đáp án rõ nhưng thiếu lời giải",
    "C": "C — có hình hoặc MathType cần xác minh",
    "D": "D — nguồn/ranh giới/dữ kiện chưa đủ",
}
GROUP_RANK = {group: rank for rank, group in enumerate(("A", "B", "C", "D"))}
ANSWER_RE = re.compile(r"(?i)\b(?:đáp\s*án|đáp\s*số|chọn)\s*[:\-]?\s*(?:\(?[A-D]\)?|[+\-]?\d+(?:[\.,]\d+)?|\$[^$\n]{1,100}\$)")


def _normalize_text(value: object) -> str:
    text = str(value or "")
    return "".join(
        char for char in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(char) != "Mn"
    ).replace("đ", "d")


def _has_visual_source(candidate: dict) -> bool:
    return bool(
        candidate.get("source_image_names")
        or candidate.get("legacy_math_image_names")
        or candidate.get("visual_paths")
    )


def _answer_and_explanation_state(solution: object) -> tuple[bool, bool]:
    text = str(solution or "").strip()
    match = ANSWER_RE.search(text)
    if not match:
        return False, False
    explanation = _normalize_text(text[match.end():]).strip(" .:-")
    return True, len(explanation) >= 24


def triage_candidate(candidate: object) -> dict[str, object]:
    """Xếp một candidate vào A–D, chỉ từ cờ hiện hữu và không tự sửa dữ liệu."""
    if not isinstance(candidate, dict):
        return {"group": "D", "rank": GROUP_RANK["D"], "reason": "Candidate không đúng định dạng."}

    question = str(candidate.get("question_text") or "").strip()
    solution = str(candidate.get("solution_text") or "").strip()
    boundary_issue = bool(candidate.get("boundary_issue") or candidate.get("implicit_boundary"))
    visual_required = bool(candidate.get("requires_visual_review") or candidate.get("has_legacy_mathtype"))
    visual_source = _has_visual_source(candidate)
    text_pipeline = bool(candidate.get("eligible_for_text_pipeline"))
    answer_clear, explanation_clear = _answer_and_explanation_state(solution)
    source_issues = source_content_quality_issues(candidate)

    if boundary_issue:
        group, reason = "D", "Ranh giới câu hoặc dữ kiện nguồn đang nghi ngờ."
    elif source_issues:
        group, reason = "D", source_issues[0]
    elif not question:
        group, reason = "D", "Thiếu nội dung đề bài để xác định câu độc lập."
    elif visual_required:
        if visual_source:
            group, reason = "C", "Có hình/MathType nguồn; cần xác minh công thức hoặc hình trước khi dựng câu."
        else:
            group, reason = "D", "Có cờ cần hình/công thức nhưng chưa tìm thấy mảnh nguồn đủ để đối chiếu."
    elif not text_pipeline:
        group, reason = "D", "Không thuộc luồng văn bản rõ; cần đối chiếu nguồn hoặc phân loại lại."
    elif not answer_clear:
        group, reason = "D", "Chưa nhận ra đáp án rõ ràng trong lời giải nguồn."
    elif explanation_clear:
        group, reason = "A", "Văn bản, đáp án và phần giải thích đủ rõ để ưu tiên tạo bản nháp rồi duyệt."
    else:
        group, reason = "B", "Đã có đề và đáp án rõ nhưng phần giải thích quá ngắn hoặc thiếu."

    return {"group": group, "rank": GROUP_RANK[group], "reason": reason}


def triage_candidates(candidates: Iterable[object]) -> dict[str, object]:
    """Tạo bảng ưu tiên để UI/service dùng mà không thay đổi candidate gốc."""
    counts = {group: 0 for group in GROUP_LABELS}
    rows = []
    for candidate in candidates:
        triage = triage_candidate(candidate)
        group = str(triage["group"])
        counts[group] += 1
        candidate_data = candidate if isinstance(candidate, dict) else {}
        rows.append({
            "candidate_id": candidate_data.get("candidate_id", ""),
            "group": group,
            "label": GROUP_LABELS[group],
            "rank": triage["rank"],
            "reason": triage["reason"],
            "grade": candidate_data.get("grade", "Chưa phân loại"),
            "lesson": candidate_data.get("lesson", "Chưa phân loại"),
            "source_name": candidate_data.get("source_name") or candidate_data.get("source_file") or "Không rõ nguồn",
            "question_number": candidate_data.get("question_number", "?"),
        })
    rows.sort(key=lambda item: (item["rank"], str(item["grade"]), str(item["lesson"]), str(item["source_name"]), str(item["question_number"])))
    return {"counts": counts, "rows": rows}
