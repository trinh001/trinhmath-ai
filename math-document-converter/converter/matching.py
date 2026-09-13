"""Explainable, conservative matching from post-OCR drafts to TrinhMath candidates."""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
import json
import re
import unicodedata
from pathlib import Path


CONFIG = {
    "very_high": 0.95,
    "high": 0.85,
    "medium": 0.70,
    "ambiguity_gap": 0.06,
    "duplicate": 0.92,
    "auto_approve": 0.97,
    "weights": {"source": 0.30, "number": 0.18, "text": 0.28, "math": 0.10, "options": 0.08, "image": 0.06},
}


@lru_cache(maxsize=20000)
def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").lower()
    value = re.sub(r"\b(?:câu|bài|question)\s*\d+\s*[\.:\)]?", " ", value)
    value = re.sub(r"\$+|\\\[|\\\]|\\\(|\\\)", " ", value)
    value = re.sub(r"[^\wà-ỹ\\]+", " ", value, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", value).strip()


def similarity(left: str, right: str) -> float:
    left, right = normalize_text(left)[:1200], normalize_text(right)[:1200]
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def source_context(images: list[str], manifest: dict, source_path: str | None = None) -> dict:
    mappings = [manifest.get(str(Path(image).resolve())) for image in images]
    mappings = [item for item in mappings if item]
    source_files = {item["source_file"] for item in mappings}
    # Direct-text PDF pages retain their original source path in SQLite.  That
    # filename is a first-class match signal even when no separate image exists.
    if source_path:
        source_files.add(Path(source_path).name)
    return {"source_files": sorted(source_files), "image_names": sorted({item["image_name"] for item in mappings})}


def candidate_pool(draft: dict, candidates: list[dict], context: dict) -> list[dict]:
    sources = set(context["source_files"])
    same_source = [item for item in candidates if item.get("source_file") in sources]
    if not same_source:
        # Bounded text fallback only when the source trace has no candidate.
        text = normalize_text(draft.get("question_text", ""))
        tokens = set(text.split())
        return [item for item in candidates if tokens and tokens.intersection(normalize_text(item.get("question_text", "")).split())][:150]
    image_names = set(context["image_names"])
    image_matches = [item for item in same_source if image_names.intersection(item.get("source_image_names") or [])]
    if image_matches:
        return image_matches
    number = draft.get("question_number")
    same_number = [item for item in same_source if str(item.get("question_number", "")) == str(number)] if number is not None else []
    return same_number or same_source[:120]


def score_match(draft: dict, candidate: dict, context: dict) -> dict:
    weights = CONFIG["weights"]
    source = float(candidate.get("source_file") in set(context["source_files"]))
    number = float(draft.get("question_number") is not None and str(candidate.get("question_number")) == str(draft.get("question_number")))
    text = similarity(draft.get("question_text", ""), candidate.get("question_text", ""))
    math = similarity(" ".join(draft.get("question_math", [])), candidate.get("question_text", "") + " " + candidate.get("solution_text", ""))
    options = similarity(" ".join(item.get("content", "") for item in draft.get("options", [])), candidate.get("question_text", ""))
    source_images = set(candidate.get("source_image_names") or [])
    image = float(bool(source_images.intersection(context["image_names"])))
    signals = {"source": source, "number": number, "text": text, "math": math, "options": options, "image": image}
    return {"score": sum(weights[name] * signals[name] for name in weights), "signals": signals}


def validate_draft(draft: dict) -> dict:
    flags = set(draft.get("flags") or [])
    errors: list[str] = []
    if not (draft.get("question_text") or "").strip(): errors.append("empty_question_text")
    qtype = draft.get("question_type", "unknown")
    options = draft.get("options") or []
    labels = [item.get("label") for item in options]
    if qtype == "unknown": errors.append("question_type_unknown")
    if qtype == "multiple_choice" and set(labels) != {"A", "B", "C", "D"}: errors.append("incomplete_abcd")
    if "duplicate_option_label" in flags or "empty_question_text" in flags: errors.append("parser_severe_flag")
    if not draft.get("raw_ocr_text"): errors.append("missing_raw_ocr_trace")
    return {"pass": not errors, "errors": errors, "warnings": sorted(flags)}


def decide(draft: dict, scored: list[dict], validation: dict) -> dict:
    top = scored[0] if scored else None
    runner = scored[1] if len(scored) > 1 else None
    score = top["match_score"] if top else 0.0
    ambiguous = bool(top and runner and score - runner["match_score"] < CONFIG["ambiguity_gap"])
    duplicate = bool(top and score >= CONFIG["duplicate"])
    severe_flags = {"possible_cross_page_question", "question_number_out_of_order", "possible_missing_question_number"}
    # A number of entries originate from one cropped figure in a Word
    # question.  They are valuable OCR/LaTeX supplements but are not complete
    # questions: forcing A/B/C/D validation on them makes the review queue look
    # broken.  An exact image association can safely link the *source* only;
    # it never approves its OCR text or publishes anything to students.
    visual_supplement = bool(
        top
        and top.get("breakdown", {}).get("image") == 1
        and draft.get("question_type") == "unknown"
        and not ambiguous
    )
    auto = bool(top and score >= CONFIG["auto_approve"] and validation["pass"] and not ambiguous and not severe_flags.intersection(draft.get("flags") or []))
    if auto: status, reason = "APPROVED", "very_high_match_and_validation_pass"
    elif visual_supplement: status, reason = "LINKED_SUPPLEMENT", "exact_image_link_ocr_is_supplement_not_question"
    elif not top: status, reason = "REVIEW_REQUIRED", "no_candidate"
    elif ambiguous: status, reason = "REVIEW_REQUIRED", "ambiguous_candidates"
    elif not validation["pass"]: status, reason = "REVIEW_REQUIRED", "validation_failed"
    else: status, reason = "REVIEW_REQUIRED", "manual_confirmation_required"
    return {"status": status, "reason": reason, "match_score": score, "ambiguous": ambiguous, "duplicate": duplicate, "matched_candidate_id": top["candidate_id"] if top else None}


def dry_run(drafts: list[dict], candidates: list[dict], manifest: dict) -> list[dict]:
    outcomes = []
    for draft in drafts:
        context = source_context(draft.get("images", []), manifest, draft.get("source_path"))
        pool = candidate_pool(draft, candidates, context)
        scored = []
        for candidate in pool:
            result = score_match(draft, candidate, context)
            scored.append({"candidate_id": candidate.get("candidate_id"), "match_score": result["score"], "breakdown": result["signals"]})
        scored.sort(key=lambda item: item["match_score"], reverse=True)
        validation = validate_draft(draft)
        decision = decide(draft, scored, validation)
        outcomes.append({"parser_draft_id": draft["id"], "source_context": context, "normalized_parser_data": normalize_text(draft.get("question_text", "")), "raw_parser_data": draft, "top_matches": scored[:3], "validation": validation, **decision})
    return outcomes
