from curriculum_coverage import build_curriculum_coverage, build_development_queue, curriculum_lesson_key


CURRICULUM = [{"chapter": "Chương I", "lessons": ["Bài 1. Hàm số", "Bài 2. Đạo hàm", "Bài 3. Tích phân"]}]


def test_coverage_counts_only_requested_grade_and_reports_unmapped_ready():
    coverage = build_curriculum_coverage(
        CURRICULUM,
        "Lớp 12",
        [{"candidate_id": "a", "grade": "Lớp 12", "lesson": "Bài 1. Hàm số"}, {"grade": "Lớp 11", "lesson": "Bài 1"}],
        [{"grade": "Lớp 12", "lesson": "Bài 1. Hàm số"}],
        [{"grade": "Lớp 12", "lesson": "Bài 2. Đạo hàm"}, {"grade": "Lớp 12", "lesson": "Không ghép được"}],
    )
    rows = {row["key"]: row for row in coverage["lessons"]}
    assert rows["bai-1"]["coverage"] == "Có nguyên liệu, chưa phát hành"
    assert rows["bai-2"]["coverage"] == "Cần thêm câu đã duyệt"
    assert coverage["unmapped_ready"] == 1


def test_development_queue_prefers_approved_then_safe_text_then_visual():
    coverage = build_curriculum_coverage(
        CURRICULUM,
        "Lớp 12",
        [
            {"candidate_id": "one", "grade": "Lớp 12", "lesson": "Bài 1. Hàm số"},
            {"candidate_id": "two", "grade": "Lớp 12", "lesson": "Bài 2. Đạo hàm"},
        ],
        [{"grade": "Lớp 12", "lesson": "Bài 1. Hàm số"}],
        [],
    )
    queue = build_development_queue(coverage, [
        {"candidate_id": "one", "lesson": "Bài 1. Hàm số"},
        {"candidate_id": "two", "lesson": "Bài 2. Đạo hàm"},
    ], {"two"})
    assert queue[0]["lesson"].startswith("Bài 1") and queue[0]["priority"] == 0
    assert queue[1]["lesson"].startswith("Bài 2") and queue[1]["priority"] == 1


def test_lesson_key_handles_extra_lesson_text():
    assert curriculum_lesson_key("Bài 12. Tích phân") == "bai-12"
    assert curriculum_lesson_key("Bài 12 - đề luyện") == "bai-12"
