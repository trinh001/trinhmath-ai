import json

from health_checks import audit_data_links


READY = "Đã duyệt — sẵn sàng cho học sinh"


def _ready_record(variant):
    return {"status": READY, "variant": json.dumps(variant, ensure_ascii=False)}


def _valid_variant():
    return {
        "usable": True,
        "type": "multiple_choice",
        "question": "Giải phương trình x + 1 = 2.",
        "options": ["x = 1", "x = 2", "x = -1", "x = 0"],
        "correct_answer": "A",
        "solution": "Ta có x = 1.\nĐáp án: A.",
        "requires_teacher_review": False,
    }


def _audit(variant):
    return audit_data_links(
        sources=[{"file_name": "source.docx"}],
        candidates=[{"candidate_id": "candidate-1", "source_file": "source.docx"}],
        variants={"candidate-1": _ready_record(variant)},
        sources_dir=".",
    )


def test_audit_accepts_a_ready_variant_that_passes_the_release_gate():
    assert _audit(_valid_variant())["invalid_ready"] == []


def test_audit_flags_a_ready_variant_with_duplicate_options():
    variant = _valid_variant()
    variant["options"] = ["x = 1", " x = 1 ", "x = -1", "x = 0"]

    assert _audit(variant)["invalid_ready"] == ["candidate-1"]


def test_audit_flags_a_ready_variant_with_a_non_verified_math_result():
    variant = _valid_variant()
    variant["math_verification"] = {"status": "INCONCLUSIVE"}

    assert _audit(variant)["invalid_ready"] == ["candidate-1"]
