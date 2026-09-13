"""Regression test for manual review persistence and audit trail."""
from pathlib import Path
from tempfile import TemporaryDirectory

from converter.storage import ConverterStore


with TemporaryDirectory() as directory:
    root = Path(directory)
    source = root / "source.txt"
    source.write_text("Câu 1. 1 + 1 = ?", encoding="utf-8")
    store = ConverterStore(root / "converter.db")
    document_id = store.register_document(source, "TEXT", [{"number": 1, "classification": "TEXT_PAGE", "text": source.read_text(encoding="utf-8")}])
    store.replace_parsed_document(document_id, [{
        "source_page": 1, "source_page_end": 1, "question_number": 1,
        "question_type": "short_answer", "question_text": "1 + 1 = ?",
        "raw_ocr_text": "Câu 1. 1 + 1 = ?", "validation": {"valid": True},
    }], [])
    draft_id = store.parsed_questions(1)[0]["id"]
    store.save_match_reviews([{
        "parser_draft_id": draft_id, "matched_candidate_id": "candidate-1",
        "match_score": 0.99, "duplicate": False, "status": "REVIEW_REQUIRED",
        "reason": "test", "ambiguous": False, "validation": {"pass": True},
        "source_context": {}, "normalized_parser_data": "1 1", "top_matches": [{"breakdown": {"text": 1.0}}],
    }])
    store.record_manual_match_decision(draft_id, "APPROVED_MANUAL", "teacher_checked", "TEST_TEACHER")
    row = store.match_reviews(1)[0]
    assert row["status"] == "APPROVED_MANUAL"
    with store.session() as connection:
        audit = connection.execute("SELECT decision, approved_by FROM match_audit_log ORDER BY id DESC LIMIT 1").fetchone()
    assert audit["decision"] == "APPROVED_MANUAL" and audit["approved_by"] == "TEST_TEACHER"

print("REVIEW_STORAGE=OK")
