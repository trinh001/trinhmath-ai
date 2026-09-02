import sqlite3
from pathlib import Path

import app
from health_checks import audit_data_links, has_data_link_errors, validate_curricula


bank = app.load_bank()
assert app.build_exam_pdf(bank, True).startswith(b"%PDF")
assert "\\overrightarrow" in app.normalize_pdf_math("vectơ AB = (1; 2; 3)")
assert "\\int_{0}^{1}" in app.normalize_pdf_math("∫₀¹ 3x² dx bằng")
assert app.get_candidates()
assert Path("backups").exists()
tables = {row[0] for row in sqlite3.connect("results.db").execute("select name from sqlite_master where type='table'")}
assert {"users", "attempts"} <= tables
assert not validate_curricula(app.load_curriculum)
audit = audit_data_links(app.get_sources(), app.get_candidates(), app.get_quiz_variants(), app.SOURCES_DIR)
assert not has_data_link_errors(audit), audit
assert app.detect_source_metadata("Lop 11 Bai 6 Cap so cong.docx")[2].startswith("Bài 6")
assert app.detect_source_metadata("Lop 10 Bai 24 Hoan vi.docx")[2].startswith("Bài 24")
assert app.detect_source_metadata("Lop 12 De thi thu TN THPT.docx")[3] == "Thi thử & đề THPT Quốc gia"
wrapped_image_result = '[{"confidence": 0.9, "needs_teacher_review": false, "math_topic": "Tích phân"}]'
assert app.normalize_ai_image_result(wrapped_image_result)["math_topic"] == "Tích phân"
assert app.is_ai_image_safe_to_use(wrapped_image_result)
print(f"OK: candidates={len(app.get_candidates())}, ready_multiple_choice={len(app.get_ready_export_bank()['multiple_choice'])}.")
