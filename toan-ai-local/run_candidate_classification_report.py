"""Read-only CLI for deterministic M2 candidate-classification reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from candidate_classification import classify_candidates


def _load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read {label} JSON: {error}") from error


def build_report(candidate_path: Path, source_path: Path | None = None) -> dict[str, Any]:
    """Load explicitly supplied JSON files and return a derived report only."""
    candidates = _load_json(candidate_path, "candidate")
    sources = _load_json(source_path, "source") if source_path else []
    return classify_candidates(candidates, sources)


def main() -> int:
    # Windows PowerShell may start Python with a legacy CP1252 stdout codec.
    # The report can contain Vietnamese reason text, so make local CLI output
    # deterministic without changing either input file.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    parser = argparse.ArgumentParser(description="Build a read-only M2 candidate-classification report.")
    parser.add_argument("--candidates", required=True, type=Path, help="Explicit local JSON candidate list.")
    parser.add_argument("--sources", type=Path, help="Optional explicit local JSON source metadata list.")
    parser.add_argument("--output", type=Path, help="Optional derived report path; inputs are never changed.")
    args = parser.parse_args()
    try:
        report = build_report(args.candidates, args.sources)
    except ValueError as error:
        parser.error(str(error))
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if report["unclassified_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
