"""Pure M2 teacher-review queue layered on existing source-review evidence."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from candidate_classification import INVALID, MATCHED, REVIEW_REQUIRED, normalize_text
from local_review_workflow import LOCAL_DRAFT_PROVENANCE, review_decision_text
from source_review import build_source_review_snapshot


_OUTCOME_RANK = {REVIEW_REQUIRED: 0, INVALID: 1, MATCHED: 2}
_REASON_RANK = {
    "MATH_CONTRADICTED": 0,
    "VISUAL_OR_FORMULA_REVIEW_REQUIRED": 1,
    "SOURCE_ANSWER_CONFLICT": 2,
    "SOURCE_OPTIONS_CONFLICT": 2,
    "FORMULA_FINGERPRINT_CONFLICT": 2,
    "MULTIPLE_PLAUSIBLE_SOURCE_MATCHES": 3,
    "SOURCE_MATCH_LOW_CONFIDENCE": 4,
    "DUPLICATE_CANDIDATE": 5,
}


def _preview(value: object, limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _review_state(draft: object) -> tuple[str, str]:
    if not isinstance(draft, Mapping):
        return "NO_LOCAL_DRAFT", "Chưa có bản nháp cục bộ để ghi nhận quyết định."
    if draft.get("status") == "Đã duyệt và đưa vào ngân hàng":
        return "ALREADY_APPROVED", "Bản nháp đã ở ngân hàng; không xử lý lại từ hàng M2."
    decision = review_decision_text(draft.get("review_decision"))
    if decision:
        return "TEACHER_FLAGGED", decision
    if draft.get("provenance") in LOCAL_DRAFT_PROVENANCE:
        return "AWAITING_TEACHER_REVIEW", "Bản nháp cục bộ có thể được gắn cờ sau khi đối chiếu."
    return "OTHER_DRAFT", "Bản nháp không thuộc workflow parser cục bộ."


def build_candidate_review_queue(
    classification_report: Mapping[str, Any],
    candidates: object,
    image_analyses: object,
    drafts: object,
    manual_formula_overrides: object = None,
) -> dict[str, Any]:
    candidate_map = {
        str(item.get("candidate_id") or ""): item
        for item in candidates if isinstance(candidates, list) and isinstance(item, Mapping) and item.get("candidate_id")
    }
    draft_map = drafts if isinstance(drafts, Mapping) else {}
    overrides = manual_formula_overrides if isinstance(manual_formula_overrides, Mapping) else {}
    classifications = classification_report.get("classifications") if isinstance(classification_report.get("classifications"), list) else []
    rows = []
    for classification in classifications:
        if not isinstance(classification, Mapping):
            continue
        candidate_id = str(classification.get("candidate_id") or "")
        candidate = candidate_map.get(candidate_id, {})
        draft = draft_map.get(candidate_id)
        snapshot = build_source_review_snapshot(candidate, image_analyses, overrides.get(candidate_id))
        state, state_note = _review_state(draft)
        reasons = [str(reason) for reason in classification.get("reason_codes", [])]
        outcome = str(classification.get("outcome") or REVIEW_REQUIRED)
        resolved = state in {"TEACHER_FLAGGED", "ALREADY_APPROVED"}
        priority = (
            10 if resolved else _OUTCOME_RANK.get(outcome, 0),
            min((_REASON_RANK.get(reason, 9) for reason in reasons), default=9),
            str(snapshot.get("lesson") or candidate.get("lesson") or ""),
            str(snapshot.get("source_name") or candidate.get("source_name") or ""),
            str(snapshot.get("question_number") or candidate.get("question_number") or ""),
            candidate_id,
        )
        rows.append({
            "candidate_id": candidate_id,
            "outcome": outcome,
            "reason_codes": reasons,
            "priority": priority,
            "source_file": str(snapshot.get("source_file") or candidate.get("source_file") or ""),
            "source_name": str(snapshot.get("source_name") or candidate.get("source_name") or "Không rõ nguồn"),
            "question_number": str(snapshot.get("question_number") or candidate.get("question_number") or "?"),
            "lesson": str(candidate.get("lesson") or "Chưa phân loại"),
            "question_preview": _preview(candidate.get("question_text")),
            "solution_preview": _preview(candidate.get("solution_text")),
            "review_state": state,
            "review_state_note": state_note,
            "can_flag_local_draft": isinstance(draft, Mapping) and draft.get("provenance") in LOCAL_DRAFT_PROVENANCE and state != "ALREADY_APPROVED",
            "source_review": snapshot,
            "evidence": classification.get("evidence") or {},
        })
    rows.sort(key=lambda row: row["priority"])
    return {"rows": rows, "counts": {outcome: sum(row["outcome"] == outcome for row in rows) for outcome in (REVIEW_REQUIRED, INVALID, MATCHED)}}


def filter_candidate_review_queue(
    queue: Mapping[str, Any],
    *, outcomes: object = None, reasons: object = None, source_query: object = "", lesson: object = "",
) -> list[dict[str, Any]]:
    selected_outcomes = set(outcomes) if isinstance(outcomes, (list, tuple, set)) else set()
    selected_reasons = set(reasons) if isinstance(reasons, (list, tuple, set)) else set()
    source_terms = normalize_text(source_query).split()
    wanted_lesson = str(lesson or "").strip()
    result = []
    for row in queue.get("rows", []) if isinstance(queue.get("rows"), list) else []:
        if selected_outcomes and row["outcome"] not in selected_outcomes:
            continue
        if selected_reasons and not selected_reasons.intersection(row["reason_codes"]):
            continue
        source_text = normalize_text(f"{row['source_file']} {row['source_name']}")
        if source_terms and not all(term in source_text for term in source_terms):
            continue
        if wanted_lesson and row["lesson"] != wanted_lesson:
            continue
        result.append(row)
    return result
