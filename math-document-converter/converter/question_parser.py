"""Post-OCR parser for Vietnamese mathematics question banks.

The parser deliberately keeps OCR text and LaTeX intact.  It is a conservative
multi-stage interpreter: uncertain text is retained as an unassigned block or
flagged on the resulting question instead of silently disappearing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Iterable


PARSER_VERSION = "question-parser-v1"
QUESTION_PREFIX = re.compile(r"^\s*(?:câu|bài|question)\s*(\d{1,3})\s*[\.:\)\-]?(?:\s+|$)", re.IGNORECASE)
NUMBER_PREFIX = re.compile(r"^\s*(\d{1,3})\s*[\.:\)]\s+(?=\D)")
OPTION_PREFIX = re.compile(r"^\s*(?:\(?\s*([A-Da-d])\s*\)?\s*[\.:\)])\s*(.*)$")
ANSWER_MARKER = re.compile(r"^\s*(?:đáp\s*án|answer|đ\/a)\s*[:\-]?\s*(.*)$", re.IGNORECASE)
SOLUTION_MARKER = re.compile(r"^\s*(?:lời\s*giải|hướng\s*dẫn\s*giải|solution|giải)\s*[:\-]?\s*", re.IGNORECASE)
HEADER_MARKER = re.compile(r"^\s*(?:trang\s*\d+|page\s*\d+|mã\s*đề|đề\s*(?:thi|kiểm tra)|họ\s*(?:và|tên))\b", re.IGNORECASE)
MATH_FENCE = re.compile(r"^\s*(?:\$\$.*\$\$|\\\[.*\\\]|\\begin\{.+?\}).*", re.DOTALL)


@dataclass
class ParsedOption:
    label: str
    content: str

    def as_dict(self) -> dict[str, str]:
        return {"label": self.label, "content": self.content}


@dataclass
class ParsedQuestion:
    question_number: int | None
    question_text: str
    question_math: list[str] = field(default_factory=list)
    question_type: str = "unknown"
    options: list[ParsedOption] = field(default_factory=list)
    correct_answer: str | None = None
    solution: str | None = None
    images: list[str] = field(default_factory=list)
    source_page: int | None = None
    source_page_end: int | None = None
    confidence: float = 0.0
    raw_ocr_text: str = ""
    flags: list[str] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "question_number": self.question_number,
            "question_text": self.question_text,
            "question_math": self.question_math,
            "question_type": self.question_type,
            "options": [item.as_dict() for item in self.options],
            "correct_answer": self.correct_answer,
            "solution": self.solution,
            "images": self.images,
            "source_page": self.source_page,
            "source_page_end": self.source_page_end,
            "confidence": round(self.confidence, 2),
            "raw_ocr_text": self.raw_ocr_text,
            "flags": self.flags,
            "validation": self.validation,
            "parser_version": PARSER_VERSION,
        }


@dataclass
class Line:
    text: str
    page: int
    kind: str
    number: int | None = None
    option_label: str | None = None


def normalize_ocr_text(text: str) -> list[str]:
    """Normalize whitespace only; never flatten/remove math markup."""
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    text = text.replace("\ufeff", "").replace("•", "-")
    return [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]


def classify_line(text: str, page: int) -> Line:
    if not text:
        return Line(text, page, "blank")
    match = QUESTION_PREFIX.match(text) or NUMBER_PREFIX.match(text)
    if match:
        return Line(text, page, "question_start", number=int(match.group(1)))
    option = OPTION_PREFIX.match(text)
    if option:
        return Line(text, page, "option", option_label=option.group(1).upper())
    if ANSWER_MARKER.match(text):
        return Line(text, page, "answer")
    if SOLUTION_MARKER.match(text):
        return Line(text, page, "solution")
    if HEADER_MARKER.match(text) or (len(text) < 5 and text.isdigit()):
        return Line(text, page, "header_footer")
    if MATH_FENCE.match(text) or "$" in text or "\\(" in text or "\\[" in text:
        return Line(text, page, "math")
    return Line(text, page, "text")


def _strip_question_prefix(text: str) -> str:
    return (QUESTION_PREFIX.sub("", text, count=1) if QUESTION_PREFIX.match(text) else NUMBER_PREFIX.sub("", text, count=1)).strip()


def _extract_math(text: str, latex: Iterable[str]) -> list[str]:
    found = list(latex)
    for match in re.finditer(r"\$\$(.*?)\$\$|\$(.*?)\$", text, re.DOTALL):
        value = match.group(1) or match.group(2)
        if value:
            found.append(value.strip())
    return list(dict.fromkeys(item for item in found if item))


def _extract_images(text: str, image_ref: str | None) -> list[str]:
    images = [str(image_ref)] if image_ref else []
    images.extend(match.group(1).strip() for match in re.finditer(r"!\[.*?\]\((.*?)\)", text) if match.group(1).strip())
    return list(dict.fromkeys(images))


def _infer_type(question: ParsedQuestion) -> str:
    joined = " ".join([question.question_text, *(option.content for option in question.options)]).lower()
    if "đúng" in joined and "sai" in joined:
        return "true_false"
    if len(question.options) >= 2:
        return "multiple_choice"
    if any(marker in joined for marker in ("trả lời ngắn", "điền vào", "điền số", "kết quả là")):
        return "short_answer"
    if any(marker in joined for marker in ("tự luận", "chứng minh", "trình bày", "giải phương trình")):
        return "essay"
    return "unknown"


def validate_questions(questions: list[ParsedQuestion], unassigned: list[dict[str, Any]]) -> None:
    """Apply local validation and confidence scoring without discarding drafts."""
    numbers = [item.question_number for item in questions if item.question_number is not None]
    previous: int | None = None
    for question in questions:
        flags = set(question.flags)
        if not question.question_text.strip():
            flags.add("empty_question_text")
        labels = [item.label for item in question.options]
        if len(labels) != len(set(labels)):
            flags.add("duplicate_option_label")
        if question.question_type == "multiple_choice" and set(labels) != {"A", "B", "C", "D"}:
            flags.add("incomplete_abcd_options")
        if question.question_number is None:
            flags.add("question_number_unrecognized")
        if previous is not None and question.question_number is not None and question.question_number > previous + 1:
            flags.add("possible_missing_question_number")
        if previous is not None and question.question_number is not None and question.question_number <= previous:
            flags.add("question_number_out_of_order")
        if question.question_number is not None:
            previous = question.question_number
        score = 0.42
        score += 0.22 if question.question_number is not None else 0
        score += 0.24 if set(labels) == {"A", "B", "C", "D"} else 0
        score += 0.08 if question.question_text.strip() else 0
        score -= min(0.28, 0.05 * len(flags))
        question.flags = sorted(flags)
        question.confidence = max(0.05, min(0.98, score))
        question.validation = {"valid": not bool({"empty_question_text", "duplicate_option_label"} & flags), "unassigned_block_count": len(unassigned)}


def parse_document_pages(pages: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Parse ordered OCR/direct-text pages into conservative question drafts."""
    questions: list[ParsedQuestion] = []
    unassigned: list[dict[str, Any]] = []
    current: ParsedQuestion | None = None
    mode = "question"

    for page in pages:
        page_number = int(page.get("page_number") or page.get("source_page") or 1)
        raw = page.get("raw_ocr_text") or page.get("markdown") or page.get("direct_text") or ""
        latex = page.get("latex") or []
        image_ref = page.get("image_ref")
        page_lines = [classify_line(value, page_number) for value in normalize_ocr_text(raw)]
        if current:
            for image in _extract_images(raw, image_ref):
                if image not in current.images:
                    current.images.append(image)

        for line in page_lines:
            if line.kind in {"blank", "header_footer"}:
                continue
            if line.kind == "question_start":
                if current:
                    current.source_page_end = page_number if current.source_page != page_number else current.source_page
                    questions.append(current)
                current = ParsedQuestion(
                    question_number=line.number,
                    question_text=_strip_question_prefix(line.text),
                    source_page=page_number,
                    source_page_end=page_number,
                    raw_ocr_text=line.text,
                    images=_extract_images(raw, image_ref),
                )
                mode = "question"
                continue
            if not current:
                unassigned.append({"page": page_number, "text": line.text, "reason": "before_first_question"})
                continue
            current.raw_ocr_text += "\n" + line.text
            current.source_page_end = page_number
            if line.kind == "option":
                option_match = OPTION_PREFIX.match(line.text)
                current.options.append(ParsedOption(line.option_label or "?", (option_match.group(2) if option_match else "").strip()))
                mode = "option"
            elif line.kind == "answer":
                answer = ANSWER_MARKER.match(line.text)
                answer_text = (answer.group(1) if answer else "").strip()
                letter = re.fullmatch(r"\(?\s*([A-Da-d])\s*\)?", answer_text)
                current.correct_answer = letter.group(1).upper() if letter else answer_text or None
                mode = "answer"
            elif line.kind == "solution":
                current.solution = SOLUTION_MARKER.sub("", line.text).strip()
                mode = "solution"
            elif mode == "option" and current.options:
                current.options[-1].content = f"{current.options[-1].content}\n{line.text}".strip()
            elif mode == "solution":
                current.solution = f"{current.solution or ''}\n{line.text}".strip()
            else:
                current.question_text = f"{current.question_text}\n{line.text}".strip()
            current.question_math = _extract_math(current.raw_ocr_text, latex)

        # A nonempty page without a fresh question is allowed to continue the
        # previous question; mark it so review can confirm the association.
        if current and page_lines and not any(line.kind == "question_start" for line in page_lines) and current.source_page != page_number:
            current.flags.append("possible_cross_page_question")

    if current:
        questions.append(current)
    for question in questions:
        question.question_type = _infer_type(question)
        question.question_math = _extract_math(question.raw_ocr_text, question.question_math)
    validate_questions(questions, unassigned)
    return {"questions": [question.as_dict() for question in questions], "unassigned_blocks": unassigned, "parser_version": PARSER_VERSION}
