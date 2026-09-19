from adaptive_learning import (
    build_next_practice_recommendation,
    cognitive_level_band,
    practice_difficulty_plan,
    select_adaptive_question_ids,
)
from grading import grade


def test_recommendation_prioritizes_weak_topic():
    route = build_next_practice_recommendation({"Lượng giác": [0, 2], "Đạo hàm": [2, 2]})
    assert route["stage"] == "Củng cố nền tảng"
    assert route["focus_topics"] == ["Lượng giác"]
    assert route["difficulty"] == "Nhận biết → Thông hiểu"


def test_recommendation_handles_empty_or_malformed_data():
    route = build_next_practice_recommendation({"Lỗi": ["x"], "Trống": [0, 0]})
    assert route["stage"] == "Chưa đủ dữ liệu"


def test_cognitive_bands_handle_vietnamese_diacritics():
    assert cognitive_level_band("Vận dụng cao") == "stretch"
    assert cognitive_level_band("Thông hiểu") == "standard"
    assert cognitive_level_band("Nhan biet") == "foundation"


def test_adaptive_selection_keeps_safe_fallback_for_small_bank():
    questions = [
        ("base", {"cognitive_level": "Nhận biết"}),
        ("standard", {"cognitive_level": "Thông hiểu"}),
        ("advanced", {"cognitive_level": "Vận dụng"}),
    ]
    selected = select_adaptive_question_ids(questions, 2, practice_difficulty_plan(0.4))
    assert set(selected) == {"base", "standard"}


def test_difficulty_thresholds_are_stable():
    assert practice_difficulty_plan(0.59)["code"] == "foundation"
    assert practice_difficulty_plan(0.6)["code"] == "standard"
    assert practice_difficulty_plan(0.8)["code"] == "advanced"


def test_graded_practice_result_drives_the_same_next_practice_route():
    bank = {
        "multiple_choice": [
            {"id": "weak-1", "topic": "Lượng giác", "answer": "A", "solution": "Giải"},
            {"id": "strong-1", "topic": "Đạo hàm", "answer": "B", "solution": "Giải"},
        ]
    }
    _, correct, total, topic_results = grade(
        bank,
        {"weak-1": "B", "strong-1": "B"},
        answer_display=str,
    )

    route = build_next_practice_recommendation(topic_results)

    assert (correct, total) == (1, 2)
    assert route["stage"] == "Củng cố nền tảng"
    assert route["focus_topics"] == ["Lượng giác"]
