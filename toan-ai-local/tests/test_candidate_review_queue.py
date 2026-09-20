from copy import deepcopy

from candidate_classification import classify_candidates
from candidate_review_queue import (
    build_candidate_review_queue,
    filter_candidate_review_queue,
    review_queue_detail,
)


def candidate(candidate_id="c1", **overrides):
    row = {
        "candidate_id": candidate_id,
        "source_file": "sample.docx",
        "source_name": "Sample",
        "question_number": 1,
        "question_text": "Tính 2 + 3.",
        "solution_text": "Đáp án: 5. Cộng hai số tự nhiên được 5.",
        "correct_answer": "5",
        "eligible_for_text_pipeline": True,
        "lesson": "Phép tính",
    }
    row.update(overrides)
    return row


def source(**overrides):
    row = {
        "source_record_id": "sample::1",
        "source_file": "sample.docx",
        "source_name": "Sample",
        "question_number": 1,
        "question_text": "Tính 2 + 3.",
        "correct_answer": "5",
    }
    row.update(overrides)
    return row


def test_review_required_rows_are_prioritized_before_matched_rows():
    candidates = [
        candidate("matched"),
        candidate("review", question_text="Tính 2 - 3."),
    ]
    report = classify_candidates(candidates, [source()])

    queue = build_candidate_review_queue(report, candidates)

    assert queue["rows"][0]["candidate_id"] == "review"
    assert queue["rows"][0]["outcome"] == "REVIEW_REQUIRED"
    assert queue["rows"][-1]["candidate_id"] == "matched"


def test_teacher_flagged_rows_are_deprioritized_but_not_removed():
    candidates = [
        candidate("flagged", question_text="Tính 2 - 3."),
        candidate("open", question_text="Tính 2 * 3."),
    ]
    report = classify_candidates(candidates, [source()])
    drafts = {
        "flagged": {"review_decision": "source_mismatch", "status": "Bản nháp cục bộ — cần đối chiếu giáo viên"},
        "open": {"status": "Bản nháp cục bộ — cần đối chiếu giáo viên"},
    }

    queue = build_candidate_review_queue(report, candidates, drafts=drafts)

    assert queue["rows"][0]["candidate_id"] == "open"
    assert queue["rows"][-1]["candidate_id"] == "flagged"
    assert queue["rows"][-1]["resolved"] is True


def test_queue_propagates_duplicate_visual_math_and_confidence_evidence():
    candidates = [
        candidate("a", requires_visual_review=True),
        candidate("b", requires_visual_review=True),
    ]
    report = classify_candidates(candidates, [source()])

    queue = build_candidate_review_queue(report, candidates)
    row = queue["rows"][0]

    assert row["duplicate_status"] == "DUPLICATE"
    assert row["requires_visual_review"] is True
    assert row["math_status"] == "NOT_REQUESTED"
    assert 0.0 <= row["confidence"] <= 1.0


def test_filters_do_not_mutate_queue_and_support_outcome_reason_source_lesson():
    candidates = [
        candidate("one", question_text="Tính 2 - 3.", lesson="Hàm số"),
        candidate("two", source_file="other.docx", source_name="Other", lesson="Xác suất"),
    ]
    report = classify_candidates(candidates, [source()])
    queue = build_candidate_review_queue(report, candidates)
    original = deepcopy(queue)

    rows = filter_candidate_review_queue(
        queue,
        outcomes=["REVIEW_REQUIRED"],
        source_text="sample",
        lesson_text="hàm",
        unresolved_only=True,
    )

    assert [row["candidate_id"] for row in rows] == ["one"]
    assert queue == original


def test_review_queue_detail_is_detached_and_has_no_approval_or_release_mutation():
    candidates = [candidate("c1")]
    report = classify_candidates(candidates, [source()])
    queue = build_candidate_review_queue(report, candidates)

    detail = review_queue_detail(queue, "c1")

    assert detail is not None
    assert detail["classification_scope"] == "READ_ONLY_NO_APPROVAL_OR_RELEASE_CHANGE"
    detail["outcome"] = "INVALID"
    assert queue["rows"][0]["outcome"] == "MATCHED"
    assert "approval" not in detail
    assert "release" not in detail
