"""Run M2 classification over explicit local JSON inputs and print aggregates only."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from candidate_classification import classify_candidates
from candidate_data_adapter import adapt_real_m2_inputs, aggregate_classification_metrics


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def run_measurement(candidate_path: Path, source_path: Path) -> dict:
    adapted = adapt_real_m2_inputs(_load(candidate_path), _load(source_path))
    report = classify_candidates(adapted["candidates"], adapted["source_match_input"])
    return {"schema_summary": adapted["schema_summary"], "metrics": aggregate_classification_metrics(report)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only aggregate M2 measurement.")
    parser.add_argument("--candidates", type=Path, default=Path("question_candidates.json"))
    parser.add_argument("--sources", type=Path, default=Path("source_catalog.json"))
    args = parser.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    print(json.dumps(run_measurement(args.candidates, args.sources), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
