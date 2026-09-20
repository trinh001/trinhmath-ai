"""Read-only adapter from the local candidate/source schema to M2-S1."""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from candidate_classification import normalize_text


def _rows(value: object) -> list[Mapping[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, Mapping)]
    if isinstance(value, Mapping):
        nested = value.get("sources") or value.get("candidates")
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, Mapping)]
    return []


def adapt_candidates(raw_candidates: object) -> list[dict[str, Any]]:
    """Copy current candidate fields without repairing or mutating raw OCR data."""
    adapted = []
    for candidate in _rows(raw_candidates):
        item = dict(candidate)
        item["candidate_id"] = str(item.get("candidate_id") or "").strip()
        item["source_file"] = str(item.get("source_file") or "").strip()
        item["source_name"] = str(item.get("source_name") or item["source_file"]).strip()
        adapted.append(item)
    return adapted


def adapt_source_catalog(raw_sources: object) -> list[dict[str, Any]]:
    """Map current ``file_name/original_name`` records to source-match metadata."""
    adapted = []
    for source in _rows(raw_sources):
        file_name = str(source.get("source_file") or source.get("file_name") or "").strip()
        source_name = str(source.get("source_name") or source.get("original_name") or file_name).strip()
        adapted.append({
            "source_record_id": str(source.get("source_id") or file_name or source_name).strip(),
            "source_file": file_name,
            "source_name": source_name,
            "grade": source.get("grade"),
            "lesson": source.get("lesson"),
            "document_kind": source.get("document_kind"),
        })
    return adapted


def adapt_real_m2_inputs(raw_candidates: object, raw_sources: object) -> dict[str, Any]:
    candidates = adapt_candidates(raw_candidates)
    sources = adapt_source_catalog(raw_sources)
    known_files = {str(source.get("source_file") or "") for source in sources}
    source_index: dict[str, list[dict[str, Any]]] = {}
    for source in sources:
        source_file = normalize_text(source.get("source_file"))
        if source_file:
            source_index.setdefault(source_file, []).append(source)
    candidate_files = [str(candidate.get("source_file") or "") for candidate in candidates]
    return {
        "candidates": candidates,
        "sources": sources,
        "source_match_input": {"sources": sources, "by_source_file": source_index},
        "schema_summary": {
            "candidate_count": len(candidates),
            "source_count": len(sources),
            "candidate_source_reference_count": sum(bool(value) for value in candidate_files),
            "candidate_source_catalog_coverage": sum(value in known_files for value in candidate_files if value),
            "candidate_source_missing_from_catalog": sum(bool(value) and value not in known_files for value in candidate_files),
        },
    }


def aggregate_classification_metrics(report: Mapping[str, Any]) -> dict[str, Any]:
    """Return aggregate-only statistics safe to keep out of private source data."""
    rows = report.get("classifications") if isinstance(report.get("classifications"), list) else []
    reasons = Counter(reason for row in rows if isinstance(row, Mapping) for reason in row.get("reason_codes", []))
    return {
        "candidate_total": int(report.get("candidate_count") or 0),
        "outcome_counts": dict(report.get("outcome_counts") or {}),
        "top_reason_codes": reasons.most_common(10),
        "duplicate_count": sum("DUPLICATE_CANDIDATE" in row.get("reason_codes", []) for row in rows if isinstance(row, Mapping)),
        "image_formula_review_count": sum("VISUAL_OR_FORMULA_REVIEW_REQUIRED" in row.get("reason_codes", []) for row in rows if isinstance(row, Mapping)),
        "source_match_ambiguity_count": sum("MULTIPLE_PLAUSIBLE_SOURCE_MATCHES" in row.get("reason_codes", []) for row in rows if isinstance(row, Mapping)),
        "source_match_low_confidence_count": sum("SOURCE_MATCH_LOW_CONFIDENCE" in row.get("reason_codes", []) for row in rows if isinstance(row, Mapping)),
        "math_conflict_count": sum("MATH_CONTRADICTED" in row.get("reason_codes", []) for row in rows if isinstance(row, Mapping)),
        "unclassified_count": int(report.get("unclassified_count") or 0),
    }
