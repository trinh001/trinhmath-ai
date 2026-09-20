"""Pure review-queue model for M2 candidate classifications.

This module is deliberately read-only. It combines classifier output with
candidate metadata and existing teacher-review state, but never writes approval
or release state.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from candidate_classification import INVALID, MATCHED, REVIEW_REQUIRED


OUTCOME_PRIORITY = {
    REVIEW_REQUIRED: 0,
    INVALID: 1,
    MATCHED: 2,
}

REASON_PRIORITY = {
    "MATH_CONTRADICTED": 0,
    "SOURCE_ANSWER_CONFLICT": 1,
    "QUESTION_OPERATOR_CONFLICT": 2,
    "FORMULA_FINGERPRINT_CONFLICT": 3,
    "IMAGE_DEPENDENCY_UNCONFIRMED": 4,
    "VISUAL_OR_FORMULA_REVIEW_REQUIRED": 5,
    "MULTIPLE_PLAUSIBLE_SOURCE_MATCHES": 6,
    "SOURCE_MATCH_LOW_CONFIDENCE": 7,
    "SOURCE_MATCH_NOT_FOUND": 8,
    "DUPLICATE_CANDIDATE": 9,
    "SOURCE_QUALITY_REVIEW_REQUIRED": 10,
}


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _text(value: object) -> str:
    return str(value or "").strip()


def _reason_rank(reasons: object) -> int:
    values = reasons if isinstance(reasons, list) else []
    return min((REASON_PRIORITY.get(str(value), 50) for value in values), default=50)


def _candidate_map(candidates: object) -> dict[str, Mapping[str, Any]]:
    if not isinstance(candidates, list):
        return {}
    return {
        _text(item.get("candidate_id")): item
        for item in candidates
        if isinstance(item, Mapping) and _text(item.get("candidate_id"))
    }


def _draft_map(drafts: object) -> Mapping[str, Any]:
    return drafts if isinstance(drafts, Mapping) else {}


def _local_review_map(local_review_queue: object) -> dict[str, Mapping[str, Any]]:
    queue = _mapping(local_review_queue)
    rows = queue.get("rows")
    if not isinstance(rows, list):
        return {}
    return {
        _text(row.get("candidate_id")): row
        for row in rows
        if isinstance(row, Mapping) and _text(row.get("candidate_id"))
    }


def build_candidate_review_queue(
    classification_report: object,
    candidates: object,
    *,
    drafts: object = None,
    local_review_queue: object = None,
) -> dict[str, Any]:
    """Build a deterministic teacher queue from read-only classifier evidence."""
    report = _mapping(classification_report)
    classifications = report.get("classifications")
    classification_rows = classifications if isinstance(classifications, list) else []
    candidate_by_id = _candidate_map(candidates)
    draft_by_id = _draft_map(drafts)
    local_by_id = _local_review_map(local_review_queue)

    rows: list[dict[str, Any]] = []
    for classification in classification_rows:
        if not isinstance(classification, Mapping):
            continue
        candidate_id = _text(classification.get("candidate_id"))
        candidate = candidate_by_id.get(candidate_id, {})
        evidence = _mapping(classification.get("evidence"))
        source_match = _mapping(evidence.get("source_match"))
        structural = _mapping(evidence.get("structural"))
        duplicate = _mapping(evidence.get("duplicate"))
        confidence = _mapping(evidence.get("confidence"))
        draft = _mapping(draft_by_id.get(candidate_id))
        local = local_by_id.get(candidate_id, {})

        outcome = _text(classification.get("outcome"))
        reasons = [str(value) for value in classification.get("reason_codes", []) if str(value)]
        review_decision = _text(draft.get("review_decision"))
        status = _text(draft.get("status"))
        resolved = bool(
            review_decision
            or status in {"Đã duyệt và đưa vào ngân hàng", "Đã xác nhận nguồn — chờ duyệt vào ngân hàng"}
        )
        priority = (
            1 if resolved else 0,
            OUTCOME_PRIORITY.get(outcome, 9),
            _reason_rank(reasons),
            float(confidence.get("score") or 0.0),
            _text(candidate.get("source_name") or candidate.get("source_file")),
            _text(candidate.get("question_number")),
            candidate_id,
        )

        rows.append({
            "candidate_id": candidate_id,
            "outcome": outcome,
            "reason_codes": reasons,
            "priority_key": priority,
            "resolved": resolved,
            "teacher_review_decision": review_decision,
            "draft_status": status,
            "local_review_bucket": _text(local.get("bucket")),
            "source_file": _text(candidate.get("source_file")),
            "source_name": _text(candidate.get("source_name") or candidate.get("source_file")),
            "question_number": _text(candidate.get("question_number")),
            "grade": _text(candidate.get("grade")),
            "lesson": _text(candidate.get("lesson")),
            "question_text": _text(candidate.get("question_text")),
            "solution_text": _text(candidate.get("solution_text")),
            "source_match_status": _text(source_match.get("status")),
            "source_match_score": float(_mapping(source_match.get("top_match")).get("score") or 0.0),
            "confidence": float(confidence.get("score") or 0.0),
            "duplicate_status": _text(duplicate.get("status")),
            "duplicate_indexes": list(duplicate.get("matching_input_indexes") or []),
            "requires_visual_review": bool(structural.get("requires_visual_review")),
            "math_status": _text(structural.get("math_status")),
            "classification_scope": _text(classification.get("classification_scope")),
        })

    rows.sort(key=lambda row: row["priority_key"])
    for index, row in enumerate(rows, start=1):
        row["priority"] = index
        row.pop("priority_key", None)

    outcome_counts = Counter(row["outcome"] for row in rows)
    reason_counts = Counter(reason for row in rows for reason in row["reason_codes"])
    return {
        "rows": rows,
        "counts": dict(sorted(outcome_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "unresolved_count": sum(not row["resolved"] for row in rows),
        "resolved_count": sum(row["resolved"] for row in rows),
    }


def filter_candidate_review_queue(
    review_queue: object,
    *,
    outcomes: object = None,
    reason_codes: object = None,
    source_text: str = "",
    lesson_text: str = "",
    unresolved_only: bool = False,
) -> list[dict[str, Any]]:
    """Filter queue rows without mutating the queue."""
    queue = _mapping(review_queue)
    rows = queue.get("rows") if isinstance(queue.get("rows"), list) else []
    allowed_outcomes = {str(value) for value in outcomes} if isinstance(outcomes, (list, tuple, set)) else set()
    allowed_reasons = {str(value) for value in reason_codes} if isinstance(reason_codes, (list, tuple, set)) else set()
    source_query = _text(source_text).lower()
    lesson_query = _text(lesson_text).lower()

    result = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if allowed_outcomes and _text(row.get("outcome")) not in allowed_outcomes:
            continue
        row_reasons = {str(value) for value in row.get("reason_codes", [])}
        if allowed_reasons and not (row_reasons & allowed_reasons):
            continue
        source_haystack = " ".join([
            _text(row.get("source_name")),
            _text(row.get("source_file")),
        ]).lower()
        if source_query and source_query not in source_haystack:
            continue
        if lesson_query and lesson_query not in _text(row.get("lesson")).lower():
            continue
        if unresolved_only and bool(row.get("resolved")):
            continue
        result.append(dict(row))
    return result


def review_queue_detail(review_queue: object, candidate_id: str) -> dict[str, Any] | None:
    """Return one detached queue row for a detail panel."""
    queue = _mapping(review_queue)
    rows = queue.get("rows") if isinstance(queue.get("rows"), list) else []
    target = _text(candidate_id)
    for row in rows:
        if isinstance(row, Mapping) and _text(row.get("candidate_id")) == target:
            return dict(row)
    return None
