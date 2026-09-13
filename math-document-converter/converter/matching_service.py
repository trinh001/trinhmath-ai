"""Dry-run orchestration. Never writes to TrinhMath's question bank."""
from __future__ import annotations
import json
from pathlib import Path
from .matching import dry_run
from .trinhmath_bridge import default_trinhmath_dir


def run_dry_match(store, data_dir: Path, trinhmath_dir: Path | None = None) -> tuple[list[dict], dict]:
    root = Path(trinhmath_dir or default_trinhmath_dir())
    candidates = json.loads((root / "question_candidates.json").read_text(encoding="utf-8"))
    manifest_path = Path(data_dir) / "trinhmath_bridge_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    drafts = []
    for row in store.parsed_questions(10000):
        item = dict(row)
        for key, fallback in (("question_math_json", []), ("options_json", []), ("images_json", []), ("flags_json", []), ("validation_json", {})):
            item[key.replace("_json", "")] = json.loads(item.get(key) or json.dumps(fallback))
        item["question_text"] = item["question_text"]
        item["raw_ocr_text"] = item["raw_ocr_text"]
        drafts.append(item)
    outcomes = dry_run(drafts, candidates, manifest)
    store.save_match_reviews(outcomes)
    report = {"total_parser_drafts": len(outcomes), "matched_high_confidence": 0, "matched_medium_confidence": 0, "matched_low_confidence": 0, "no_match": 0, "ambiguous_match": 0, "linked_supplements": 0, "auto_approve_candidates": 0, "review_required": 0, "duplicates": 0, "validation_failed": 0}
    for item in outcomes:
        score = item["match_score"]
        if not item.get("matched_candidate_id"): report["no_match"] += 1
        elif score >= .85: report["matched_high_confidence"] += 1
        elif score >= .70: report["matched_medium_confidence"] += 1
        else: report["matched_low_confidence"] += 1
        report["ambiguous_match"] += int(item["ambiguous"])
        report["duplicates"] += int(item["duplicate"])
        report["linked_supplements"] += int(item["status"] == "LINKED_SUPPLEMENT")
        report["auto_approve_candidates"] += int(item["status"] == "APPROVED")
        report["review_required"] += int(item["status"] == "REVIEW_REQUIRED")
        report["validation_failed"] += int(not item["validation"]["pass"])
    return outcomes, report
