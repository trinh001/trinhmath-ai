import json

from math_verifier import CONTRADICTED, VERIFIED
from variant_review_service import RELEASED_STATUS, attach_math_verification


def draft_record(status="Bản nháp trắc nghiệm — chưa dùng cho học sinh"):
    return {
        "status": status,
        "variant": json.dumps({
            "usable": True,
            "type": "short_answer",
            "question": "Giải $x^2-1=0$.",
            "correct_answer": "$x=1$",
            "solution": "Thử lại nghiệm.",
        }, ensure_ascii=False),
    }


def test_attach_math_verification_keeps_input_and_adds_audit_history():
    record = draft_record()
    ok, updated, result = attach_math_verification(
        record,
        {"kind": "equation_solution", "lhs": "x**2 - 1", "rhs": "0", "candidate": "1", "variable": "x"},
        checked_at="13/09/2026 19:00",
    )
    assert ok and result["status"] == VERIFIED
    assert "math_verification" not in json.loads(record["variant"])
    saved_variant = json.loads(updated["variant"])
    assert saved_variant["math_verification"]["status"] == VERIFIED
    assert updated["math_verification_history"][0]["claim"]["candidate"] == "1"
    assert updated["status"] == record["status"]


def test_contradicted_result_is_kept_for_review_not_silently_changed():
    ok, updated, result = attach_math_verification(
        draft_record(),
        {"kind": "equation_solution", "lhs": "x**2 - 1", "rhs": "0", "candidate": "2", "variable": "x"},
    )
    assert ok and result["status"] == CONTRADICTED
    assert json.loads(updated["variant"])["math_verification"]["status"] == CONTRADICTED
    assert updated["status"] != RELEASED_STATUS


def test_released_variant_is_never_mutated_by_verifier():
    record = draft_record(RELEASED_STATUS)
    ok, updated, result = attach_math_verification(record, {"kind": "expression_equivalence", "lhs": "x", "rhs": "x"})
    assert not ok and updated is None
    assert "không được sửa" in result["message"]
