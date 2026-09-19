from source_quality import source_content_quality_issues


def test_detects_missing_math_placeholders_and_unbalanced_latex():
    issues = source_content_quality_issues({
        "question_text": "Tính tổng.",
        "solution_text": "Gọi  lần lượt là các số hạng. Ta có: , , . Kết quả là . $\\left(x+1$",
    })
    assert len(issues) >= 3
    assert any("mất" in issue for issue in issues)
    assert any("không cân bằng" in issue for issue in issues)


def test_clean_source_is_not_flagged():
    assert source_content_quality_issues({
        "question_text": "Tính tổng 1 đến 10.",
        "solution_text": "Ta có tổng là 55. Đáp án: 55.",
    }) == []
