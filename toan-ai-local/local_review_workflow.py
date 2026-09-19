"""Các chuyển trạng thái có thể đảo ngược cho hàng duyệt nháp cục bộ."""

from __future__ import annotations

from collections.abc import Mapping


LOCAL_DRAFT_PROVENANCE = frozenset({
    "strict_local_mc_parser",
    "strict_local_short_answer_parser",
})

DECISION_LABELS = {
    "missing_source_data": "Thiếu hoặc rơi dữ kiện từ nguồn",
    "formula_or_image_mismatch": "Công thức/hình không khớp nguồn",
    "math_mismatch": "Đề, đáp án hoặc lời giải Toán chưa khớp",
    "other": "Cần xem lại vì lý do khác",
}


def review_decision_text(decision: object) -> str:
    """Đổi payload lưu trữ thành nhãn ngắn, an toàn cho bảng điều phối."""
    if isinstance(decision, Mapping):
        category = str(decision.get("category") or "other")
        label = DECISION_LABELS.get(category, DECISION_LABELS["other"])
        note = str(decision.get("note") or "").strip()
        return f"{label}: {note}" if note else label
    return str(decision or "").strip()


def flag_local_draft(record: object, category: object, note: object, decided_at: object) -> tuple[bool, dict | None, str]:
    """Đánh dấu nháp không được duyệt, không xóa/sửa nội dung nháp gốc."""
    if not isinstance(record, Mapping):
        return False, None, "Không tìm thấy bản nháp để gắn cờ."
    if record.get("provenance") not in LOCAL_DRAFT_PROVENANCE:
        return False, None, "Chỉ bản nháp parser cục bộ mới dùng được quyết định này."
    if record.get("status") == "Đã duyệt và đưa vào ngân hàng":
        return False, None, "Câu đã duyệt không thể bị đổi trạng thái âm thầm ở hàng nháp."
    category_key = str(category or "other")
    if category_key not in DECISION_LABELS:
        category_key = "other"
    updated = dict(record)
    updated["review_decision"] = {
        "category": category_key,
        "note": str(note or "").strip()[:800],
        "decided_at": str(decided_at or "").strip(),
    }
    updated["status"] = "Đã gắn cờ — không duyệt cho đến khi đối chiếu lại"
    return True, updated, "Đã gắn cờ. Bản nháp và nguồn vẫn được giữ nguyên để xem lại sau."


def clear_local_draft_flag(record: object) -> tuple[bool, dict | None, str]:
    """Đưa nháp bị gắn cờ về hàng đối chiếu; không tự mở khóa duyệt."""
    if not isinstance(record, Mapping):
        return False, None, "Không tìm thấy bản nháp để khôi phục."
    if record.get("provenance") not in LOCAL_DRAFT_PROVENANCE:
        return False, None, "Chỉ bản nháp parser cục bộ mới dùng được thao tác này."
    if not record.get("review_decision"):
        return False, None, "Bản nháp này chưa có cờ để khôi phục."
    updated = dict(record)
    updated.pop("review_decision", None)
    updated["status"] = "Bản nháp cục bộ — cần đối chiếu giáo viên"
    return True, updated, "Đã đưa lại vào hàng đối chiếu. Câu vẫn cần giáo viên xác nhận nguồn trước khi duyệt."


def flag_local_draft_batch(
    records: object,
    candidate_ids: object,
    category: object,
    note: object,
    decided_at: object,
) -> tuple[dict[str, dict], list[str], list[str]]:
    """Gắn cờ một lô nháp cục bộ mà không ghi đè cờ/quyết định đã có.

    Hàm thuần này chỉ tạo bản sao của dữ liệu. Caller phải tự ghi một lần sau
    khi giáo viên đã xác nhận phạm vi tệp nguồn trong giao diện.
    """
    record_map = records if isinstance(records, Mapping) else {}
    ids = candidate_ids if isinstance(candidate_ids, list) else []
    updated = dict(record_map)
    changed_ids: list[str] = []
    skipped_ids: list[str] = []
    for raw_id in ids:
        candidate_id = str(raw_id or "").strip()
        if not candidate_id or candidate_id in changed_ids or candidate_id in skipped_ids:
            continue
        record = record_map.get(candidate_id)
        if not isinstance(record, Mapping):
            skipped_ids.append(candidate_id)
            continue
        if record.get("review_decision") or record.get("status") == "Đã duyệt và đưa vào ngân hàng":
            skipped_ids.append(candidate_id)
            continue
        ok, flagged, _message = flag_local_draft(record, category, note, decided_at)
        if ok and flagged is not None:
            updated[candidate_id] = flagged
            changed_ids.append(candidate_id)
        else:
            skipped_ids.append(candidate_id)
    return updated, changed_ids, skipped_ids
