"""Export local Converter question-level provenance without modifying either app."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

from converter.question_provenance import (
    build_question_provenance_records,
    load_candidates,
    provenance_summary,
)
from converter.storage import ConverterStore
from converter.matching_service import run_dry_match


APP_DIR = Path(__file__).parent


def default_db_path() -> Path:
    configured = os.environ.get("MATH_CONVERTER_DATA_DIR")
    if configured:
        return Path(configured) / "converter.db"
    preferred = Path(r"E:\TrinhMath_Data\MathDocumentConverter\converter.db")
    return preferred if preferred.exists() else APP_DIR / "data" / "converter.db"


def read_provenance_rows(database_path: Path) -> list[dict]:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT
                pq.id AS parser_draft_id,
                pq.question_number,
                pq.question_text,
                pq.question_math_json,
                pq.options_json,
                pq.correct_answer,
                pq.solution,
                pq.images_json,
                pq.first_page_number,
                pq.last_page_number,
                pq.confidence AS parser_confidence,
                pq.flags_json,
                mr.matched_candidate_id,
                mr.match_score,
                mr.status AS match_status,
                mr.ambiguity,
                mr.validation_json,
                mr.source_context_json
            FROM parsed_questions pq
            JOIN match_reviews mr ON mr.parser_draft_id = pq.id
            WHERE mr.matched_candidate_id IS NOT NULL
            ORDER BY pq.document_id, pq.first_page_number, pq.id
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Export question-level provenance from Converter.")
    parser.add_argument("--db", type=Path, default=default_db_path())
    parser.add_argument(
        "--candidates",
        type=Path,
        default=APP_DIR.parent / "toan-ai-local" / "question_candidates.json",
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--refresh-matches",
        action="store_true",
        help="Refresh deterministic Converter dry-match rows before exporting provenance.",
    )
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    if args.refresh_matches:
        store = ConverterStore(args.db)
        run_dry_match(store, args.db.parent, args.candidates.parent)

    rows = read_provenance_rows(args.db)
    candidates = load_candidates(args.candidates)
    records = build_question_provenance_records(rows, candidates)
    summary = provenance_summary(records)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(args.output)

    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
