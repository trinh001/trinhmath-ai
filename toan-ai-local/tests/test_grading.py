from grading import grade, short_answer_matches


def test_short_answer_matches_numbers_and_simple_latex():
    assert short_answer_matches("1,5", "1.5")
    assert short_answer_matches("y = x", "$y=x$")
    assert not short_answer_matches("y=-x", "$y=x$")


def test_grading_tracks_each_question_type_and_topic():
    bank = {
        "multiple_choice": [{
            "id": "mc1", "topic": "Đạo hàm", "answer": "A", "solution": "Giải 1",
        }],
        "true_false": [{
            "topic": "Hình học", "items": [
                {"id": "tf1", "answer": "Đúng", "solution": "Giải 2"},
                {"id": "tf2", "answer": "Sai", "solution": "Giải 3"},
            ],
        }],
        "short_answer": [{
            "id": "sa1", "topic": "Tích phân", "answer": "1.5", "solution": "Giải 4",
        }],
    }
    details, correct, total, topics = grade(
        bank,
        {"mc1": "A", "tf1": "Đúng", "tf2": "Đúng", "sa1": "1,5"},
        answer_display=lambda value: str(value),
    )
    assert total == 4
    assert correct == 3
    assert [detail["correct"] for detail in details] == [True, True, False, True]
    assert topics == {"Đạo hàm": [1, 1], "Hình học": [1, 2], "Tích phân": [1, 1]}


def test_grading_handles_an_empty_bank_without_inventing_results():
    details, correct, total, topics = grade({}, {}, answer_display=str)
    assert details == []
    assert (correct, total, topics) == (0, 0, {})
