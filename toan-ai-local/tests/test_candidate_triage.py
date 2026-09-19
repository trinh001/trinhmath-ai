from candidate_triage import triage_candidate, triage_candidates


def base_candidate(**overrides):
    candidate = {
        "candidate_id": "demo::q1",
        "question_text": "Tính giá trị biểu thức.",
        "solution_text": "Đáp án: 2. Vì thay số vào biểu thức ta được kết quả bằng hai.",
        "eligible_for_text_pipeline": True,
        "boundary_issue": False,
        "requires_visual_review": False,
        "has_legacy_mathtype": False,
        "lesson": "Bài 1",
        "source_name": "demo.docx",
    }
    candidate.update(overrides)
    return candidate


def test_group_a_requires_clear_text_answer_and_explanation():
    triage = triage_candidate(base_candidate())
    assert triage["group"] == "A"


def test_group_b_has_clear_answer_but_not_enough_explanation():
    triage = triage_candidate(base_candidate(solution_text="Đáp số: 2"))
    assert triage["group"] == "B"


def test_group_c_requires_visual_verification_when_source_exists():
    triage = triage_candidate(base_candidate(
        requires_visual_review=True,
        source_image_names=["word/media/image1.png"],
    ))
    assert triage["group"] == "C"


def test_group_d_blocks_boundary_and_missing_data():
    assert triage_candidate(base_candidate(boundary_issue=True))["group"] == "D"
    assert triage_candidate(base_candidate(question_text=""))["group"] == "D"


def test_summary_orders_clear_text_before_other_groups():
    summary = triage_candidates([
        base_candidate(candidate_id="d", boundary_issue=True),
        base_candidate(candidate_id="c", requires_visual_review=True, source_image_names=["image.png"]),
        base_candidate(candidate_id="b", solution_text="Đáp án: 2"),
        base_candidate(candidate_id="a"),
    ])
    assert summary["counts"] == {"A": 1, "B": 1, "C": 1, "D": 1}
    assert [row["group"] for row in summary["rows"]] == ["A", "B", "C", "D"]
