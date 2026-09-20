from pathlib import Path

import teacher_review_pilot as pilot


def row(**overrides):
    value = {"candidate_id": "c1", "outcome": "REVIEW_REQUIRED", "resolved": False, "reason_codes": ["SOURCE_MATCH_LOW_CONFIDENCE"], "source_match_score": 0.7, "confidence": 0.8, "duplicate_status": "UNIQUE", "requires_visual_review": False, "math_status": "VERIFIED", "source_file": "sample.docx", "evidence": {"structural": {"math_status": "VERIFIED", "hard_issues": []}, "source_match": {"candidate_linked_source_count": 1}}}
    value.update(overrides); return value


def test_shortlist_excludes_unsafe_rows():
    assert [item["candidate_id"] for item in pilot.build_shortlist([row(), row(candidate_id="bad", requires_visual_review=True)])] == ["c1"]


def test_decision_audit_and_promote_are_local_and_versioned(tmp_path, monkeypatch):
    monkeypatch.setattr(pilot, "RECORDS_FILE", Path(tmp_path) / "records.json")
    monkeypatch.setattr(pilot, "TRUSTED_BANK_FILE", Path(tmp_path) / "bank.json")
    reviewed = pilot.save_decision("c1", pilot.APPROVED_MANUAL, "teacher", "source checked", row())
    assert reviewed["audit"][0]["previous_decision"] is None
    candidate = {"question_text": "2+3", "solution_text": "5", "correct_answer": "5"}
    assert pilot.promote(candidate, row(), reviewed)[0] is True
    assert pilot.promote(candidate, row(), reviewed)[0] is False
    reviewed = pilot.save_decision("c1", pilot.APPROVED_MANUAL, "teacher", "rechecked source", row())
    assert pilot.promote(candidate, row(), reviewed)[0] is True
    assert [entry["version"] for entry in pilot.load_trusted_bank()["c1"]] == [1, 2]
