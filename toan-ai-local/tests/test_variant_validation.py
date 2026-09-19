from variant_validation import explicit_solution_answer_labels, validate_quiz_variant_for_student


def valid_multiple_choice():
    return {
        "usable": True,
        "type": "multiple_choice",
        "question": "Giải phương trình $x+1=2$.",
        "options": ["$x=1$", "$x=2$", "$x=-1$", "$x=0$"],
        "correct_answer": "A",
        "solution": "Ta có $x=1$.\nĐáp án: A.",
        "requires_teacher_review": False,
    }


def test_valid_variant_is_releasable():
    assert validate_quiz_variant_for_student(valid_multiple_choice()) == []


def test_blank_and_duplicate_options_are_blocked():
    variant = valid_multiple_choice()
    variant["options"] = ["$x=1$", " $x=1$ ", "$x=-1$", ""]
    errors = validate_quiz_variant_for_student(variant)
    assert any("rỗng" in error for error in errors)
    assert any("trùng" in error for error in errors)


def test_solution_answer_conflict_is_blocked():
    variant = valid_multiple_choice()
    variant["solution"] = "Lời giải đã kiểm tra.\nĐáp án: B."
    assert any("không khớp" in error for error in validate_quiz_variant_for_student(variant))


def test_multiple_declared_labels_are_blocked():
    variant = valid_multiple_choice()
    variant["solution"] = "Đáp án: A.\nĐáp án: C."
    assert any("nhiều nhãn" in error for error in validate_quiz_variant_for_student(variant))


def test_short_answer_needs_a_key_and_review_flag_blocks_release():
    variant = {
        "usable": True,
        "type": "short_answer",
        "question": "Tính $1+1$.",
        "correct_answer": "",
        "solution": "Ta có $1+1=2$.",
        "requires_teacher_review": True,
    }
    errors = validate_quiz_variant_for_student(variant)
    assert any("giáo viên" in error for error in errors)
    assert any("thiếu đáp án" in error.lower() for error in errors)


def test_explicit_answer_labels_only_accept_clear_labels():
    assert explicit_solution_answer_labels("Đáp án: C.") == {"C"}
    assert explicit_solution_answer_labels("Theo đáp án tham khảo, phương án C hợp lý.") == set()
