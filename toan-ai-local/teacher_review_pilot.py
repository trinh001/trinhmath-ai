"""Local-only M3-S1 teacher-review pilot; no approval or release mutation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).parent
RECORDS_FILE = APP_DIR / "teacher_review_pilot_records.json"
TRUSTED_BANK_FILE = APP_DIR / "trusted_question_bank.json"

APPROVED_MANUAL = "APPROVED_MANUAL"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
REJECTED = "REJECTED"
VALID_DECISIONS = {APPROVED_MANUAL, REVIEW_REQUIRED, REJECTED}
ALLOWED_SHORTLIST_REASONS = {"SOURCE_MATCH_LOW_CONFIDENCE"}
MIN_SHORTLIST_MATCH_SCORE = 0.65


def _text(value: object) -> str:
    return str(value or "").strip()


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, json.JSONDecodeError):
        value = {}
    return value if isinstance(value, dict) else {}


def _save(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_records() -> dict[str, Any]:
    return _load(RECORDS_FILE)


def load_trusted_bank() -> dict[str, Any]:
    return _load(TRUSTED_BANK_FILE)


def build_shortlist(rows: object, records: object = None, max_items: int = 50) -> list[dict[str, Any]]:
    """Return deterministic, promotable REVIEW_REQUIRED rows only.

    A row with ambiguous matches, source-quality/parser failures, duplicate,
    unresolved visual/formula work, or math contradiction is intentionally not
    eligible for the first trusted-seed review batch.
    """
    record_map = records if isinstance(records, dict) else {}
    result: list[dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or row.get("outcome") != REVIEW_REQUIRED or row.get("resolved"):
            continue
        candidate_id = _text(row.get("candidate_id"))
        if _text(record_map.get(candidate_id, {}).get("decision")) in {APPROVED_MANUAL, REJECTED}:
            continue
        reasons = set(row.get("reason_codes") or [])
        if not reasons or reasons - ALLOWED_SHORTLIST_REASONS:
            continue
        evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
        structural = evidence.get("structural") if isinstance(evidence.get("structural"), dict) else {}
        source_match = evidence.get("source_match") if isinstance(evidence.get("source_match"), dict) else {}
        if row.get("duplicate_status") == "DUPLICATE" or row.get("requires_visual_review"):
            continue
        if _text(structural.get("math_status") or row.get("math_status")) == "CONTRADICTED":
            continue
        if int(source_match.get("candidate_linked_source_count") or 0) < 1:
            continue
        score = float(row.get("source_match_score") or 0.0)
        if score < MIN_SHORTLIST_MATCH_SCORE:
            continue
        result.append(dict(row))
    result.sort(key=lambda row: (-float(row.get("source_match_score") or 0.0), -float(row.get("confidence") or 0.0), _text(row.get("source_name")), _text(row.get("candidate_id"))))
    return result[:max(1, min(int(max_items or 50), 50))]


def save_decision(candidate_id: str, decision: str, reviewer: str, reason: str, row: object) -> dict[str, Any]:
    """Append an immutable local audit event; does not touch source or release state."""
    candidate_id, decision, reason = _text(candidate_id), _text(decision), _text(reason)
    if not candidate_id or decision not in VALID_DECISIONS or not reason:
        raise ValueError("candidate_id, a valid decision, and a reason are required")
    records = load_records()
    prior = records.get(candidate_id) if isinstance(records.get(candidate_id), dict) else {}
    event = {"timestamp": _now(), "decision": decision, "reviewer": _text(reviewer), "reason": reason, "previous_decision": prior.get("decision"), "previous_state": (row or {}).get("review_state") if isinstance(row, dict) else None}
    updated = {**prior, "candidate_id": candidate_id, "decision": decision, "reviewer": _text(reviewer), "reason": reason, "updated_at": event["timestamp"], "audit": [*(prior.get("audit") or []), event]}
    records[candidate_id] = updated
    _save(RECORDS_FILE, records)
    return updated


def promotion_errors(candidate: object, row: object, record: object) -> list[str]:
    candidate = candidate if isinstance(candidate, dict) else {}
    row = row if isinstance(row, dict) else {}
    record = record if isinstance(record, dict) else {}
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    structural = evidence.get("structural") if isinstance(evidence.get("structural"), dict) else {}
    source_match = evidence.get("source_match") if isinstance(evidence.get("source_match"), dict) else {}
    errors = []
    if record.get("decision") != APPROVED_MANUAL: errors.append("Teacher decision is not APPROVED_MANUAL")
    if not _text(record.get("reason")): errors.append("Missing teacher evidence note")
    if not _text(candidate.get("question_text")): errors.append("Missing question text")
    if not _text(candidate.get("solution_text")): errors.append("Missing solution text")
    if structural.get("hard_issues"): errors.append("Structural hard issues remain")
    if _text(structural.get("math_status") or row.get("math_status")) == "CONTRADICTED": errors.append("Math evidence is contradicted")
    if row.get("requires_visual_review") or (row.get("source_review") or {}).get("requires_visual_review"): errors.append("Visual/formula review remains")
    if int(source_match.get("candidate_linked_source_count") or 0) < 1: errors.append("Missing question-level provenance")
    return errors


def promote(candidate: object, row: object, record: object) -> tuple[bool, str]:
    """Explicitly version a trusted-bank entry after all gates pass; never release it."""
    errors = promotion_errors(candidate, row, record)
    candidate_id = _text((row or {}).get("candidate_id")) if isinstance(row, dict) else ""
    records = load_records()
    stored = records.get(candidate_id) if isinstance(records.get(candidate_id), dict) else dict(record or {})
    if stored.get("promotion_status") == "PROMOTED" and stored.get("promoted_for_updated_at") == stored.get("updated_at"):
        return False, "This teacher decision was already promoted; record a new manual review before creating another version."
    if errors:
        if candidate_id:
            stored["promotion_status"] = "BLOCKED"
            stored["promotion_error"] = "; ".join(errors)
            stored["audit"] = [*(stored.get("audit") or []), {"timestamp": _now(), "action": "PROMOTE_BLOCKED", "reason": stored["promotion_error"]}]
            records[candidate_id] = stored
            _save(RECORDS_FILE, records)
        return False, "; ".join(errors)
    candidate, row, record = dict(candidate), dict(row), dict(record)
    bank, candidate_id = load_trusted_bank(), _text(row.get("candidate_id"))
    versions = list(bank.get(candidate_id) or [])
    version = len(versions) + 1
    versions.append({"version": version, "promoted_at": _now(), "candidate_id": candidate_id, "question": {key: candidate.get(key) for key in ("question_text", "solution_text", "correct_answer", "options", "lesson", "grade")}, "provenance": {"source_file": row.get("source_file"), "source_name": row.get("source_name"), "question_number": row.get("question_number"), "evidence": row.get("evidence")}, "teacher_audit": list(record.get("audit") or [])})
    bank[candidate_id] = versions
    _save(TRUSTED_BANK_FILE, bank)
    stored["promotion_status"] = "PROMOTED"
    stored["promotion_version"] = version
    stored["promoted_for_updated_at"] = stored.get("updated_at")
    stored["audit"] = [*(stored.get("audit") or []), {"timestamp": _now(), "action": "PROMOTED_TO_TRUSTED_BANK", "version": version}]
    records[candidate_id] = stored
    _save(RECORDS_FILE, records)
    return True, f"Promoted trusted-bank version {version}; not approved or released to students."
