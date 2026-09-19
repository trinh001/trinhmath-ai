from local_review_workflow import (
    clear_local_draft_flag,
    flag_local_draft,
    flag_local_draft_batch,
    review_decision_text,
)


def _record():
    return {"provenance": "strict_local_short_answer_parser", "status": "Bản nháp cục bộ"}


def test_flag_is_reversible_and_preserves_original_fields():
    ok, flagged, _ = flag_local_draft(_record(), "math_mismatch", "Đáp số không khớp tổng cấp số.", "14/09/2026 09:00")

    assert ok is True
    assert flagged["provenance"] == "strict_local_short_answer_parser"
    assert flagged["review_decision"]["category"] == "math_mismatch"
    assert "không duyệt" in flagged["status"]
    assert "Đề, đáp án" in review_decision_text(flagged["review_decision"])

    restored, record, _ = clear_local_draft_flag(flagged)
    assert restored is True
    assert "review_decision" not in record
    assert "cần đối chiếu" in record["status"]


def test_flag_refuses_to_mutate_approved_question():
    record = _record() | {"status": "Đã duyệt và đưa vào ngân hàng"}
    ok, updated, message = flag_local_draft(record, "other", "", "now")
    assert ok is False
    assert updated is None
    assert "đã duyệt" in message


def test_batch_flag_preserves_existing_decisions_and_approved_records():
    records = {
        "first": _record() | {"question": "Câu 1"},
        "already-flagged": _record() | {"review_decision": {"category": "other"}},
        "approved": _record() | {"status": "Đã duyệt và đưa vào ngân hàng"},
        "ai": {"provenance": "gemini", "status": "Bản nháp AI"},
    }

    updated, changed, skipped = flag_local_draft_batch(
        records,
        ["first", "already-flagged", "approved", "ai", "first"],
        "missing_source_data",
        "Tệp nguồn cùng lỗi.",
        "14/09/2026 14:00",
    )

    assert changed == ["first"]
    assert set(skipped) == {"already-flagged", "approved", "ai"}
    assert updated["first"]["question"] == "Câu 1"
    assert updated["first"]["review_decision"]["category"] == "missing_source_data"
    assert updated["already-flagged"] == records["already-flagged"]
    assert updated["approved"] == records["approved"]
