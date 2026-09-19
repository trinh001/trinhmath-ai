import json
import sqlite3
from pathlib import Path

import app
from health_checks import audit_data_links, has_data_link_errors, validate_curricula
from source_analyzer import build_candidates


bank = app.load_bank()
app.init_database()
assert app.build_exam_pdf(bank, True).startswith(b"%PDF")
# Kiểm thử trọn vòng chấm bài với một đề hiện có: mọi đáp án đúng phải đạt
# điểm tuyệt đối, gồm trắc nghiệm, đúng/sai và trả lời ngắn.
perfect_answers = {}
for question in bank["multiple_choice"]:
    perfect_answers[question["id"]] = app.math_display_text(question["answer"])
for question in bank["true_false"]:
    for item in question["items"]:
        perfect_answers[item["id"]] = item["answer"]
for question in bank["short_answer"]:
    perfect_answers[question["id"]] = question["answer"]
_, perfect_score, total_items, _ = app.grade(bank, perfect_answers)
assert total_items > 0 and perfect_score == total_items
assert app.exam_duration_minutes("Ôn theo bài học") == 45
assert app.exam_duration_minutes("Thi thử & đề THPT Quốc gia") == 90
assert app.option_text_for_display("A. Hàm số đồng biến") == "Hàm số đồng biến"
assert app.option_text_for_display("$x=2$") == "$x=2$"
assert "\\overrightarrow" in app.normalize_pdf_math("vectơ AB = (1; 2; 3)")
assert "\\int_{0}^{1}" in app.normalize_pdf_math("∫₀¹ 3x² dx bằng")
assert app.get_candidates()
assert Path("backups").exists()
tables = {row[0] for row in sqlite3.connect("results.db").execute("select name from sqlite_master where type='table'")}
assert {"users", "attempts", "topic_attempts"} <= tables
assert isinstance(app.get_topic_learning_summary("__self_check_user__"), list)
assert isinstance(app.get_teacher_topic_summary(), list)
assert not validate_curricula(app.load_curriculum)
audit = audit_data_links(app.get_sources(), app.get_candidates(), app.get_quiz_variants(), app.SOURCES_DIR)
assert not has_data_link_errors(audit), audit
quality_report = app.get_bank_quality_report()
assert isinstance(quality_report["variant_issues"], list)
assert sum(quality_report["triage"]["counts"].values()) == len(app.get_candidates())
assert {row["group"] for row in quality_report["triage"]["rows"]} <= {"A", "B", "C", "D"}
coverage_grade12 = app.get_curriculum_coverage("Lớp 12")
assert coverage_grade12["lessons"]
assert all(item["coverage"] in {"Có thể luyện ngắn", "Cần thêm câu đã duyệt", "Có nguyên liệu, chưa phát hành", "Chưa có dữ liệu"} for item in coverage_grade12["lessons"])
assert app.curriculum_lesson_key("Bài 12. Tích phân") == "bai-12"
development_queue = app.get_curriculum_development_queue("Lớp 12")
assert isinstance(development_queue, list)
assert all(item["action"] and item["ready"] < 3 for item in development_queue)
assert app.detect_source_metadata("Lop 11 Bai 6 Cap so cong.docx")[2].startswith("Bài 6")
assert app.detect_source_metadata("Lop 10 Bai 24 Hoan vi.docx")[2].startswith("Bài 24")
assert app.detect_source_metadata("Lop 12 De thi thu TN THPT.docx")[3] == "Thi thử & đề THPT Quốc gia"
# Word hay dùng dòng "Đáp án" thay vì tiêu đề "Lời giải"; đáp án không được
# dính vào phần đề khi tách câu.
sample_source = {"file_name": "demo.docx", "original_name": "demo.docx"}
sample_candidates = build_candidates(sample_source, [
    "Câu 1. Tính $1+1$.", "Đáp án: 2", "Vì $1+1=2$.",
])
assert len(sample_candidates) == 1
assert "Đáp án" not in sample_candidates[0]["question_text"]
assert sample_candidates[0]["solution_text"].startswith("Đáp án: 2")
inline_candidates = build_candidates(sample_source, [
    "Câu 2. Tính $2+2$. Đáp số: 4", "Vì $2+2=4$.",
])
assert "Đáp số" not in inline_candidates[0]["question_text"]
assert inline_candidates[0]["solution_text"].startswith("Đáp số: 4")
implicit_candidates = build_candidates(sample_source, [
    "Câu 3. Tính $1+1$?", "Đáp án: 2", "Lời giải: $1+1=2$.",
    "Một bài mới không ghi số câu, hãy tính $2+2$?", "Đáp số: 4", "Lời giải: $2+2=4$.",
])
assert len(implicit_candidates) == 2
assert implicit_candidates[1]["question_number"] == "3a"
assert implicit_candidates[1]["implicit_boundary"] is True
wrapped_image_result = '[{"confidence": 0.9, "needs_teacher_review": false, "math_topic": "Tích phân"}]'
assert app.normalize_ai_image_result(wrapped_image_result)["math_topic"] == "Tích phân"
assert app.is_ai_image_safe_to_use(wrapped_image_result)
assert app.is_ai_image_safe_to_use('{"confidence": 0.9, "needs_teacher_review": "false"}')
assert not app.is_ai_image_safe_to_use('{"confidence": 0.9, "needs_teacher_review": "ảnh mờ cần kiểm tra"}')
# Đóng gói cục bộ chỉ được phép với câu trắc nghiệm đã có một đáp án khớp duy nhất.
local_question = {
    "question": {
        "question_type": "multiple_choice",
        "question_latex_or_text": "Tìm $x$ biết $x+1=2$.",
        "options": ["$x=1$", "$x=2$", "$x=-1$", "$x=0$"],
        "correct_answer": "$x=1$",
        "solution_latex_or_text": "$x=1$.",
        "topic": "Phương trình",
        "cognitive_level": "Nhận biết",
    }
}
local_ok, local_variant_text = app.create_local_multiple_choice_variant(local_question)
assert local_ok
local_variant = json.loads(local_variant_text)
assert local_variant["correct_answer"] == "A" and len(local_variant["options"]) == 4
assert not app.validate_quiz_variant_for_student(local_variant)
assert app.explicit_solution_answer_labels("Lời giải.\nĐáp án: C.") == {"C"}
inconsistent_variant = dict(local_variant)
inconsistent_variant["solution"] = "Ta giải được nghiệm cần chọn.\nĐáp án: B."
assert any("không khớp" in item for item in app.validate_quiz_variant_for_student(inconsistent_variant))
broken_variant = dict(local_variant)
broken_variant["options"] = ["$x=1$", "$x=1$", "$x=-1$", ""]
broken_variant["correct_answer"] = "E"
broken_errors = app.validate_quiz_variant_for_student(broken_variant)
assert any("rỗng" in item for item in broken_errors)
assert any("trùng" in item for item in broken_errors)
assert any("A, B, C hoặc D" in item for item in broken_errors)
local_question["question"]["correct_answer"] = "$x=3$"
local_ok, _ = app.create_local_multiple_choice_variant(local_question)
assert not local_ok
# Tự luận chỉ được chuyển cục bộ khi đáp án là một kết quả LaTex ngắn duy nhất.
short_answer_question = {
    "question": {
        "question_type": "essay",
        "question_latex_or_text": "Tìm tiệm cận xiên của $y=x+\\frac{1}{x+1}$.",
        "correct_answer": "Đường tiệm cận xiên là $y=x$.",
        "solution_latex_or_text": "Ta có $\\lim_{x\\to\\pm\\infty}(y-x)=0$.",
        "topic": "Đường tiệm cận",
        "cognitive_level": "Thông hiểu",
    }
}
short_ok, short_variant_text = app.create_local_short_answer_variant(short_answer_question)
assert short_ok
assert json.loads(short_variant_text)["correct_answer"] == "$y=x$"
short_answer_question["question"]["correct_answer"] = "Học sinh tự vẽ đồ thị theo các bước."
short_ok, _ = app.create_local_short_answer_variant(short_answer_question)
assert not short_ok
assert app.short_answer_matches("y = x", "$y=x$")
assert app.short_answer_matches("1,5", "1.5")
assert not app.short_answer_matches("y = -x", "$y=x$")
# Lộ trình sau lượt làm phải dựa đúng vào tỷ lệ của từng chủ đề: phần yếu
# được củng cố trước, còn khi đã tốt thì mới khuyến khích tăng độ khó.
weak_route = app.build_next_practice_recommendation({"Phương trình lượng giác": [0, 2], "Đạo hàm": [2, 2]})
assert weak_route["stage"] == "Củng cố nền tảng"
assert weak_route["focus_topics"] == ["Phương trình lượng giác"]
steady_route = app.build_next_practice_recommendation({"Tích phân": [3, 5]})
assert steady_route["stage"] == "Luyện chắc"
strong_route = app.build_next_practice_recommendation({"Hình học không gian": [4, 4], "Xác suất": [3, 3]})
assert strong_route["stage"] == "Mở rộng"
assert strong_route["difficulty"] == "Thông hiểu → Vận dụng"
assert app.cognitive_level_band("Vận dụng cao") == "stretch"
assert app.cognitive_level_band("Thông hiểu") == "standard"
foundation_plan = app.practice_difficulty_plan(0.4)
assert foundation_plan["code"] == "foundation"
adaptive_ids = app.select_adaptive_question_ids([
    ("base", {"cognitive_level": "Nhận biết"}),
    ("standard", {"cognitive_level": "Thông hiểu"}),
    ("advanced", {"cognitive_level": "Vận dụng"}),
], 2, foundation_plan)
assert set(adaptive_ids) == {"base", "standard"}
assert app.practice_difficulty_plan(0.9)["code"] == "advanced"
# Parser cục bộ chỉ nhận mẫu A/B/C/D kèm đáp án ghi rõ; không đoán câu thiếu.
strict_candidate = {
    "eligible_for_text_pipeline": True,
    "question_text": "Câu 1. Phương trình tương đương là gì? A. Cùng tập xác định. B. Cùng số nghiệm. C. Cùng dạng. D. Cùng tập nghiệm.",
    "solution_text": "Chọn D. Theo định nghĩa, hai phương trình có cùng tập nghiệm.",
    "lesson": "Phương trình",
}
strict_draft = app.parse_strict_local_multiple_choice(strict_candidate)
assert strict_draft and strict_draft["correct_answer"] == "Cùng tập nghiệm."
strict_candidate["solution_text"] = "Lời giải chưa nêu đáp án."
assert app.parse_strict_local_multiple_choice(strict_candidate) is None
numeric_candidate = {
    "eligible_for_text_pipeline": True,
    "question_text": "Câu 2. Tính tổng số ghế trong rạp hát.",
    "solution_text": "Đáp số: 900\nVì tổng các hàng ghế được tính theo công thức cấp số cộng.",
    "lesson": "Cấp số cộng",
}
numeric_draft = app.parse_strict_local_short_answer(numeric_candidate)
assert numeric_draft and numeric_draft["correct_answer"] == "900"
numeric_candidate["solution_text"] = "Đáp số: 900"
assert app.parse_strict_local_short_answer(numeric_candidate) is None
numeric_candidate["solution_text"] = "Đáp án: $x=2$"
assert app.parse_strict_local_short_answer(numeric_candidate) is None
numeric_candidate["question_text"] = "Câu 2. Đề bị dính câu sau. Đáp án: 99"
numeric_candidate["solution_text"] = "Lời giải đang dở.\nĐáp án: 99"
assert app.parse_strict_local_short_answer(numeric_candidate) is None
assert app.detect_candidate_boundary_issue({"question_text": "Câu 1. Nội dung. Đáp án: 9", "solution_text": ""})
assert not app.detect_candidate_boundary_issue({"question_text": "Câu 1. Tính $1+1$.", "solution_text": "Đáp án: 2"})
assert not app.detect_candidate_boundary_issue({"question_text": "Câu 1. Tính quãng đường.", "solution_text": "Đáp án: $144$\\nĐáp số: 144"})
assert app.detect_source_grade("TONG_HOP_TOAN_12_NEW.docx") == "Lớp 12"
# MathType cũ trong Word lưu công thức thành WMF/OLE, không có m:oMath.
# Phải nhận diện riêng và render lại vector ở DPI cao thay vì gửi ảnh vài pixel.
legacy_candidate = next(item for item in app.get_candidates() if item.get("question_text", "").startswith("Bài tập 4:  Thể tích"))
assert legacy_candidate.get("has_legacy_mathtype")
legacy_names = legacy_candidate.get("legacy_math_image_names") or []
assert len(legacy_names) == 7
legacy_images, legacy_error = app.get_docx_images(
    app.SOURCES_DIR / legacy_candidate["source_file"], set(legacy_names), set(legacy_names)
)
assert not legacy_error and all(item.get("render_dpi") == 600 for item in legacy_images)
affected_formula_candidate = next(item for item in app.get_candidates() if item.get("candidate_id", "").endswith("Bài_01_Dạng_01._Lý_thuyết_về_tính_đơn_điệu,_cực_trị_của_hàm_số_cho_trước_GV.docx::q1"))
formula_retry, damaged_formulas, formula_retry_error = app.get_formula_images_needing_retry(affected_formula_candidate)
assert not formula_retry_error and "word/media/image105.wmf" in damaged_formulas
# Gemini đôi khi chèn newline thật trong lời giải dù JSON yêu cầu chuỗi một dòng.
# App cần khôi phục trường hợp này, nhưng không được đoán phần JSON bị cắt dở.
draft_with_raw_linebreak = '{"usable": true, "question_latex_or_text": "Tính đạo hàm", "solution_latex_or_text": "Bước 1\nBước 2"}'
assert app.parse_ai_draft_json(draft_with_raw_linebreak)["solution_latex_or_text"] == "Bước 1\nBước 2"
# JSON hợp lệ vẫn không được phát hành nếu model để null ở đáp án/lời giải.
incomplete_draft, incomplete_issue = app.normalize_question_draft_for_review({
    "usable": True,
    "question_type": "essay",
    "question_latex_or_text": "Tìm các khoảng đồng biến.",
    "correct_answer": None,
    "solution_latex_or_text": None,
})
assert incomplete_issue and incomplete_draft["usable"] is False
assert incomplete_draft["correct_answer"] == "" and incomplete_draft["solution_latex_or_text"] == ""
assert app.draft_student_text_quality_issue({
    "question_latex_or_text": "a) a) $y=x^2$ (hoặc tương tự theo ảnh 1 bị lỗi)",
})
assert not app.draft_student_text_quality_issue({
    "question_latex_or_text": "a) $y=x^2$\\nb) $y=x+1$",
})
try:
    app.parse_ai_draft_json('{"usable": true, "question_latex_or_text": "Câu bị cắt')
except json.JSONDecodeError:
    pass
else:
    raise AssertionError("Không được tự nhận câu JSON bị cắt dở là hợp lệ.")
print(f"OK: candidates={len(app.get_candidates())}, ready_multiple_choice={len(app.get_ready_export_bank()['multiple_choice'])}.")
