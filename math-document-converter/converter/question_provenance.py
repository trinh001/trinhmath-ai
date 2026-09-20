"""Build question-level provenance records from Converter parser/match data.

These records are evidence only. A trusted provenance record may help a candidate
reach MATCHED, but never changes TrinhMath approval or release state.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


TRUSTED_MATCH_STATUSES = frozenset({"APPROVED", "APPROVED_MANUAL"})


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


def _candidate_map(candidates: object) -> dict[str, Mapping[str, Any]]:
    if not isinstance(candidates, list):
        return {}
    return {
        _text(item.get("candidate_id")): item
        for item in candidates
        if isinstance(item, Mapping) and _text(item.get("candidate_id"))
    }


def _option_values(value: object) -> list[str]:
    rows = _json(value, [])
    result: list[str] = []
    for item in rows if isinstance(rows, list) else []:
        if isinstance(item, Mapping):
            content = _text(item.get("content") or item.get("text"))
        else:
            content = _text(item)
        if content:
            result.append(content)
    return result


def build_question_provenance_records(
    rows: object,
    candidates: object,
    *,
    trusted_statuses: object = TRUSTED_MATCH_STATUSES,
) -> list[dict[str, Any]]:
    """Convert joined Converter rows to auditable question-level source records."""
    candidate_by_id = _candidate_map(candidates)
    trusted = {str(value) for value in trusted_statuses} if isinstance(trusted_statuses, (set, frozenset, list, tuple)) else set(TRUSTED_MATCH_STATUSES)
    records: list[dict[str, Any]] = []

    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, Mapping):
            continue
        matched_candidate_id = _text(row.get("matched_candidate_id"))
        candidate = candidate_by_id.get(matched_candidate_id)
        if not candidate:
            continue

        match_status = _text(row.get("match_status") or row.get("status"))
        validation = _json(row.get("validation_json"), {})
        source_context = _json(row.get("source_context_json"), {})
        parser_flags = _json(row.get("flags_json"), [])
        parser_math = _json(row.get("question_math_json"), [])
        source_images = (
            list(source_context.get("image_names") or [])
            if isinstance(source_context, Mapping)
            else []
        )

        parser_draft_id = _text(row.get("parser_draft_id") or row.get("id"))
        records.append({
            "source_record_id": f"converter:{parser_draft_id}",
            "source_file": _text(candidate.get("source_file")),
            "source_name": _text(candidate.get("source_name") or candidate.get("source_file")),
            "question_number": row.get("question_number"),
            "question_text": _text(row.get("question_text")),
            "options": _option_values(row.get("options_json")),
            "correct_answer": _text(row.get("correct_answer")),
            "solution_text": _text(row.get("solution")),
            "formula_fingerprint": " ".join(_text(item) for item in parser_math if _text(item)),
            "source_image_names": source_images,
            "source_page": row.get("first_page_number"),
            "source_page_end": row.get("last_page_number"),
            "parser_confidence": float(row.get("parser_confidence") or row.get("confidence") or 0.0),
            "parser_flags": list(parser_flags) if isinstance(parser_flags, list) else [],
            "parser_validation": dict(validation) if isinstance(validation, Mapping) else {},
            "match_status": match_status,
            "match_score": float(row.get("match_score") or 0.0),
            "match_ambiguity": bool(row.get("ambiguity")),
            "matched_candidate_id": matched_candidate_id,
            "provenance_kind": "converter_question_parser_match",
            "provenance_trusted": bool(
                match_status in trusted
                and not bool(row.get("ambiguity"))
                and isinstance(validation, Mapping)
                and bool(validation.get("pass"))
                and _text(row.get("question_text"))
            ),
        })

    records.sort(
        key=lambda item: (
            item["source_file"],
            str(item.get("question_number") or ""),
            item["source_record_id"],
        )
    )
    return records


def provenance_summary(records: object) -> dict[str, int]:
    rows = records if isinstance(records, list) else []
    return {
        "records": len(rows),
        "trusted": sum(bool(item.get("provenance_trusted")) for item in rows if isinstance(item, Mapping)),
        "untrusted": sum(not bool(item.get("provenance_trusted")) for item in rows if isinstance(item, Mapping)),
    }


def load_candidates(path: Path) -> list[dict[str, Any]]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    return [dict(item) for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []
