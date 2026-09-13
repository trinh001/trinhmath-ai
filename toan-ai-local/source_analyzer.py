"""Bộ tách câu hỏi cục bộ cho tài liệu Word trong kho đề.

Đây là lớp tiền xử lý: giữ lại tệp gốc, tách các đoạn "Câu n" và đánh dấu
những tệp có công thức/hình nhúng để AI hoặc giáo viên kiểm tra ở bước sau.
"""

import html
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

try:
    from pypdf import PdfReader
except ImportError:  # Giữ app mở được nếu môi trường chưa cài phần đọc PDF.
    PdfReader = None


QUESTION_RE = re.compile(r"^\s*(?:Câu\s*|Bài(?:\s+tập)?\s*)(\d+)\s*[\.:]", re.IGNORECASE)
ANSWER_MARKER_RE = re.compile(r"^\s*(?:đáp\s*án|đáp\s*số|kết\s*quả)\s*[:\-]?", re.IGNORECASE)
# Some Word exports omit the space before the marker (``làĐáp án:``).  Do not
# require a word boundary here; the marker itself is distinctive and is later
# validated by the question-boundary safeguards.
INLINE_ANSWER_MARKER_RE = re.compile(r"(?i)(?:đáp\s*án|đáp\s*số|kết\s*quả)\s*[:\-]?")
IMPLICIT_QUESTION_HINT_RE = re.compile(
    r"(?i)\b(?:tính|hỏi|xác\s*định|cho\s*biết|tìm|bao\s*nhiêu|giá\s*trị)\b"
)


def _local_name(element):
    return element.tag.rsplit("}", 1)[-1]


def _child(element, name):
    return next((item for item in element if _local_name(item) == name), None)


def _math_text(element):
    if element is None:
        return ""
    return "".join(node.text or "" for node in element.iter() if _local_name(node) == "t")


def ooxml_math_to_latex(element):
    """Chuyển phần OOXML Math thông dụng của Word sang LaTex tại máy.

    Hàm ưu tiên không mất dữ kiện: cấu trúc không nhận ra vẫn giữ phần chữ thay
    vì đoán công thức. Đây là trích xuất, không phải OCR nên không tốn quota AI.
    """
    name = _local_name(element)
    if name in {"oMath", "oMathPara", "e", "num", "den", "sub", "sup", "deg", "lim", "arg", "base"}:
        return "".join(ooxml_math_to_latex(child) for child in element)
    if name in {"r", "t"}:
        return _math_text(element)
    if name == "f":
        return r"\frac{" + ooxml_math_to_latex(_child(element, "num") or element) + "}{" + ooxml_math_to_latex(_child(element, "den") or element) + "}"
    if name == "rad":
        degree = _child(element, "deg")
        body = ooxml_math_to_latex(_child(element, "e") or element)
        return (r"\sqrt[" + ooxml_math_to_latex(degree) + "]{" + body + "}") if degree is not None else r"\sqrt{" + body + "}"
    if name == "sSup":
        return ooxml_math_to_latex(_child(element, "e") or element) + "^{" + ooxml_math_to_latex(_child(element, "sup") or element) + "}"
    if name == "sSub":
        return ooxml_math_to_latex(_child(element, "e") or element) + "_{" + ooxml_math_to_latex(_child(element, "sub") or element) + "}"
    if name == "sSubSup":
        return (ooxml_math_to_latex(_child(element, "e") or element) + "_{" + ooxml_math_to_latex(_child(element, "sub") or element)
                + "}^{" + ooxml_math_to_latex(_child(element, "sup") or element) + "}")
    if name == "nary":
        props = _child(element, "naryPr")
        character = _math_text(_child(props, "chr")) if props is not None else ""
        symbol = {"∫": r"\int", "∑": r"\sum", "∏": r"\prod"}.get(character, r"\int")
        sub, sup = _child(element, "sub"), _child(element, "sup")
        limits = ("_{" + ooxml_math_to_latex(sub) + "}") if sub is not None else ""
        limits += ("^{" + ooxml_math_to_latex(sup) + "}") if sup is not None else ""
        return symbol + limits + " " + ooxml_math_to_latex(_child(element, "e") or element)
    if name == "d":
        return r"\left(" + ooxml_math_to_latex(_child(element, "e") or element) + r"\right)"
    return "".join(ooxml_math_to_latex(child) for child in element)


def has_visual_math(path):
    try:
        with zipfile.ZipFile(path) as archive:
            document_xml = archive.read("word/document.xml")
            has_equation = b"<m:oMath" in document_xml or b"<m:oMathPara" in document_xml
            has_media = any(name.startswith("word/media/") for name in archive.namelist())
            return has_equation or has_media
    except (KeyError, zipfile.BadZipFile):
        return False


def has_ooxml_math(path):
    """Kiểm tra công thức Word dạng OOXML; khác với ảnh minh họa VML/WMF."""
    try:
        with zipfile.ZipFile(path) as archive:
            document_xml = archive.read("word/document.xml")
        return b"<m:oMath" in document_xml or b"<m:oMathPara" in document_xml
    except (KeyError, zipfile.BadZipFile):
        return False


def read_docx_paragraphs(path):
    """Đọc chữ Word và chuyển công thức OOXML thành LaTex ngay tại máy."""
    paragraph_tag = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"
    with zipfile.ZipFile(path) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    paragraphs = []
    for paragraph in root.iter(paragraph_tag):
        parts = []

        def visit(node):
            node_name = _local_name(node)
            if node_name in {"oMath", "oMathPara"}:
                formula = ooxml_math_to_latex(node).strip()
                if formula:
                    parts.append(f"${formula}$")
                return
            if node_name == "t":
                parts.append(node.text or "")
                return
            for child in node:
                visit(child)

        visit(paragraph)
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def read_pdf_paragraphs(path):
    """Đọc PDF có lớp văn bản chọn được, hoàn toàn tại máy.

    PDF scan thực chất chỉ là ảnh nên ``extract_text`` sẽ rỗng hoặc rất ít chữ.
    Hàm này chủ động trả về danh sách rỗng trong trường hợp đó để luồng sau gắn
    nhãn OCR/AI, thay vì bịa câu hỏi từ dữ liệu không đủ.
    """
    if PdfReader is None:
        return []
    reader = PdfReader(str(path))
    paragraphs = []
    for page in reader.pages:
        text = page.extract_text() or ""
        paragraphs.extend(line.strip() for line in text.replace("\r", "\n").splitlines() if line.strip())
    return paragraphs


def map_docx_question_images(path):
    """Ánh xạ ảnh nhúng vào khung Câu/Bài đứng trước nó trong Word.

    Chỉ ảnh nằm trong phần đề (trước ``Lời giải``) được gắn vào câu. Kết quả
    là gợi ý cục bộ; ảnh không xác định được vị trí sẽ không bị gán bừa.
    """
    # Đọc trực tiếp XML thay vì dựng toàn bộ cây ElementTree. Một số bộ đề có
    # hàng nghìn ảnh WMF/VML; cách này nhanh hơn nhiều và chỉ lấy thông tin cần
    # để nối ảnh với số câu.
    try:
        with zipfile.ZipFile(path) as archive:
            document_xml = archive.read("word/document.xml")
            rels_xml = archive.read("word/_rels/document.xml.rels")
        relation_map = {}
        for relation in re.finditer(rb"<Relationship\b[^>]*\bId=\"([^\"]+)\"[^>]*\bTarget=\"([^\"]+)\"[^>]*/?>", rels_xml):
            relation_id, target = relation.group(1).decode("utf-8", "ignore"), relation.group(2).decode("utf-8", "ignore")
            if "media/" in target:
                relation_map[relation_id] = "word/" + target.lstrip("/")
        result, current_number, section = {}, None, "question"
        for paragraph in re.finditer(rb"<w:p\b[^>]*>.*?</w:p>", document_xml, flags=re.DOTALL):
            raw = paragraph.group(0)
            text_parts = re.findall(rb"<(?:w|m):t\b[^>]*>(.*?)</(?:w|m):t>", raw, flags=re.DOTALL)
            text = html.unescape("".join(part.decode("utf-8", "ignore") for part in text_parts)).strip()
            if text.lower().startswith("lời giải"):
                section = "solution"
            match = QUESTION_RE.match(text)
            if match:
                current_number, section = match.group(1), "question"
                result.setdefault(current_number, [])
            if current_number and section == "question":
                embeds = [value.decode("utf-8", "ignore") for value in re.findall(rb"\br:(?:id|embed)=\"([^\"]+)\"", raw)]
                for embed in embeds:
                    image_name = relation_map.get(embed)
                    if image_name and image_name not in result[current_number]:
                        result[current_number].append(image_name)
        return result
    except (KeyError, zipfile.BadZipFile, UnicodeDecodeError):
        return {}


def map_docx_legacy_math_images(path):
    """Ánh xạ ảnh xem trước của MathType cũ vào từng Câu/Bài.

    Nhiều tài liệu Việt Nam tạo bằng Equation Editor/MathType không chứa
    ``m:oMath`` của Word. Công thức nằm trong OLE ``Equation.DSMT4`` và Word
    kèm một ảnh WMF vector để hiển thị. Đây là dữ kiện toán học, không phải
    hình minh họa; cần giữ riêng để app có thể render/quét lại ở độ phân giải
    cao thay vì coi câu là thiếu công thức.
    """
    try:
        with zipfile.ZipFile(path) as archive:
            document_xml = archive.read("word/document.xml")
            rels_xml = archive.read("word/_rels/document.xml.rels")
        relation_map = {}
        for relation in re.finditer(rb"<Relationship\b[^>]*\bId=\"([^\"]+)\"[^>]*\bTarget=\"([^\"]+)\"[^>]*/?>", rels_xml):
            relation_id, target = relation.group(1).decode("utf-8", "ignore"), relation.group(2).decode("utf-8", "ignore")
            if "media/" in target:
                relation_map[relation_id] = "word/" + target.lstrip("/")
        result, current_number, section = {}, None, "question"
        for paragraph in re.finditer(rb"<w:p\b[^>]*>.*?</w:p>", document_xml, flags=re.DOTALL):
            raw = paragraph.group(0)
            text_parts = re.findall(rb"<(?:w|m):t\b[^>]*>(.*?)</(?:w|m):t>", raw, flags=re.DOTALL)
            text = html.unescape("".join(part.decode("utf-8", "ignore") for part in text_parts)).strip()
            if text.lower().startswith("lời giải"):
                section = "solution"
            match = QUESTION_RE.match(text)
            if match:
                current_number, section = match.group(1), "question"
                result.setdefault(current_number, [])
            if not current_number or section != "question" or b"Equation.DSMT" not in raw:
                continue
            for relation_id in re.findall(rb"<v:imagedata\b[^>]*\br:id=\"([^\"]+)\"", raw):
                image_name = relation_map.get(relation_id.decode("utf-8", "ignore"))
                if image_name and image_name not in result[current_number]:
                    result[current_number].append(image_name)
        return result
    except (KeyError, zipfile.BadZipFile, UnicodeDecodeError):
        return {}


def build_candidates(source, paragraphs, *, requires_visual_review=False):
    candidates, current = [], None
    section = "question"
    implicit_suffix = 0
    for index, text in enumerate(paragraphs):
        next_text = paragraphs[index + 1] if index + 1 < len(paragraphs) else ""
        if text.lower().startswith("lời giải"):
            section = "solution"
            continue
        match = QUESTION_RE.match(text)
        if match:
            if current:
                candidates.append(current)
            # An answer marker can occur on the same line as the question
            # header (for example: "Câu 2. ... Đáp số: 4").  Split it here as
            # well as in continuation paragraphs; otherwise the first answer
            # leaks into question_text before the normal continuation logic
            # gets a chance to run.
            inline_answer = INLINE_ANSWER_MARKER_RE.search(text, match.end())
            question_head = text[:inline_answer.start()].strip() if inline_answer else text
            solution_head = text[inline_answer.start():].strip() if inline_answer else ""
            implicit_suffix = 0
            current = {
                "number": match.group(1),
                "implicit_base": match.group(1),
                "question_parts": [question_head] if question_head else [],
                "solution_parts": [solution_head] if solution_head else [],
            }
            section = "question"
            if solution_head:
                section = "solution"
        elif current:
            # A handful of compiled Word banks omit the next "Câu n:" label.
            # Split only on an unusually strong three-part signal: we are
            # already inside a solved question, this paragraph reads like a
            # full question, and the immediately following paragraph starts
            # an answer.  The new item gets an explicit provisional suffix so
            # it can never masquerade as a numbered source question.
            has_prior_answer = any(ANSWER_MARKER_RE.match(part) for part in current["solution_parts"])
            is_implicit_question = (
                section == "solution" and has_prior_answer and len(text.strip()) >= 30
                and text.strip().endswith("?") and IMPLICIT_QUESTION_HINT_RE.search(text)
                and ANSWER_MARKER_RE.match(next_text or "")
            )
            if is_implicit_question:
                candidates.append(current)
                implicit_suffix += 1
                current = {
                    "number": f"{current.get('implicit_base', current['number'])}{chr(96 + implicit_suffix)}",
                    "implicit_base": current.get("implicit_base", current["number"]),
                    "question_parts": [text],
                    "solution_parts": [],
                    "implicit_boundary": True,
                }
                section = "question"
                continue
            # Many Vietnamese worksheets put "Đáp án: …" directly before the
            # explanation, without a "Lời giải" heading.  Treat it as the
            # solution boundary so the answer cannot leak into question text.
            inline_answer = INLINE_ANSWER_MARKER_RE.search(text) if section == "question" else None
            if inline_answer:
                before_answer = text[:inline_answer.start()].strip()
                answer_and_solution = text[inline_answer.start():].strip()
                if before_answer:
                    current["question_parts"].append(before_answer)
                section = "solution"
                if answer_and_solution:
                    current["solution_parts"].append(answer_and_solution)
            else:
                if section == "question" and ANSWER_MARKER_RE.match(text):
                    section = "solution"
                current[f"{section}_parts"].append(text)
    if current:
        candidates.append(current)

    return [
        {
            "candidate_id": f"{source['file_name']}::q{item['number']}",
            "source_file": source["file_name"],
            "source_name": source["original_name"],
            "grade": source.get("grade", "Chưa phân loại"),
            "chapter": source.get("chapter", "Chưa phân loại"),
            "lesson": source.get("lesson", "Chưa phân loại"),
            "document_kind": source.get("document_kind", "Bộ hỗn hợp / đề hoàn chỉnh"),
            "question_number": item["number"],
            "question_text": "\n".join(item["question_parts"]),
            "solution_text": "\n".join(item["solution_parts"]),
            "requires_visual_review": requires_visual_review,
            "implicit_boundary": bool(item.get("implicit_boundary")),
            "status": "Chờ AI phân loại và giáo viên duyệt"
        }
        for item in candidates
    ]


def extract_docx_candidates(source, path):
    candidates = build_candidates(source, read_docx_paragraphs(path))
    question_images = map_docx_question_images(path)
    legacy_math_images = map_docx_legacy_math_images(path)
    contains_ooxml_math = has_ooxml_math(path)
    for candidate in candidates:
        question_number = str(candidate["question_number"])
        image_names = question_images.get(question_number, [])
        legacy_images = legacy_math_images.get(question_number, [])
        # OOXML Math đã được trích trực tiếp, nên chỉ ảnh minh họa thật mới cần AI đọc.
        candidate["source_image_names"] = image_names
        candidate["legacy_math_image_names"] = legacy_images
        candidate["has_legacy_mathtype"] = bool(legacy_images)
        candidate["contains_ooxml_math"] = contains_ooxml_math
        candidate["math_extraction_status"] = (
            "Có công thức MathType cũ — chờ đọc ảnh vector độ phân giải cao"
            if legacy_images else ("Đã trích OOXML sang LaTex" if contains_ooxml_math else "Không có công thức OOXML")
        )
        candidate["requires_visual_review"] = bool(image_names)
        candidate["visual_flag_version"] = 2
    return candidates


def extract_pdf_candidates(source, path):
    """Tách câu từ PDF có chữ; PDF scan được trả rỗng để chờ OCR/AI."""
    return build_candidates(source, read_pdf_paragraphs(path), requires_visual_review=False)


def analyze_sources(sources, sources_dir):
    candidates, results = [], []
    for source in sources:
        path = Path(sources_dir) / source["file_name"]
        try:
            suffix = path.suffix.lower()
            if suffix == ".docx":
                extracted = extract_docx_candidates(source, path)
                success_status = "Đã tách câu ứng viên"
            elif suffix == ".pdf":
                extracted = extract_pdf_candidates(source, path)
                success_status = "Đã tách câu PDF có chữ"
            else:
                results.append((source["file_name"], 0, "Định dạng chưa hỗ trợ"))
                continue
            if suffix == ".pdf" and not extracted:
                results.append((source["file_name"], 0, "PDF cần OCR/AI ở bước tiếp theo"))
                continue
            candidates.extend(extracted)
            results.append((source["file_name"], len(extracted), success_status))
        except Exception as error:
            results.append((source["file_name"], 0, f"Chưa đọc được: {error}"))
    return candidates, results
