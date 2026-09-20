import json

from candidate_classification import classify_candidates
from candidate_data_adapter import adapt_real_m2_inputs, aggregate_classification_metrics
from candidate_review_queue import build_candidate_review_queue, filter_candidate_review_queue
from run_local_m2_measurement import run_measurement


def raw_candidate(**overrides):
    value = {
        "candidate_id": "candidate-1", "source_file": "raw.docx", "source_name": "Raw source",
        "question_number": 1, "question_text": "Tính 2 + 2.",
        "solution_text": "Đáp án: 4. Cộng hai số được 4.", "lesson": "Bài 1",
    }
    value.update(overrides)
    return value


def raw_source(**overrides):
    value = {"file_name": "raw.docx", "original_name": "Raw source", "grade": "Lớp 10", "lesson": "Bài 1"}
    value.update(overrides)
    return value


def test_real_schema_adapter_builds_index_without_rewriting_input():
    candidates = [raw_candidate()]
    sources = [raw_source()]
    adapted = adapt_real_m2_inputs(candidates, sources)

    assert candidates[0]["source_file"] == "raw.docx"
    assert adapted["sources"][0]["source_file"] == "raw.docx"
    assert "raw docx" in adapted["source_match_input"]["by_source_file"]
    assert adapted["schema_summary"]["candidate_source_catalog_coverage"] == 1


def test_queue_prioritizes_unresolved_review_and_propagates_source_evidence():
    candidates = [
        raw_candidate(candidate_id="review", requires_visual_review=True, source_image_names=["a.png"]),
        raw_candidate(candidate_id="resolved", question_number=2, question_text="Tính 3 + 3.", source_image_names=[]),
    ]
    adapted = adapt_real_m2_inputs(candidates, [raw_source()])
    report = classify_candidates(adapted["candidates"], adapted["source_match_input"])
    drafts = {"resolved": {"provenance": "strict_local_short_answer_parser", "status": "Bản nháp cục bộ", "review_decision": {"category": "other", "note": "Đã xem"}}}

    queue = build_candidate_review_queue(report, candidates, {}, drafts)

    assert queue["rows"][0]["candidate_id"] == "review"
    assert queue["rows"][0]["outcome"] == "REVIEW_REQUIRED"
    assert queue["rows"][0]["source_review"]["requires_visual_review"] is True
    assert queue["rows"][1]["review_state"] == "TEACHER_FLAGGED"


def test_queue_filters_by_outcome_reason_source_and_lesson_without_state_mutation():
    candidates = [raw_candidate(requires_visual_review=True, source_image_names=["a.png"])]
    adapted = adapt_real_m2_inputs(candidates, [raw_source()])
    report = classify_candidates(adapted["candidates"], adapted["source_match_input"])
    queue = build_candidate_review_queue(report, candidates, {}, {})

    filtered = filter_candidate_review_queue(
        queue, outcomes=["REVIEW_REQUIRED"], reasons=["VISUAL_OR_FORMULA_REVIEW_REQUIRED"], source_query="raw", lesson="Bài 1"
    )

    assert len(filtered) == 1
    assert candidates[0]["candidate_id"] == "candidate-1"
    assert filtered[0]["can_flag_local_draft"] is False


def test_aggregate_metrics_and_measurement_only_return_counts(tmp_path):
    candidates_path = tmp_path / "candidates.json"
    sources_path = tmp_path / "sources.json"
    candidates_path.write_text(json.dumps([raw_candidate()], ensure_ascii=False), encoding="utf-8")
    sources_path.write_text(json.dumps([raw_source()], ensure_ascii=False), encoding="utf-8")

    measured = run_measurement(candidates_path, sources_path)
    metrics = measured["metrics"]

    assert metrics["candidate_total"] == 1
    assert metrics["unclassified_count"] == 0
    assert "classifications" not in metrics
    assert aggregate_classification_metrics({"candidate_count": 0, "outcome_counts": {}, "classifications": []})["candidate_total"] == 0


def test_teacher_flagged_local_draft_can_be_restored_but_not_flagged_again():
    candidates = [raw_candidate()]
    adapted = adapt_real_m2_inputs(candidates, [raw_source()])
    report = classify_candidates(adapted["candidates"], adapted["source_match_input"])
    drafts = {
        "candidate-1": {
            "provenance": "strict_local_short_answer_parser",
            "status": "Đã gắn cờ — không duyệt cho đến khi đối chiếu lại",
            "review_decision": {"category": "other", "note": "Đã xem"},
        }
    }

    queue = build_candidate_review_queue(report, candidates, {}, drafts)
    row = queue["rows"][0]

    assert row["review_state"] == "TEACHER_FLAGGED"
    assert row["resolved"] is True
    assert row["can_restore_local_draft"] is True
    assert row["can_flag_local_draft"] is False


def test_manual_formula_override_reaches_source_review_snapshot():
    candidates = [
        raw_candidate(
            legacy_math_image_names=["word/media/formula.wmf"],
            requires_visual_review=True,
        )
    ]
    adapted = adapt_real_m2_inputs(candidates, [raw_source()])
    report = classify_candidates(adapted["candidates"], adapted["source_match_input"])

    queue = build_candidate_review_queue(
        report,
        candidates,
        {},
        {},
        {"candidate-1": {"word/media/formula.wmf": "x+1=2"}},
    )

    row = queue["rows"][0]
    assert row["source_review"]["requires_visual_review"] is True
    assert row["classification_scope"] == "READ_ONLY_NO_APPROVAL_OR_RELEASE_CHANGE"
