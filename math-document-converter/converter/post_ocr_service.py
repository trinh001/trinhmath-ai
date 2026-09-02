"""Persistence-facing service for parsing existing OCR output.

This module reads only completed OCR/direct-text rows.  It never queues OCR or
changes OCR output, so it is safe to rerun after parser improvements.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .question_parser import parse_document_pages


def parse_available_documents(store, limit_documents: int | None = None) -> dict:
    grouped: dict[int, list[dict]] = defaultdict(list)
    source_paths: dict[int, str] = {}
    for row in store.pages_for_parsing():
        document_id = int(row["document_id"])
        source_path = str(row["source_path"])
        source_paths[document_id] = source_path
        try:
            latex = json.loads(row["latex_json"] or "[]")
        except (TypeError, json.JSONDecodeError):
            latex = []
        raw = row["markdown"] or row["direct_text"] or ""
        grouped[document_id].append(
            {
                "page_number": row["page_number"],
                "raw_ocr_text": raw,
                "latex": latex,
                "image_ref": source_path if str(row["kind"]).upper() == "IMAGE" else None,
            }
        )
    parsed_documents = parsed_questions = unassigned = 0
    for document_id in sorted(grouped):
        if limit_documents is not None and parsed_documents >= limit_documents:
            break
        result = parse_document_pages(grouped[document_id])
        store.replace_parsed_document(document_id, result["questions"], result["unassigned_blocks"])
        parsed_documents += 1
        parsed_questions += len(result["questions"])
        unassigned += len(result["unassigned_blocks"])
    store.log("INFO", f"Post-OCR parser: {parsed_documents} tài liệu, {parsed_questions} câu, {unassigned} đoạn chưa gắn.")
    return {"documents": parsed_documents, "questions": parsed_questions, "unassigned": unassigned}
