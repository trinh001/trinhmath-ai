from converter.question_provenance import build_question_provenance_records, provenance_summary


def test_question_provenance_requires_trusted_match_validation_and_candidate_link():
    candidates = [{
        "candidate_id": "c1",
        "source_file": "source.docx",
        "source_name": "Nguồn",
    }]
    rows = [{
        "parser_draft_id": 12,
        "matched_candidate_id": "c1",
        "match_status": "APPROVED_MANUAL",
        "match_score": 0.93,
        "ambiguity": 0,
        "validation_json": '{"pass": true, "errors": []}',
        "source_context_json": '{"source_files":["source.docx"],"image_names":["word/media/a.png"]}',
        "question_number": 4,
        "question_text": "Tính 2 + 2.",
        "question_math_json": '["2+2"]',
        "options_json": '[{"label":"A","content":"3"},{"label":"B","content":"4"}]',
        "correct_answer": "B",
        "solution": "2 + 2 = 4",
        "first_page_number": 2,
        "last_page_number": 2,
        "parser_confidence": .88,
        "flags_json": "[]",
    }]

    records = build_question_provenance_records(rows, candidates)

    assert len(records) == 1
    record = records[0]
    assert record["provenance_trusted"] is True
    assert record["source_file"] == "source.docx"
    assert record["matched_candidate_id"] == "c1"
    assert record["source_image_names"] == ["word/media/a.png"]
    assert record["formula_fingerprint"] == "2+2"
    assert provenance_summary(records) == {"records": 1, "trusted": 1, "untrusted": 0}


def test_auto_match_is_provenance_trusted_but_review_required_is_not():
    candidates = [{"candidate_id": "c1", "source_file": "a.pdf"}]
    base = {
        "matched_candidate_id": "c1",
        "match_score": .99,
        "ambiguity": 0,
        "validation_json": '{"pass": true}',
        "source_context_json": "{}",
        "question_number": 1,
        "question_text": "Cho x = 1.",
        "question_math_json": "[]",
        "options_json": "[]",
        "flags_json": "[]",
    }
    records = build_question_provenance_records([
        {"parser_draft_id": 1, "match_status": "APPROVED", **base},
        {"parser_draft_id": 2, "match_status": "REVIEW_REQUIRED", **base},
    ], candidates)

    assert records[0]["provenance_trusted"] is True
    assert records[1]["provenance_trusted"] is False


def test_ambiguous_or_invalid_match_never_becomes_trusted_provenance():
    candidates = [{"candidate_id": "c1", "source_file": "a.pdf"}]
    rows = [{
        "parser_draft_id": 1,
        "matched_candidate_id": "c1",
        "match_status": "APPROVED_MANUAL",
        "match_score": .99,
        "ambiguity": 1,
        "validation_json": '{"pass": true}',
        "source_context_json": "{}",
        "question_text": "Q",
        "question_math_json": "[]",
        "options_json": "[]",
        "flags_json": "[]",
    }, {
        "parser_draft_id": 2,
        "matched_candidate_id": "c1",
        "match_status": "APPROVED_MANUAL",
        "match_score": .99,
        "ambiguity": 0,
        "validation_json": '{"pass": false}',
        "source_context_json": "{}",
        "question_text": "Q",
        "question_math_json": "[]",
        "options_json": "[]",
        "flags_json": "[]",
    }]

    records = build_question_provenance_records(rows, candidates)

    assert all(not record["provenance_trusted"] for record in records)
