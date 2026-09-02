from pathlib import Path
from converter.matching import dry_run

candidates = [
 {"candidate_id":"a::q1","source_file":"a.docx","question_number":"1","question_text":"Tính giá trị của x^2", "source_image_names":["word/media/a.png"]},
 {"candidate_id":"b::q1","source_file":"b.docx","question_number":"1","question_text":"Tìm tập nghiệm phương trình", "source_image_names":["word/media/b.png"]},
]
image = str(Path("a.png").resolve())
draft = {"id":1,"question_number":1,"question_text":"Tính giá trị x^2", "question_math":["x^2"],"question_type":"multiple_choice","options":[{"label":"A","content":"1"},{"label":"B","content":"2"},{"label":"C","content":"3"},{"label":"D","content":"4"}],"raw_ocr_text":"Câu 1", "flags":[], "images":[image]}
manifest = {image:{"source_file":"a.docx","image_name":"word/media/a.png"}}
outcome = dry_run([draft], candidates, manifest)[0]
assert outcome["matched_candidate_id"] == "a::q1" and outcome["validation"]["pass"]
# Same number in another file must not win.
assert outcome["top_matches"][0]["breakdown"]["source"] == 1
# Bad options become review-required even with a source match.
draft["options"] = [{"label":"A","content":"1"}]
assert dry_run([draft], candidates, manifest)[0]["status"] == "REVIEW_REQUIRED"
print("MATCHING=OK")
