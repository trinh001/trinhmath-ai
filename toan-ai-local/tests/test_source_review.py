from source_review import (
    build_local_review_queue,
    build_local_source_batches,
    build_source_review_snapshot,
    prioritize_draft_ids_for_review,
)


def test_snapshot_keeps_every_visual_and_its_read_state():
    candidate = {
        "source_file": "de.docx",
        "source_name": "Đề mẫu",
        "question_number": 3,
        "question_text": "Tính $x$.",
        "solution_text": "Đáp án: 2. Vì thay vào được 0.",
        "source_image_names": ["word/media/a.png", "word/media/a.png"],
        "legacy_math_image_names": ["word/media/formula.wmf"],
        "has_legacy_mathtype": True,
    }
    analyses = {
        "de.docx::word/media/a.png": {
            "read_status": "Đã đọc",
            "usage_status": "Đủ tin cậy để dùng tự động",
            "safe_to_use": True,
            "result": '{"confidence": 0.91, "needs_teacher_review": false}',
        }
    }

    snapshot = build_source_review_snapshot(candidate, analyses)

    assert snapshot["question_text"] == "Tính $x$."
    assert len(snapshot["visuals"]) == 2
    assert snapshot["visuals"][0]["safe_to_use"] is True
    assert snapshot["visuals"][0]["confidence"] == 0.91
    assert snapshot["visuals"][1]["read_status"] == "Chưa đọc"
    assert snapshot["visuals"][1]["kind"] == "MathType/công thức cũ"


def test_snapshot_retains_source_quality_warning():
    snapshot = build_source_review_snapshot(
        {"question_text": "Tính tổng.", "solution_text": "Gọi  lần lượt là các số."},
        {},
    )
    assert snapshot["source_issues"]
    assert snapshot["requires_visual_review"] is False


def test_snapshot_treats_confirmed_overlapping_mathtype_as_a_source_block():
    candidate = {
        "source_file": "damaged.docx",
        "question_text": "Tìm cực trị.",
        "solution_text": "Đáp án cần đối chiếu từ nguồn.",
        "legacy_math_image_names": ["word/media/formula.wmf"],
        "has_legacy_mathtype": True,
    }
    analyses = {
        "damaged.docx::word/media/formula.wmf": {
            "read_status": "Đã đọc",
            "result": '{"confidence": 0, "needs_teacher_review": "Công thức bị chồng chéo."}',
        }
    }

    snapshot = build_source_review_snapshot(candidate, analyses)

    assert snapshot["fatal_formula_issues"]
    assert any("chồng nét" in issue for issue in snapshot["source_issues"])


def test_local_queue_blocks_the_entire_source_batch_after_confirmed_formula_damage():
    drafts = {
        "formula": {"provenance": "strict_local_short_answer_parser", "status": "Bản nháp cục bộ"},
        "neighbor": {"provenance": "strict_local_short_answer_parser", "status": "Bản nháp cục bộ"},
    }
    candidates = [
        {
            "candidate_id": "formula", "source_file": "damaged.docx", "source_name": "Tệp lỗi",
            "question_text": "Tìm cực trị.", "solution_text": "Đáp án: 2. Vì thay vào đúng.",
            "legacy_math_image_names": ["word/media/formula.wmf"], "has_legacy_mathtype": True,
        },
        {
            "candidate_id": "neighbor", "source_file": "damaged.docx", "source_name": "Tệp lỗi",
            "question_text": "Tính tổng.", "solution_text": "Đáp án: 3. Vì cộng các số hạng.",
        },
    ]
    analyses = {
        "damaged.docx::word/media/formula.wmf": {
            "read_status": "Đã đọc",
            "result": '{"confidence": 0, "needs_teacher_review": "Formula is overlapping."}',
        }
    }

    queue = build_local_review_queue(drafts, candidates, analyses)

    assert queue["counts"]["blocked_by_source"] == 2
    assert {row["bucket"] for row in queue["rows"]} == {"blocked_by_source"}
    assert queue["blocked_batches"][0]["local_draft_count"] == 2


def test_local_review_queue_prioritizes_clean_sources_and_keeps_blocks_visible():
    drafts = {
        "clean": {"provenance": "strict_local_short_answer_parser", "status": "Bản nháp cục bộ"},
        "broken": {"provenance": "strict_local_short_answer_parser", "status": "Bản nháp cục bộ"},
        "other": {"provenance": "gemini", "status": "Bản nháp AI"},
    }
    candidates = [
        {"candidate_id": "clean", "question_text": "Tính.", "solution_text": "Đáp án: 2. Vì thay vào đúng.", "lesson": "Bài 1"},
        {"candidate_id": "broken", "question_text": "Tính.", "solution_text": "Gọi  lần lượt là các số.", "lesson": "Bài 2"},
    ]

    queue = build_local_review_queue(drafts, candidates, {})

    assert queue["counts"]["ready_for_comparison"] == 1
    assert queue["counts"]["blocked_by_source"] == 1
    assert len(queue["rows"]) == 2
    assert queue["rows"][0]["candidate_id"] == "clean"


def test_draft_picker_puts_clean_local_comparisons_before_broken_legacy_drafts():
    queue = {
        "rows": [
            {"candidate_id": "clean-local", "bucket": "ready_for_comparison"},
            {"candidate_id": "visual-local", "bucket": "needs_visual_review"},
            {"candidate_id": "blocked-local", "bucket": "blocked_by_source"},
        ]
    }

    ordered = prioritize_draft_ids_for_review(
        ["blocked-local", "old-draft", "visual-local", "clean-local"],
        ["old-draft"],
        queue,
    )

    assert ordered == ["clean-local", "old-draft", "visual-local", "blocked-local"]


def test_source_batches_group_queue_rows_without_changing_their_review_bucket():
    batches = build_local_source_batches({
        "rows": [
            {
                "candidate_id": "one", "source_file": "same.docx", "source_name": "Cùng nguồn",
                "bucket": "blocked_by_source", "reason": "Thiếu đề bài nguồn.",
            },
            {
                "candidate_id": "two", "source_file": "same.docx", "source_name": "Cùng nguồn",
                "bucket": "ready_for_comparison", "reason": "Sẵn sàng để giáo viên đối chiếu.",
            },
            {
                "candidate_id": "three", "source_file": "other.docx", "source_name": "Nguồn khác",
                "bucket": "needs_visual_review", "reason": "Cần xem ảnh.",
            },
        ]
    })

    assert [batch["source_file"] for batch in batches] == ["same.docx", "other.docx"]
    assert batches[0]["candidate_ids"] == ["one", "two"]
    assert batches[0]["counts"]["blocked_by_source"] == 1
    assert batches[0]["counts"]["ready_for_comparison"] == 1
    assert batches[0]["reasons"] == ["Thiếu đề bài nguồn.", "Sẵn sàng để giáo viên đối chiếu."]
