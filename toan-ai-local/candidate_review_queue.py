"""Read-only M2 review queue built from classifier and source-review evidence.

The queue is a derived teacher-workflow view. It never changes candidate,
approval, release, OCR, or source state.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from candidate_classification import INVALID, MATCHED, REVIEW_REQUIRED, normalize_text
from local_review_workflow import LOCAL_DRAFT_PROVENANCE, review_decision_text
from source_review import build_source_review_snapshot


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


def _text(value: object) -> str:
    return str(value or "").strip()


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


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


def _local_review_map(local_review_queue: object) -> dict[str, Mapping[str, Any]]:
    queue = _mapping(local_review_queue)
    rows = queue.get("rows") if isinstance(queue.get("rows"), list) else []
    return {
        _text(row.get("candidate_id")): row
        for row in rows
        if isinstance(row, Mapping) and _text(row.get("candidate_id"))
    }


def _review_state(draft: Mapping[str, Any], decision_text: str, status: str) -> str:
    if decision_text:
        return "TEACHER_FLAGGED"
    if status == "Đã duyệt và đưa vào ngân hàng":
        return "ALREADY_APPROVED"
    if status == "Đã xác nhận nguồn — chờ duyệt vào ngân hàng":
        return "SOURCE_REVIEW_CONFIRMED"
    if draft.get("provenance") in LOCAL_DRAFT_PROVENANCE:
        return "AWAITING_TEACHER_REVIEW"
    return "NO_LOCAL_DRAFT"


def build_candidate_review_queue(
    classification_report: object,
    candidates: object,
    image_analyses: object = None,
    drafts: object = None,
    manual_formula_overrides: object = None,
    *,
    local_review_queue: object = None,
) -> dict[str, Any]:
    """Build a deterministic queue without mutating any supplied data."""
    report = _mapping(classification_report)
    classifications = report.get("classifications")
    classification_rows = classifications if isinstance(classifications, list) else []
    candidate_by_id = _candidate_map(candidates)
    draft_by_id = _mapping(drafts)
    override_by_id = _mapping(manual_formula_overrides)
    local_by_id = _local_review_map(local_review_queue)

    rows: list[dict[str, Any]] = []
    for classification in classification_rows:
        if not isinstance(classification, Mapping):
            continue

        candidate_id = _text(classification.get("candidate_id"))
        candidate = candidate_by_id.get(candidate_id, {})
        draft = _mapping(draft_by_id.get(candidate_id))
        evidence = _mapping(classification.get("evidence"))
        structural = _mapping(evidence.get("structural"))
        source_match = _mapping(evidence.get("source_match"))
        duplicate = _mapping(evidence.get("duplicate"))
        confidence = _mapping(evidence.get("confidence"))
        source_snapshot = build_source_review_snapshot(
            candidate,
            image_analyses,
            override_by_id.get(candidate_id),
        )

        decision_text = review_decision_text(draft.get("review_decision"))
        status = _text(draft.get("status"))
        state = _review_state(draft, decision_text, status)
        resolved = state in {"TEACHER_FLAGGED", "ALREADY_APPROVED", "SOURCE_REVIEW_CONFIRMED"}
        reasons = [str(value) for value in classification.get("reason_codes", []) if str(value)]
        outcome = _text(classification.get("outcome"))
        priority_key = (
            1 if resolved else 0,
            OUTCOME_PRIORITY.get(outcome, 9),
            _reason_rank(reasons),
            float(confidence.get("score") or 0.0),
            _text(candidate.get("source_name") or candidate.get("source_file")),
            _text(candidate.get("question_number")),
            candidate_id,
        )

        is_local_draft = bool(draft) and draft.get("provenance") in LOCAL_DRAFT_PROVENANCE
        rows.append({
            "candidate_id": candidate_id,
            "outcome": outcome,
            "reason_codes": reasons,
            "priority_key": priority_key,
            "resolved": resolved,
            "teacher_review_decision": decision_text,
            "review_state": state,
            "review_state_note": decision_text,
            "draft_status": status,
            "local_review_bucket": _text(_mapping(local_by_id.get(candidate_id)).get("bucket")),
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
            "source_review": source_snapshot,
            "evidence": dict(evidence),
            "can_flag_local_draft": is_local_draft and not resolved,
            "can_restore_local_draft": is_local_draft and state == "TEACHER_FLAGGED",
        })

    rows.sort(key=lambda row: row["priority_key"])
    for index, row in enumerate(rows, start=1):
        row["priority"] = index
        row.pop("priority_key", None)

    return {
        "rows": rows,
        "counts": dict(Counter(row["outcome"] for row in rows)),
        "reason_counts": dict(Counter(reason for row in rows for reason in row["reason_codes"])),
        "unresolved_count": sum(not row["resolved"] for row in rows),
        "resolved_count": sum(row["resolved"] for row in rows),
    }


def filter_candidate_review_queue(
    review_queue: object,
    *,
    outcomes: object = None,
    reason_codes: object = None,
    reasons: object = None,
    source_text: str = "",
    source_query: str = "",
    lesson_text: str = "",
    lesson: str = "",
    unresolved_only: bool = False,
) -> list[dict[str, Any]]:
    """Filter queue rows without mutating the queue."""
    queue = _mapping(review_queue)
    rows = queue.get("rows") if isinstance(queue.get("rows"), list) else []
    allowed_outcomes = set(outcomes or [])
    allowed_reasons = set(reason_codes or reasons or [])
    source_terms = normalize_text(source_text or source_query).split()
    lesson_query = normalize_text(lesson_text or lesson)

    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if allowed_outcomes and row.get("outcome") not in allowed_outcomes:
            continue
        if allowed_reasons and not allowed_reasons.intersection(row.get("reason_codes", [])):
            continue
        source_haystack = normalize_text(f"{row.get('source_name')} {row.get('source_file')}")
        if source_terms and not all(term in source_haystack for term in source_terms):
            continue
        if lesson_query and lesson_query not in normalize_text(row.get("lesson")):
            continue
        if unresolved_only and bool(row.get("resolved")):
            continue
        result.append(dict(row))
    return result


def review_queue_detail(review_queue: object, candidate_id: str) -> dict[str, Any] | None:
    """Return a detached row for the UI detail panel."""
    queue = _mapping(review_queue)
    rows = queue.get("rows") if isinstance(queue.get("rows"), list) else []
    target = _text(candidate_id)
    return next(
        (
            dict(row)
            for row in rows
            if isinstance(row, Mapping) and _text(row.get("candidate_id")) == target
        ),
        None,
    )
