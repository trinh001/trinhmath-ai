from pathlib import Path
from tempfile import TemporaryDirectory

from converter.storage import ConverterStore
from converter.trusted_bank import promote_approved_match_to_trusted_bank


with TemporaryDirectory() as temporary:
    root = Path(temporary)
    source = root / "source.docx"
    source.write_text("Câu 1. Tính 2+2.\nA. 3\nB. 4\nC. 5\nD. 6\nĐáp án: B", encoding="utf-8")

    store = ConverterStore(root / "converter.db")
    document_id = store.register_document(
        source,
        "TEXT",
        [{"number": 1, "classification": "TEXT_PAGE", "text": source.read_text(encoding="utf-8")}],
    )
    store.replace_parsed_document(
        document_id,
        [
            {
                "source_page": 1,
                "source_page_end": 1,
                "question_number": 1,
                "question_type": "multiple_choice",
                "question_text": "Tính 2+2.",
                "question_math": ["2+2"],
                "options": [
                    {"label": "A", "content": "3"},
                    {"label": "B", "content": "4"},
                    {"label": "C", "content": "5"},
                    {"label": "D", "content": "6"},
                ],
                "correct_answer": "B",
                "solution": "2+2=4",
                "raw_ocr_text": "Câu 1. Tính 2+2.",
                "validation": {"pass": True},
            }
        ],
        [],
    )

    parser_draft_id = store.parsed_questions(1)[0]["id"]
    store.save_match_reviews([
        {
            "parser_draft_id": parser_draft_id,
            "matched_candidate_id": "candidate-1",
            "match_score": 0.99,
            "duplicate": False,
            "status": "REVIEW_REQUIRED",
            "reason": "teacher_review",
            "ambiguous": False,
            "validation": {"pass": True},
            "source_context": {"source_files": ["source.docx"]},
            "normalized_parser_data": "2 2",
            "top_matches": [{"breakdown": {"text": 1.0}}],
        }
    ])
    store.record_manual_match_decision(parser_draft_id, "APPROVED_MANUAL", "teacher_checked", "TEST_TEACHER")

    result = promote_approved_match_to_trusted_bank(
        store,
        parser_draft_id,
        teacher_review_evidence={"manual": True, "notes": "reviewed"},
        reviewer="TEST_TEACHER",
        reviewed_at="2026-01-01 00:00:00",
        curriculum_metadata={"grade": "10"},
        math_verification_evidence={"status": "VERIFIED"},
    )

    assert result["question_id"] == "candidate-1"
    assert result["version"] == 1
    assert result["status"] == "APPROVED"

    row = store.get_match_review_for_promotion(parser_draft_id)
    assert row["match_status"] == "APPROVED_MANUAL"

    summary = store.trusted_question_summary()
    assert summary["questions"]["APPROVED"] == 1
    assert summary["versions"] == 1

    # Promotion must fail without explicit teacher review evidence.
    try:
        promote_approved_match_to_trusted_bank(
            store,
            parser_draft_id,
            teacher_review_evidence={},
            reviewer="TEST_TEACHER",
            reviewed_at="2026-01-01 00:00:00",
            status="APPROVED",
        )
        raise AssertionError("expected promotion to fail for approval evidence type")
    except ValueError:
        pass

    # A contradicted math claim is never promotable.
    try:
        promote_approved_match_to_trusted_bank(
            store,
            parser_draft_id,
            teacher_review_evidence={"manual": True},
            reviewer="TEST_TEACHER",
            math_verification_evidence={"status": "CONTRADICTED"},
        )
        raise AssertionError("expected contradicted math to block promotion")
    except ValueError:
        pass

    # Only an explicit teacher approval state may promote content.
    with store.session() as connection:
        connection.execute("UPDATE match_reviews SET status='REVIEW_REQUIRED' WHERE parser_draft_id=?", (parser_draft_id,))
    try:
        promote_approved_match_to_trusted_bank(
            store,
            parser_draft_id,
            teacher_review_evidence={"manual": True},
            reviewer="TEST_TEACHER",
        )
        raise AssertionError("expected non-manual match status to block promotion")
    except ValueError:
        pass

    with store.session() as connection:
        connection.execute("UPDATE match_reviews SET status='APPROVED_MANUAL' WHERE parser_draft_id=?", (parser_draft_id,))
        connection.execute("UPDATE documents SET source_path='' WHERE id=?", (document_id,))
    try:
        promote_approved_match_to_trusted_bank(
            store,
            parser_draft_id,
            teacher_review_evidence={"manual": True},
            reviewer="TEST_TEACHER",
        )
        raise AssertionError("expected unresolved source provenance to block promotion")
    except ValueError:
        pass

    with store.session() as connection:
        connection.execute("UPDATE documents SET source_path=? WHERE id=?", (str(source), document_id))
        connection.execute("UPDATE parsed_questions SET correct_answer='' WHERE id=?", (parser_draft_id,))
    try:
        promote_approved_match_to_trusted_bank(
            store,
            parser_draft_id,
            teacher_review_evidence={"manual": True},
            reviewer="TEST_TEACHER",
        )
        raise AssertionError("expected incomplete answer structure to block promotion")
    except ValueError:
        pass

print("TRUSTED_BANK=OK")
