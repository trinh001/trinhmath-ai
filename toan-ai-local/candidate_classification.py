"""Deterministic, read-only classification for source-derived candidates.

This M2 slice deliberately produces only a review classification.  It neither
updates a candidate nor assigns an approval/release state.  Callers supply a
small source metadata catalog explicitly; no OCR files, database, or network
resource is opened here.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

from candidate_triage import triage_candidate
from math_verifier import CONTRADICTED, INCONCLUSIVE, UNSUPPORTED, VERIFIED, verify_math_claim
from source_quality import source_content_quality_issues


MATCHED = "MATCHED"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
INVALID = "INVALID"
OUTCOMES = frozenset({MATCHED, REVIEW_REQUIRED, INVALID})

MATCH_THRESHOLD = 0.85
PLAUSIBLE_MATCH_THRESHOLD = 0.65
SCHEMA_VERSION = "m2-s1"


def normalize_text(value: object) -> str:
    """Make a deterministic comparison form without changing source values."""
    text = str(value or "")
    text = "".join(
        character for character in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(character) != "Mn"
    ).replace("đ", "d")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def _compact_fingerprint(value: object) -> str:
    return normalize_text(value).replace(" ", "")


def _fingerprint_digest(value: object) -> str:
    return hashlib.sha256(_compact_fingerprint(value).encode("utf-8")).hexdigest()


def _text(value: object) -> str:
    return str(value or "").strip()


def _reference(candidate: Mapping[str, Any]) -> str:
    return _text(candidate.get("source_file")) or _text(candidate.get("source_name"))


def _answer(candidate: Mapping[str, Any]) -> str:
    return _text(candidate.get("correct_answer")) or _text(candidate.get("answer"))


def _options(candidate: Mapping[str, Any]) -> tuple[str, ...]:
    values = candidate.get("options")
    if not isinstance(values, list):
        return ()
    return tuple(normalize_text(value) for value in values if normalize_text(value))


def _image_names(candidate: Mapping[str, Any]) -> set[str]:
    names: set[str] = set()
    for field in ("source_image_names", "legacy_math_image_names", "visual_paths"):
        values = candidate.get(field)
        if isinstance(values, list):
            names.update(normalize_text(value) for value in values if normalize_text(value))
    return names


def _source_records(records: object) -> list[Mapping[str, Any]]:
    if isinstance(records, Mapping):
        nested = records.get("sources")
        values = nested if isinstance(nested, list) else [records]
    elif isinstance(records, Iterable) and not isinstance(records, (str, bytes, bytearray)):
        values = list(records)
    else:
        values = []
    return [record for record in values if isinstance(record, Mapping)]


def _source_id(record: Mapping[str, Any], index: int) -> str:
    return (
        _text(record.get("source_record_id"))
        or _text(record.get("source_id"))
        or _text(record.get("source_file"))
        or _text(record.get("source_name"))
        or f"source-row-{index:04d}"
    )


def _token_similarity(left: object, right: object) -> float:
    left_tokens = set(normalize_text(left).split())
    right_tokens = set(normalize_text(right).split())
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _match_score(candidate: Mapping[str, Any], source: Mapping[str, Any], index: int) -> dict[str, Any]:
    candidate_file = normalize_text(candidate.get("source_file"))
    source_file = normalize_text(source.get("source_file"))
    candidate_name = normalize_text(candidate.get("source_name"))
    source_name = normalize_text(source.get("source_name"))
    candidate_number = normalize_text(candidate.get("question_number"))
    source_number = normalize_text(source.get("question_number"))
    candidate_question = candidate.get("question_text")
    source_question = source.get("question_text")
    candidate_answer = normalize_text(_answer(candidate))
    source_answer = normalize_text(_answer(source))
    candidate_options = _options(candidate)
    source_options = _options(source)
    candidate_formula = normalize_text(candidate.get("formula_fingerprint"))
    source_formula = normalize_text(source.get("formula_fingerprint"))

    file_exact = bool(candidate_file and source_file and candidate_file == source_file)
    name_exact = bool(candidate_name and source_name and candidate_name == source_name)
    number_exact = bool(candidate_number and source_number and candidate_number == source_number)
    question_exact = bool(
        _compact_fingerprint(candidate_question)
        and _compact_fingerprint(candidate_question) == _compact_fingerprint(source_question)
    )
    text_similarity = 1.0 if question_exact else _token_similarity(candidate_question, source_question)
    answer_conflict = bool(candidate_answer and source_answer and candidate_answer != source_answer)
    answer_exact = bool(candidate_answer and source_answer and candidate_answer == source_answer)
    options_conflict = bool(candidate_options and source_options and candidate_options != source_options)
    options_exact = bool(candidate_options and source_options and candidate_options == source_options)
    formula_conflict = bool(candidate_formula and source_formula and candidate_formula != source_formula)
    formula_exact = bool(candidate_formula and source_formula and candidate_formula == source_formula)
    candidate_images = _image_names(candidate)
    source_images = _image_names(source)
    visual_required = bool(candidate.get("requires_visual_review") or candidate.get("has_legacy_mathtype") or candidate_images)
    image_exact = bool(visual_required and candidate_images and candidate_images == source_images)
    image_not_applicable = not visual_required

    components = {
        "source_file_exact": 0.40 if file_exact else 0.0,
        "source_name_exact": 0.05 if not file_exact and name_exact else 0.0,
        "question_number_exact": 0.20 if number_exact else 0.0,
        "question_text_similarity": round(0.20 * text_similarity, 4),
        "answer_agreement": 0.08 if answer_exact else 0.0,
        "option_agreement": 0.04 if options_exact else 0.0,
        "formula_fingerprint": 0.03 if formula_exact else 0.0,
        "image_dependency": 0.05 if image_exact or image_not_applicable else 0.0,
    }
    return {
        "source_id": _source_id(source, index),
        "score": round(sum(components.values()), 4),
        "components": components,
        "question_text_similarity": round(text_similarity, 4),
        "answer_conflict": answer_conflict,
        "options_conflict": options_conflict,
        "formula_conflict": formula_conflict,
        "image_confirmed": image_exact or image_not_applicable,
        "source_file_exact": file_exact,
        "question_number_exact": number_exact,
    }


def source_match_evidence(candidate: Mapping[str, Any], sources: object) -> dict[str, Any]:
    """Return auditable, weighted evidence without including source text."""
    matches = [_match_score(candidate, source, index) for index, source in enumerate(_source_records(sources), start=1)]
    matches.sort(key=lambda item: (-float(item["score"]), str(item["source_id"])))
    top = matches[0] if matches else None
    plausible = [item for item in matches if float(item["score"]) >= PLAUSIBLE_MATCH_THRESHOLD]
    confirmed = bool(
        top
        and float(top["score"]) >= MATCH_THRESHOLD
        and top["source_file_exact"]
        and not top["answer_conflict"]
        and len(plausible) == 1
    )
    if not matches:
        status = "NOT_FOUND"
    elif len(plausible) > 1:
        status = "AMBIGUOUS"
    elif confirmed:
        status = "CONFIRMED"
    else:
        status = "INSUFFICIENT_EVIDENCE"
    return {
        "status": status,
        "match_threshold": MATCH_THRESHOLD,
        "plausible_threshold": PLAUSIBLE_MATCH_THRESHOLD,
        "catalog_size": len(matches),
        "top_match": top,
        "plausible_source_ids": [item["source_id"] for item in plausible],
    }


def structural_evidence(candidate: object) -> dict[str, Any]:
    """Reuse conservative source/triage contracts; never repair the candidate."""
    if not isinstance(candidate, Mapping):
        return {
            "valid": False,
            "hard_issues": ["INVALID_CANDIDATE_FORMAT"],
            "quality_issues": [],
            "triage_group": "D",
            "requires_visual_review": True,
            "math_status": "NOT_REQUESTED",
        }
    hard_issues: list[str] = []
    if not _text(candidate.get("candidate_id")):
        hard_issues.append("MISSING_CANDIDATE_ID")
    if not _text(candidate.get("question_text")):
        hard_issues.append("MISSING_QUESTION_TEXT")
    if not _text(candidate.get("solution_text")):
        hard_issues.append("MISSING_SOLUTION_TEXT")
    if not _reference(candidate):
        hard_issues.append("MISSING_SOURCE_REFERENCE")
    if bool(candidate.get("source_association_impossible")):
        hard_issues.append("SOURCE_ASSOCIATION_IMPOSSIBLE")
    if str(candidate.get("parse_status") or "").strip().upper() in {"FAILED", "FATAL", "UNRECOVERABLE"}:
        hard_issues.append("UNRECOVERABLE_PARSE")

    math_result: Mapping[str, Any] | None = None
    if isinstance(candidate.get("math_claim"), Mapping):
        math_result = verify_math_claim(dict(candidate["math_claim"]))
    elif isinstance(candidate.get("math_verification"), Mapping):
        math_result = candidate["math_verification"]
    math_status = _text((math_result or {}).get("status")).upper() or "NOT_REQUESTED"
    if math_status == CONTRADICTED:
        hard_issues.append("MATH_CONTRADICTED")

    quality_issues = source_content_quality_issues(dict(candidate))
    return {
        "valid": not hard_issues,
        "hard_issues": hard_issues,
        "quality_issues": quality_issues,
        "triage_group": str(triage_candidate(dict(candidate))["group"]),
        "requires_visual_review": bool(
            candidate.get("requires_visual_review")
            or candidate.get("has_legacy_mathtype")
            or _image_names(candidate)
        ),
        "boundary_issue": bool(candidate.get("boundary_issue") or candidate.get("implicit_boundary")),
        "math_status": math_status,
    }


def _duplicate_evidence(candidates: list[object]) -> list[dict[str, Any]]:
    groups: dict[str, list[int]] = {}
    id_counts: Counter[str] = Counter()
    for index, candidate in enumerate(candidates, start=1):
        if isinstance(candidate, Mapping):
            candidate_id = _text(candidate.get("candidate_id"))
            if candidate_id:
                id_counts[candidate_id] += 1
            fingerprint = _compact_fingerprint(candidate.get("question_text"))
            if fingerprint:
                groups.setdefault(fingerprint, []).append(index)
    evidence: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates, start=1):
        record = candidate if isinstance(candidate, Mapping) else {}
        fingerprint = _compact_fingerprint(record.get("question_text"))
        member_indexes = groups.get(fingerprint, []) if fingerprint else []
        candidate_id = _text(record.get("candidate_id"))
        duplicate_id = bool(candidate_id and id_counts[candidate_id] > 1)
        evidence.append({
            "status": "DUPLICATE" if len(member_indexes) > 1 or duplicate_id else "UNIQUE",
            "fingerprint_sha256": _fingerprint_digest(record.get("question_text")) if fingerprint else "",
            "matching_input_indexes": member_indexes,
            "duplicate_candidate_id": duplicate_id,
        })
    return evidence


def _confidence(match: Mapping[str, Any], ambiguity_count: int) -> dict[str, Any]:
    top = match.get("top_match") if isinstance(match.get("top_match"), Mapping) else {}
    base = float(top.get("score") or 0.0)
    penalty = min(0.75, ambiguity_count * 0.15)
    return {
        "score": round(max(0.0, base - penalty), 4),
        "base_source_match_score": round(base, 4),
        "ambiguity_penalty": round(penalty, 4),
        "match_threshold": MATCH_THRESHOLD,
    }


def classify_candidate(
    candidate: object,
    sources: object,
    *,
    input_index: int = 1,
    duplicate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify one candidate into exactly one non-release outcome."""
    record = candidate if isinstance(candidate, Mapping) else {}
    structural = structural_evidence(candidate)
    match = source_match_evidence(record, sources) if isinstance(candidate, Mapping) else {
        "status": "NOT_FOUND", "catalog_size": 0, "top_match": None, "plausible_source_ids": [],
        "match_threshold": MATCH_THRESHOLD, "plausible_threshold": PLAUSIBLE_MATCH_THRESHOLD,
    }
    duplicate = dict(duplicate or {"status": "UNIQUE", "fingerprint_sha256": "", "matching_input_indexes": [], "duplicate_candidate_id": False})

    reason_codes = list(structural["hard_issues"])
    ambiguity_codes: list[str] = []
    if structural["quality_issues"]:
        ambiguity_codes.append("SOURCE_QUALITY_REVIEW_REQUIRED")
    if structural["requires_visual_review"]:
        ambiguity_codes.append("VISUAL_OR_FORMULA_REVIEW_REQUIRED")
    if structural["boundary_issue"]:
        ambiguity_codes.append("BOUNDARY_REVIEW_REQUIRED")
    if structural["math_status"] in {INCONCLUSIVE, UNSUPPORTED}:
        ambiguity_codes.append("MATH_REVIEW_REQUIRED")
    elif structural["math_status"] not in {"NOT_REQUESTED", VERIFIED, CONTRADICTED}:
        ambiguity_codes.append("MATH_STATUS_UNKNOWN_REVIEW_REQUIRED")
    if duplicate["status"] == "DUPLICATE":
        ambiguity_codes.append("DUPLICATE_CANDIDATE")
    if duplicate.get("duplicate_candidate_id"):
        ambiguity_codes.append("DUPLICATE_CANDIDATE_ID")
    if match["status"] == "AMBIGUOUS":
        ambiguity_codes.append("MULTIPLE_PLAUSIBLE_SOURCE_MATCHES")
    elif match["status"] == "NOT_FOUND":
        ambiguity_codes.append("SOURCE_MATCH_NOT_FOUND")
    elif match["status"] != "CONFIRMED":
        ambiguity_codes.append("SOURCE_MATCH_LOW_CONFIDENCE")
    top = match.get("top_match") if isinstance(match.get("top_match"), Mapping) else {}
    if top.get("answer_conflict"):
        ambiguity_codes.append("SOURCE_ANSWER_CONFLICT")
    if top.get("options_conflict"):
        ambiguity_codes.append("SOURCE_OPTIONS_CONFLICT")
    if top.get("formula_conflict"):
        ambiguity_codes.append("FORMULA_FINGERPRINT_CONFLICT")
    if not top.get("image_confirmed", True):
        ambiguity_codes.append("IMAGE_DEPENDENCY_UNCONFIRMED")

    if reason_codes:
        outcome = INVALID
    elif ambiguity_codes:
        outcome = REVIEW_REQUIRED
        reason_codes = ambiguity_codes
    elif match["status"] == "CONFIRMED":
        outcome = MATCHED
        reason_codes = ["SOURCE_MATCH_CONFIRMED", "STRUCTURE_VALID", "NO_DUPLICATE_DETECTED"]
    else:  # Defensive fail-closed guard for future changes to the decision tree.
        outcome = REVIEW_REQUIRED
        reason_codes = ["CLASSIFIER_FALLBACK_REVIEW_REQUIRED"]

    confidence = _confidence(match, len(ambiguity_codes))
    return {
        "schema_version": SCHEMA_VERSION,
        "input_index": input_index,
        "candidate_id": _text(record.get("candidate_id")) or f"row-{input_index:04d}",
        "outcome": outcome,
        "reason_codes": reason_codes,
        "evidence": {
            "source_match": match,
            "structural": structural,
            "duplicate": duplicate,
            "confidence": confidence,
        },
        "classification_scope": "READ_ONLY_NO_APPROVAL_OR_RELEASE_CHANGE",
    }


def classify_candidates(candidates: object, sources: object = ()) -> dict[str, Any]:
    """Build a complete read-only batch report; unclassified rows are errors."""
    if isinstance(candidates, list):
        candidate_rows = list(candidates)
    elif isinstance(candidates, tuple):
        candidate_rows = list(candidates)
    else:
        candidate_rows = [candidates]
    duplicate_rows = _duplicate_evidence(candidate_rows)
    classifications = [
        classify_candidate(candidate, sources, input_index=index, duplicate=duplicate_rows[index - 1])
        for index, candidate in enumerate(candidate_rows, start=1)
    ]
    unclassified = [row["candidate_id"] for row in classifications if row["outcome"] not in OUTCOMES]
    if unclassified:
        raise RuntimeError(f"Unclassified candidates are not allowed: {', '.join(unclassified)}")
    outcome_counts = {outcome: sum(row["outcome"] == outcome for row in classifications) for outcome in sorted(OUTCOMES)}
    reason_counts = Counter(reason for row in classifications for reason in row["reason_codes"])
    return {
        "schema_version": SCHEMA_VERSION,
        "classification_scope": "READ_ONLY_NO_APPROVAL_OR_RELEASE_CHANGE",
        "candidate_count": len(candidate_rows),
        "outcome_counts": outcome_counts,
        "reason_code_counts": dict(sorted(reason_counts.items())),
        "unclassified_count": 0,
        "classifications": classifications,
    }
