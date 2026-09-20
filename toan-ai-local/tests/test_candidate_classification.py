from copy import deepcopy
from pathlib import Path

from candidate_classification import INVALID, MATCHED, REVIEW_REQUIRED, classify_candidates
from run_candidate_classification_report import build_report, main


def candidate(**overrides):
    record = {
        "candidate_id": "candidate-1",
        "source_file": "sample.docx",
        "source_name": "Sample source",
        "question_number": 1,
        "question_text": "Tính 2 + 3.",
        "solution_text": "Đáp án: 5. Cộng hai số tự nhiên được 5.",
        "correct_answer": "5",
        "eligible_for_text_pipeline": True,
    }
    record.update(overrides)
    return record


def source(**overrides):
    record = {
        "source_record_id": "sample.docx::1",
        "source_file": "sample.docx",
        "source_name": "Sample source",
        "question_number": 1,
        "question_text": "Tính 2 + 3.",
        "correct_answer": "5",
    }
    record.update(overrides)
    return record


def test_clean_exact_source_match_is_matched_with_auditable_confidence():
    report = classify_candidates([candidate()], [source()])

    row = report["classifications"][0]
    assert row["outcome"] == MATCHED
    assert row["reason_codes"] == ["SOURCE_MATCH_CONFIRMED", "STRUCTURE_VALID", "NO_DUPLICATE_DETECTED"]
    assert row["evidence"]["source_match"]["status"] == "CONFIRMED"
    assert row["evidence"]["confidence"]["score"] >= 0.85
    assert row["classification_scope"] == "READ_ONLY_NO_APPROVAL_OR_RELEASE_CHANGE"


def test_multiple_plausible_source_matches_require_teacher_review():
    report = classify_candidates([candidate()], [source(source_record_id="a"), source(source_record_id="b")])

    row = report["classifications"][0]
    assert row["outcome"] == REVIEW_REQUIRED
    assert "MULTIPLE_PLAUSIBLE_SOURCE_MATCHES" in row["reason_codes"]
    assert row["evidence"]["source_match"]["status"] == "AMBIGUOUS"


def test_exact_source_file_limits_comparison_without_hiding_same_file_ambiguity():
    report = classify_candidates(
        [candidate()],
        [source(source_record_id="same-a"), source(source_record_id="same-b"), source(source_record_id="other", source_file="other.docx")],
    )

    match = report["classifications"][0]["evidence"]["source_match"]
    assert match["catalog_size"] == 3
    assert match["compared_source_count"] == 2
    assert match["status"] == "AMBIGUOUS"


def test_prebuilt_source_file_index_preserves_matching_outcome():
    matching_source = source()
    report = classify_candidates(
        [candidate()],
        {"sources": [matching_source], "by_source_file": {"sample docx": [matching_source]}},
    )

    assert report["classifications"][0]["outcome"] == MATCHED


def test_exact_duplicate_candidates_are_reviewed_and_input_is_not_changed():
    candidates = [candidate(candidate_id="one"), candidate(candidate_id="two")]
    original = deepcopy(candidates)

    report = classify_candidates(candidates, [source()])

    assert candidates == original
    assert [row["outcome"] for row in report["classifications"]] == [REVIEW_REQUIRED, REVIEW_REQUIRED]
    assert all("DUPLICATE_CANDIDATE" in row["reason_codes"] for row in report["classifications"])
    assert report["reason_code_counts"]["DUPLICATE_CANDIDATE"] == 2


def test_missing_essential_structure_is_invalid_not_unknown():
    report = classify_candidates([candidate(question_text="")], [source()])

    row = report["classifications"][0]
    assert row["outcome"] == INVALID
    assert "MISSING_QUESTION_TEXT" in row["reason_codes"]
    assert row["outcome"] in {MATCHED, REVIEW_REQUIRED, INVALID}


def test_visual_or_formula_dependency_requires_review_even_when_source_matches():
    image_name = "word/media/formula.png"
    report = classify_candidates(
        [candidate(requires_visual_review=True, source_image_names=[image_name])],
        [source(source_image_names=[image_name])],
    )

    row = report["classifications"][0]
    assert row["outcome"] == REVIEW_REQUIRED
    assert "VISUAL_OR_FORMULA_REVIEW_REQUIRED" in row["reason_codes"]


def test_conflicting_explicit_answers_require_review():
    report = classify_candidates([candidate()], [source(correct_answer="6")])

    row = report["classifications"][0]
    assert row["outcome"] == REVIEW_REQUIRED
    assert "SOURCE_ANSWER_CONFLICT" in row["reason_codes"]


def test_option_and_formula_fingerprint_evidence_is_explicit_and_conflicts_fail_closed():
    matching = classify_candidates(
        [candidate(options=["3", "4", "5", "6"], formula_fingerprint="x+1=4")],
        [source(options=["3", "4", "5", "6"], formula_fingerprint="x+1=4")],
    )
    conflicting = classify_candidates(
        [candidate(options=["3", "4", "5", "6"], formula_fingerprint="x+1=4")],
        [source(options=["3", "4", "6", "5"], formula_fingerprint="x+2=4")],
    )

    evidence = matching["classifications"][0]["evidence"]["source_match"]["top_match"]
    assert evidence["components"]["option_agreement"] > 0
    assert evidence["components"]["formula_fingerprint"] > 0
    assert conflicting["classifications"][0]["outcome"] == REVIEW_REQUIRED
    assert "SOURCE_OPTIONS_CONFLICT" in conflicting["classifications"][0]["reason_codes"]
    assert "FORMULA_FINGERPRINT_CONFLICT" in conflicting["classifications"][0]["reason_codes"]


def test_math_contradiction_is_invalid_and_inconclusive_math_needs_review():
    contradicted = classify_candidates([candidate(math_verification={"status": "CONTRADICTED"})], [source()])
    inconclusive = classify_candidates([candidate(math_verification={"status": "INCONCLUSIVE"})], [source()])

    assert contradicted["classifications"][0]["outcome"] == INVALID
    assert "MATH_CONTRADICTED" in contradicted["classifications"][0]["reason_codes"]
    assert inconclusive["classifications"][0]["outcome"] == REVIEW_REQUIRED
    assert "MATH_REVIEW_REQUIRED" in inconclusive["classifications"][0]["reason_codes"]


def test_synthetic_cli_report_is_complete_and_read_only():
    fixture_dir = Path(__file__).parent / "fixtures"
    candidates_path = fixture_dir / "candidate_classification_candidates.json"
    sources_path = fixture_dir / "candidate_classification_sources.json"
    original_candidates = candidates_path.read_text(encoding="utf-8")
    original_sources = sources_path.read_text(encoding="utf-8")

    report = build_report(candidates_path, sources_path)

    assert report["candidate_count"] == 5
    assert report["unclassified_count"] == 0
    assert sum(report["outcome_counts"].values()) == 5
    assert candidates_path.read_text(encoding="utf-8") == original_candidates
    assert sources_path.read_text(encoding="utf-8") == original_sources


def test_cli_can_write_a_utf8_derived_report_without_touching_inputs(tmp_path, monkeypatch):
    fixture_dir = Path(__file__).parent / "fixtures"
    output_path = tmp_path / "report.json"
    monkeypatch.setattr("sys.argv", [
        "run_candidate_classification_report.py",
        "--candidates", str(fixture_dir / "candidate_classification_candidates.json"),
        "--sources", str(fixture_dir / "candidate_classification_sources.json"),
        "--output", str(output_path),
    ])

    assert main() == 0
    assert '"unclassified_count": 0' in output_path.read_text(encoding="utf-8")


def test_math_sensitive_matching_does_not_collapse_different_operators():
    report = classify_candidates(
        [candidate(question_text="Giải x + 1 = 4.", correct_answer="3")],
        [source(question_text="Giải x - 1 = 4.", correct_answer="3")],
    )

    row = report["classifications"][0]
    assert row["outcome"] == REVIEW_REQUIRED
    assert "QUESTION_OPERATOR_CONFLICT" in row["reason_codes"]
    assert row["evidence"]["source_match"]["status"] != "CONFIRMED"


def test_answer_sign_is_preserved_for_conflict_detection():
    report = classify_candidates(
        [candidate(correct_answer="-1")],
        [source(correct_answer="1")],
    )

    row = report["classifications"][0]
    assert row["outcome"] == REVIEW_REQUIRED
    assert "SOURCE_ANSWER_CONFLICT" in row["reason_codes"]


def test_missing_solution_is_review_required_not_destructively_invalid():
    report = classify_candidates(
        [candidate(solution_text="", correct_answer="5")],
        [source()],
    )

    row = report["classifications"][0]
    assert row["outcome"] == REVIEW_REQUIRED
    assert "SOURCE_QUALITY_REVIEW_REQUIRED" in row["reason_codes"]
    assert "MISSING_SOLUTION_TEXT" not in row["evidence"]["structural"]["hard_issues"]


def test_source_catalog_can_be_mapping_of_source_ids():
    report = classify_candidates(
        [candidate()],
        {"source-a": source(source_record_id="source-a")},
    )

    row = report["classifications"][0]
    assert row["outcome"] == MATCHED
    assert row["evidence"]["source_match"]["catalog_size"] == 1
