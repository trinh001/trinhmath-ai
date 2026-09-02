from pathlib import Path
from tempfile import TemporaryDirectory

from converter.question_parser import parse_document_pages
from converter.storage import ConverterStore
from converter.post_ocr_service import parse_available_documents


def page(number: int, text: str, latex=None, image=None):
    return {"page_number": number, "raw_ocr_text": text, "latex": latex or [], "image_ref": image}


# Clean A/B/C/D question, with formula preserved.
result = parse_document_pages([page(1, "Câu 1. Tính $x^2$ khi x = 2.\nA. 2\nB. 4\nC. 6\nD. 8\nĐáp án: B", ["x^2"], "q1.png")])
assert len(result["questions"]) == 1
q1 = result["questions"][0]
assert q1["question_type"] == "multiple_choice" and q1["correct_answer"] == "B"
assert [item["label"] for item in q1["options"]] == ["A", "B", "C", "D"]
assert "x^2" in q1["question_math"] and q1["images"] == ["q1.png"]

# OCR line wrapping and multi-line option content.
result = parse_document_pages([page(1, "2. Chọn mệnh đề đúng\nA) Dòng đầu\nDòng tiếp của A\nB) Sai\nC) Sai\nD) Sai")])
assert "Dòng tiếp" in result["questions"][0]["options"][0]["content"]

# Incomplete options are retained and flagged, not discarded.
result = parse_document_pages([page(1, "Câu 3: Thiếu phương án\nA. Một\nB. Hai\nC. Ba")])
assert "incomplete_abcd_options" in result["questions"][0]["flags"]

# True/false, short answer and essay types.
result = parse_document_pages([page(1, "Câu 4. Chọn đúng hoặc sai: mệnh đề sau.\na) 1 + 1 = 2\nb) 1 + 1 = 3\nCâu 5. Trả lời ngắn: Tính 2+2.\nCâu 6. Tự luận: Chứng minh bất đẳng thức.")])
assert [q["question_type"] for q in result["questions"]] == ["true_false", "short_answer", "essay"]

# A short-answer key may itself be LaTeX rather than an A/B/C/D label.
result = parse_document_pages([page(1, "Question 9: Tính tích phân.\nĐáp án: $\\frac{1}{2}$")])
assert result["questions"][0]["correct_answer"] == "$\\frac{1}{2}$"
assert "\\frac{1}{2}" in result["questions"][0]["question_math"]

# A question continuing at the top of the next page is preserved as one object.
result = parse_document_pages([page(1, "Câu 7. Cho tam giác ABC có\nA. lựa chọn 1"), page(2, "phần còn lại của giả thiết.\nB. lựa chọn 2\nC. lựa chọn 3\nD. lựa chọn 4")])
q7 = result["questions"][0]
assert q7["source_page_end"] == 2 and "possible_cross_page_question" in q7["flags"]
assert len(q7["options"]) == 4

# Header/footer and text before a question remain visible as unassigned data.
result = parse_document_pages([page(1, "Mã đề 101\nNội dung rác OCR\nCâu 8. Nội dung hợp lệ")])
assert result["unassigned_blocks"] and result["unassigned_blocks"][0]["text"] == "Nội dung rác OCR"

# Storage integration: parser receives existing OCR rows and stores a separate result.
with TemporaryDirectory() as temporary:
    root = Path(temporary)
    image = root / "page.png"
    image.write_bytes(b"fake")
    store = ConverterStore(root / "converter.db")
    doc_id = store.register_document(image, "IMAGE", [{"number": 1, "classification": "SCAN_PAGE", "text": ""}])
    job = store.next_waiting_job()
    store.save_result(job["page_id"], "test-key", "Câu 1. Chọn A.\nA. Đúng\nB. Sai\nC. Sai\nD. Sai", [], {})
    store.set_job(job["id"], "SUCCESS", "test")
    outcome = parse_available_documents(store)
    assert outcome["documents"] == 1 and outcome["questions"] == 1
    assert store.parsed_summary()["questions"] == 1
    assert store.parsed_questions(1)[0]["document_id"] == doc_id

print("QUESTION_PARSER=OK")
