"""Versioned trusted-question bank promotion from manually approved Converter matches.

This module is intentionally the only path that creates APPROVED trusted-bank
entries.  It must be called with explicit teacher-review evidence.  There is no
LLM-controlled auto-promotion here.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .storage import ConverterStore

TRUSTED_STATUS_DRAFT = "DRAFT"
TRUSTED_STATUS_REVIEW_REQUIRED = "REVIEW_REQUIRED"
TRUSTED_STATUS_APPROVED = "APPROVED"
TRUSTED_STATUS_RETIRED = "RETIRED"
TRUSTED_STATUSES = frozenset({
    TRUSTED_STATUS_DRAFT,
    TRUSTED_STATUS_REVIEW_REQUIRED,
    TRUSTED_STATUS_APPROVED,
    TRUSTED_STATUS_RETIRED,
})


def _text(value: object) -> str:
    return str(value or "").strip()


def _json(value: object, fallback: object) -> object:
    if isinstance(value, (list, dict)):
        return value
    try:
        parsed = json.loads(str(value or ""))
    except (TypeError, json.JSONDecodeError):
        return fallback
    return parsed if isinstance(parsed, type(fallback)) else fallback


def _validate_question_shape(
    question_type: str,
    stem: str,
    options: list[dict],
    correct_answer: str,
    solution: str,
) -> list[str]:
    errors: list[str] = []
    if not stem:
        errors.append("missing_question_text")
    if question_type == "unknown":
        errors.append("question_type_unknown")
    if not correct_answer:
        errors.append("missing_correct_answer")
    if not solution:
        errors.append("missing_solution")
    if question_type == "multiple_choice":
        labels = [item.get("label") for item in options if isinstance(item, Mapping)]
        if set(labels) != {"A", "B", "C", "D"}:
            errors.append("incomplete_abcd_options")
        if correct_answer and correct_answer not in labels:
            errors.append("answer_label_not_in_options")
    return errors


def promote_approved_match_to_trusted_bank(
    store: ConverterStore,
    parser_draft_id: int,
    teacher_review_evidence: Mapping[str, Any],
    reviewer: str,
    reviewed_at: str | None = None,
    *,
    curriculum_metadata: Mapping[str, Any] | None = None,
    math_verification_evidence: Mapping[str, Any] | None = None,
    status: str = TRUSTED_STATUS_APPROVED,
) -> dict[str, Any]:
    """Create or extend an immutable trusted-question entry from a reviewed match.

    Fail-closed rules:
    - Only match rows whose status is APPROVED_MANUAL may be promoted.
    - Explicit teacher-review evidence and reviewer are required.
    - The parser output must have the required shape for its question type.
    - Any CONTRADICTED math evidence blocks promotion.
    - The creation is versioned; no existing version is overwritten.
    """

    if status != TRUSTED_STATUS_APPROVED:
        raise ValueError("promotion status must be APPROVED")
    if not reviewer.strip():
        raise ValueError("reviewer is required for teacher approval evidence")
    if not isinstance(teacher_review_evidence, Mapping) or not teacher_review_evidence:
        raise ValueError("non-empty teacher_review_evidence is required")

    row = store.get_match_review_for_promotion(parser_draft_id)
    if not row:
        raise ValueError("no match review found for parser_draft_id")
    row = dict(row)

    match_status = _text(row.get("match_status"))
    if match_status != "APPROVED_MANUAL":
        raise ValueError("only APPROVED_MANUAL match rows can be promoted to the trusted bank")

    candidate_id = _text(row.get("matched_candidate_id"))
    if not candidate_id:
        raise ValueError("matched_candidate_id is empty; cannot create trusted question")

    source_path = _text(row.get("source_path"))
    if not source_path:
        raise ValueError("source provenance is unresolved; refusing promotion")
    source_hash = _text(row.get("source_hash"))
    if not source_hash:
        raise ValueError("source hash is missing; refusing promotion")
    source_file = Path(source_path).name
    source_name = _text(source_file)
    source_page = row.get("first_page_number")
    source_page_end = row.get("last_page_number")
    question_number = row.get("question_number")
    question_type = _text(row.get("question_type")) or "unknown"
    stem = _text(row.get("question_text"))
    options = _json(row.get("options_json"), [])
    if not isinstance(options, list):
        options = []
    correct_answer = _text(row.get("correct_answer"))
    solution = _text(row.get("solution"))
    formulas = _json(row.get("question_math_json"), [])
    if not isinstance(formulas, list):
        formulas = []
    images = _json(row.get("images_json"), [])
    if not isinstance(images, list):
        images = []

    shape_errors = _validate_question_shape(question_type, stem, options, correct_answer, solution)
    if shape_errors:
        raise ValueError("incomplete question structure: " + ", ".join(shape_errors))

    parser_validation = _json(row.get("parser_validation_json"), {})
    match_validation = _json(row.get("match_validation_json"), {})
    if isinstance(parser_validation, Mapping) and parser_validation.get("pass") is False:
        raise ValueError("parser validation failed; refusing promotion")
    if isinstance(match_validation, Mapping) and match_validation.get("pass") is False:
        raise ValueError("match validation failed; refusing promotion")

    math_evidence = dict(math_verification_evidence or {})
    if math_evidence.get("status") == "CONTRADICTED":
        raise ValueError("math evidence is contradicted; refusing promotion")

    meta = dict(curriculum_metadata or {})
    grade = _text(meta.get("grade"))
    chapter = _text(meta.get("chapter"))
    topic = _text(meta.get("topic"))
    lesson = _text(meta.get("lesson"))
    skill = _text(meta.get("skill"))
    cognitive_level = _text(meta.get("cognitive_level"))
    difficulty = _text(meta.get("difficulty"))

    stable_locator = question_number if question_number is not None else parser_draft_id
    source_record_id = f"converter:{source_hash}:{source_page or 0}:{stable_locator}"

    source_match_evidence = {
        "source_hash": source_hash,
        "source_record_id": source_record_id,
        "match_score": row.get("match_score") or 0.0,
        "match_duplicate_score": row.get("duplicate_score") or 0.0,
        "score_breakdown": _json(row.get("score_breakdown_json"), {}),
        "source_context": _json(row.get("source_context_json"), {}),
        "match_validation": match_validation,
        "ambiguity": bool(row.get("ambiguity")),
        "decision_reason": _text(row.get("decision_reason")),
    }

    canonical = json.dumps(
        {
            "candidate_id": candidate_id,
            "question_type": question_type,
            "stem": stem,
            "options": options,
            "correct_answer": correct_answer,
            "solution": solution,
            "formulas": formulas,
            "images": images,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    timestamp = reviewed_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with store.session() as connection:
        current_row = connection.execute(
            "SELECT current_version FROM trusted_questions WHERE question_id = ?",
            (candidate_id,),
        ).fetchone()
        version = int(current_row["current_version"] or 0) + 1 if current_row else 1

        connection.execute(
            """
            INSERT INTO trusted_questions(question_id, current_version, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(question_id) DO UPDATE SET
                current_version = excluded.current_version,
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (candidate_id, version, status, timestamp, timestamp),
        )

        connection.execute(
            """
            INSERT INTO trusted_question_versions(
                question_id, version, candidate_id, source_record_id, source_file, source_name,
                source_page, source_page_end, question_number, grade, chapter, topic, lesson, skill,
                cognitive_level, difficulty, question_type, stem, options_json, correct_answer, solution,
                formulas_json, image_assets_json, source_match_evidence_json,
                math_verification_evidence_json, teacher_review_evidence_json,
                reviewer, reviewed_at, created_at, updated_at, content_hash, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate_id,
                version,
                candidate_id,
                source_record_id,
                source_file,
                source_name,
                source_page,
                source_page_end,
                question_number,
                grade,
                chapter,
                topic,
                lesson,
                skill,
                cognitive_level,
                difficulty,
                question_type,
                stem,
                json.dumps(options, ensure_ascii=False),
                correct_answer,
                solution,
                json.dumps(formulas, ensure_ascii=False),
                json.dumps(images, ensure_ascii=False),
                json.dumps(source_match_evidence, ensure_ascii=False),
                json.dumps(math_evidence, ensure_ascii=False),
                json.dumps(dict(teacher_review_evidence), ensure_ascii=False),
                reviewer,
                timestamp,
                timestamp,
                timestamp,
                content_hash,
                status,
            ),
        )

    return {
        "question_id": candidate_id,
        "version": version,
        "content_hash": content_hash,
        "status": status,
    }
