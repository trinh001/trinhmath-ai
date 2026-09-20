from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


SCHEMA_VERSION = "1.0"


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class ConverterStore:
    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self):
        # A bridge import can add many Word images while Streamlit refreshes.
        # Give concurrent readers/writers time to finish instead of failing fast.
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def session(self):
        """Đóng kết nối thật sự sau mỗi thao tác; cần thiết trên Windows để không khóa DB."""
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self):
        with self.session() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY,
                    source_path TEXT NOT NULL UNIQUE,
                    source_hash TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    page_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS pages (
                    id INTEGER PRIMARY KEY,
                    document_id INTEGER NOT NULL,
                    page_number INTEGER NOT NULL,
                    classification TEXT NOT NULL,
                    direct_text TEXT NOT NULL DEFAULT '',
                    input_hash TEXT NOT NULL,
                    UNIQUE(document_id, page_number),
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY,
                    page_id INTEGER NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    ocr_mode TEXT NOT NULL DEFAULT 'AUTO',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    message TEXT NOT NULL DEFAULT '',
                    started_at TEXT,
                    finished_at TEXT,
                    FOREIGN KEY(page_id) REFERENCES pages(id)
                );
                CREATE TABLE IF NOT EXISTS ocr_results (
                    id INTEGER PRIMARY KEY,
                    page_id INTEGER NOT NULL UNIQUE,
                    cache_key TEXT NOT NULL UNIQUE,
                    schema_version TEXT NOT NULL,
                    markdown TEXT NOT NULL,
                    latex_json TEXT NOT NULL DEFAULT '[]',
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(page_id) REFERENCES pages(id)
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS parsed_questions (
                    id INTEGER PRIMARY KEY,
                    document_id INTEGER NOT NULL,
                    first_page_number INTEGER,
                    last_page_number INTEGER,
                    question_number INTEGER,
                    question_type TEXT NOT NULL,
                    question_text TEXT NOT NULL,
                    question_math_json TEXT NOT NULL DEFAULT '[]',
                    options_json TEXT NOT NULL DEFAULT '[]',
                    correct_answer TEXT,
                    solution TEXT,
                    images_json TEXT NOT NULL DEFAULT '[]',
                    confidence REAL NOT NULL DEFAULT 0,
                    raw_ocr_text TEXT NOT NULL,
                    flags_json TEXT NOT NULL DEFAULT '[]',
                    validation_json TEXT NOT NULL DEFAULT '{}',
                    parser_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                );
                CREATE INDEX IF NOT EXISTS idx_parsed_questions_document ON parsed_questions(document_id);
                CREATE TABLE IF NOT EXISTS parser_unassigned_blocks (
                    id INTEGER PRIMARY KEY,
                    document_id INTEGER NOT NULL,
                    page_number INTEGER,
                    text TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    parser_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                );
                CREATE TABLE IF NOT EXISTS match_reviews (
                    id INTEGER PRIMARY KEY, parser_draft_id INTEGER NOT NULL UNIQUE,
                    matched_candidate_id TEXT, match_score REAL NOT NULL, duplicate_score REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL, decision_reason TEXT NOT NULL, ambiguity INTEGER NOT NULL DEFAULT 0,
                    score_breakdown_json TEXT NOT NULL, validation_json TEXT NOT NULL,
                    source_context_json TEXT NOT NULL, normalized_parser_text TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    FOREIGN KEY(parser_draft_id) REFERENCES parsed_questions(id)
                );
                CREATE TABLE IF NOT EXISTS match_audit_log (
                    id INTEGER PRIMARY KEY, parser_draft_id INTEGER NOT NULL, matched_candidate_id TEXT,
                    decision TEXT NOT NULL, decision_reason TEXT NOT NULL, match_score REAL NOT NULL,
                    validation_json TEXT NOT NULL, approved_by TEXT, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS trusted_questions (
                    question_id TEXT PRIMARY KEY,
                    current_version INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS trusted_question_versions (
                    id INTEGER PRIMARY KEY,
                    question_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    candidate_id TEXT,
                    source_record_id TEXT,
                    source_file TEXT NOT NULL,
                    source_name TEXT,
                    source_page INTEGER,
                    source_page_end INTEGER,
                    question_number INTEGER,
                    grade TEXT,
                    chapter TEXT,
                    topic TEXT,
                    lesson TEXT,
                    skill TEXT,
                    cognitive_level TEXT,
                    difficulty TEXT,
                    question_type TEXT NOT NULL,
                    stem TEXT NOT NULL,
                    options_json TEXT NOT NULL DEFAULT '[]',
                    correct_answer TEXT,
                    solution TEXT,
                    formulas_json TEXT NOT NULL DEFAULT '[]',
                    image_assets_json TEXT NOT NULL DEFAULT '[]',
                    source_match_evidence_json TEXT NOT NULL DEFAULT '{}',
                    math_verification_evidence_json TEXT NOT NULL DEFAULT '{}',
                    teacher_review_evidence_json TEXT NOT NULL DEFAULT '{}',
                    reviewer TEXT NOT NULL,
                    reviewed_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    UNIQUE(question_id, version),
                    FOREIGN KEY(question_id) REFERENCES trusted_questions(question_id)
                );
                CREATE INDEX IF NOT EXISTS idx_trusted_question_versions_question ON trusted_question_versions(question_id);
                """
            )

    @staticmethod
    def sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def log(self, level: str, message: str):
        with self.session() as connection:
            connection.execute("INSERT INTO events(created_at, level, message) VALUES (?, ?, ?)", (now(), level, message))

    def register_document(self, path: Path, kind: str, pages: list[dict]) -> int:
        path = Path(path).resolve()
        source_hash = self.sha256_file(path)
        timestamp = now()
        with self.session() as connection:
            # Serialize the select/update pair so clicking once during a UI
            # refresh can never create duplicate `source_path` rows.
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute("SELECT id, source_hash FROM documents WHERE source_path = ?", (str(path),)).fetchone()
            if existing and existing["source_hash"] == source_hash:
                return int(existing["id"])
            if existing:
                # Keep the document row (its unique source path stays stable),
                # clear dependent records, then refresh it in place.
                old_page_ids = [row["id"] for row in connection.execute("SELECT id FROM pages WHERE document_id = ?", (existing["id"],)).fetchall()]
                for page_id in old_page_ids:
                    connection.execute("DELETE FROM ocr_results WHERE page_id = ?", (page_id,))
                    connection.execute("DELETE FROM jobs WHERE page_id = ?", (page_id,))
                connection.execute("DELETE FROM pages WHERE document_id = ?", (existing["id"],))

                connection.execute(
                    "UPDATE documents SET source_hash=?, kind=?, page_count=?, updated_at=? WHERE id=?",
                    (source_hash, kind, len(pages), timestamp, existing["id"]),
                )
                document_id = int(existing["id"])
            else:
                cursor = connection.execute(
                    "INSERT INTO documents(source_path, source_hash, kind, page_count, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (str(path), source_hash, kind, len(pages), timestamp, timestamp),
                )
                document_id = int(cursor.lastrowid)
            for page in pages:
                page_hash = hashlib.sha256(f"{source_hash}:{page['number']}:{page['classification']}".encode()).hexdigest()
                page_cursor = connection.execute(
                    "INSERT INTO pages(document_id, page_number, classification, direct_text, input_hash) VALUES (?, ?, ?, ?, ?)",
                    (document_id, page["number"], page["classification"], page.get("text", ""), page_hash),
                )
                status = "SKIPPED" if page["classification"] == "TEXT_PAGE" else "WAITING"
                message = "Đã trích trực tiếp văn bản" if status == "SKIPPED" else "Chờ OCR"
                connection.execute("INSERT INTO jobs(page_id, status, message) VALUES (?, ?, ?)", (int(page_cursor.lastrowid), status, message))
            return document_id

    def next_waiting_job(self):
        with self.session() as connection:
            return connection.execute(
                """SELECT jobs.*, pages.page_number, pages.classification, pages.input_hash,
                          documents.source_path, documents.kind
                   FROM jobs JOIN pages ON jobs.page_id = pages.id
                   JOIN documents ON pages.document_id = documents.id
                   WHERE jobs.status IN ('WAITING', 'RETRY')
                   ORDER BY jobs.id LIMIT 1"""
            ).fetchone()

    def set_job(self, job_id: int, status: str, message: str = "", increment_attempt: bool = False):
        with self.session() as connection:
            if status == "PROCESSING":
                connection.execute(
                    "UPDATE jobs SET status=?, message=?, started_at=?, attempts=attempts+? WHERE id=?",
                    (status, message, now(), int(increment_attempt), job_id),
                )
            elif status in {"SUCCESS", "WARNING", "FAILED", "SKIPPED"}:
                connection.execute("UPDATE jobs SET status=?, message=?, finished_at=? WHERE id=?", (status, message, now(), job_id))
            else:
                connection.execute("UPDATE jobs SET status=?, message=? WHERE id=?", (status, message, job_id))

    def save_result(self, page_id: int, cache_key: str, markdown: str, latex: list[str], result: dict):
        with self.session() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO ocr_results(page_id, cache_key, schema_version, markdown, latex_json, result_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (page_id, cache_key, SCHEMA_VERSION, markdown, json.dumps(latex, ensure_ascii=False), json.dumps(result, ensure_ascii=False), now()),
            )

    def cached_result(self, cache_key: str):
        with self.session() as connection:
            return connection.execute("SELECT * FROM ocr_results WHERE cache_key = ?", (cache_key,)).fetchone()

    def summary(self) -> dict:
        with self.session() as connection:
            rows = connection.execute("SELECT status, COUNT(*) AS amount FROM jobs GROUP BY status").fetchall()
            data = {row["status"]: row["amount"] for row in rows}
            data["TOTAL"] = sum(data.values())
            return data

    def progress_stats(self) -> dict:
        """Counts plus a conservative ETA from completed OCR jobs."""
        summary = self.summary()
        total = summary.get("TOTAL", 0)
        success = summary.get("SUCCESS", 0)
        failed = summary.get("FAILED", 0) + summary.get("WARNING", 0)
        skipped = summary.get("SKIPPED", 0)
        completed = success + failed + skipped
        waiting = summary.get("WAITING", 0) + summary.get("RETRY", 0) + summary.get("PROCESSING", 0)
        with self.session() as connection:
            row = connection.execute(
                """SELECT AVG((julianday(finished_at) - julianday(started_at)) * 86400.0) AS seconds
                   FROM jobs WHERE status='SUCCESS' AND started_at IS NOT NULL AND finished_at IS NOT NULL"""
            ).fetchone()
        seconds_per_page = float(row["seconds"] or 0)
        return {
            "total": total,
            "completed": completed,
            "success": success,
            "failed": failed,
            "skipped": skipped,
            "waiting": waiting,
            "ratio": completed / total if total else 0.0,
            "seconds_per_page": seconds_per_page,
            "eta_seconds": int(seconds_per_page * waiting) if seconds_per_page > 0 else None,
        }

    def jobs(self, limit: int = 100):
        with self.session() as connection:
            return connection.execute(
                """SELECT jobs.id, jobs.status, jobs.ocr_mode, jobs.attempts, jobs.message,
                          documents.source_path, pages.page_number, pages.classification
                   FROM jobs JOIN pages ON jobs.page_id = pages.id
                   JOIN documents ON pages.document_id = documents.id
                   ORDER BY jobs.id DESC LIMIT ?""",
                (limit,),
            ).fetchall()

    def retry_failed(self):
        with self.session() as connection:
            return connection.execute("UPDATE jobs SET status='RETRY', message='Chờ thử lại' WHERE status IN ('FAILED', 'WARNING')").rowcount

    def recent_events(self, limit: int = 80):
        with self.session() as connection:
            return connection.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def pages_for_parsing(self):
        """Return direct text and completed OCR without changing the OCR tables."""
        with self.session() as connection:
            rows = connection.execute(
                """SELECT documents.id AS document_id, documents.source_path, documents.kind,
                          pages.id AS page_id, pages.page_number, pages.classification, pages.direct_text,
                          jobs.status, ocr_results.markdown, ocr_results.latex_json, ocr_results.result_json
                   FROM documents
                   JOIN pages ON pages.document_id=documents.id
                   JOIN jobs ON jobs.page_id=pages.id
                   LEFT JOIN ocr_results ON ocr_results.page_id=pages.id
                   WHERE (jobs.status='SUCCESS' AND ocr_results.id IS NOT NULL)
                      OR (pages.classification='TEXT_PAGE' AND TRIM(pages.direct_text) <> '')
                   ORDER BY documents.id, pages.page_number"""
            ).fetchall()
        return rows

    def replace_parsed_document(self, document_id: int, questions: list[dict], unassigned_blocks: list[dict]) -> None:
        """Atomically replace one document's parser output; OCR remains immutable."""
        timestamp = now()
        with self.session() as connection:
            connection.execute("DELETE FROM parser_unassigned_blocks WHERE document_id=?", (document_id,))
            connection.execute("DELETE FROM parsed_questions WHERE document_id=?", (document_id,))
            for question in questions:
                connection.execute(
                    """INSERT INTO parsed_questions(
                           document_id, first_page_number, last_page_number, question_number, question_type,
                           question_text, question_math_json, options_json, correct_answer, solution, images_json,
                           confidence, raw_ocr_text, flags_json, validation_json, parser_version, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        document_id, question.get("source_page"), question.get("source_page_end"), question.get("question_number"),
                        question.get("question_type", "unknown"), question.get("question_text", ""),
                        json.dumps(question.get("question_math", []), ensure_ascii=False), json.dumps(question.get("options", []), ensure_ascii=False),
                        question.get("correct_answer"), question.get("solution"), json.dumps(question.get("images", []), ensure_ascii=False),
                        float(question.get("confidence", 0)), question.get("raw_ocr_text", ""),
                        json.dumps(question.get("flags", []), ensure_ascii=False), json.dumps(question.get("validation", {}), ensure_ascii=False),
                        question.get("parser_version", "question-parser-v1"), timestamp, timestamp,
                    ),
                )
            for block in unassigned_blocks:
                connection.execute(
                    "INSERT INTO parser_unassigned_blocks(document_id, page_number, text, reason, parser_version, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (document_id, block.get("page"), block.get("text", ""), block.get("reason", "unassigned"), "question-parser-v1", timestamp),
                )

    def parsed_summary(self) -> dict:
        with self.session() as connection:
            row = connection.execute("SELECT COUNT(*) AS questions, SUM(CASE WHEN confidence >= .7 THEN 1 ELSE 0 END) AS confident FROM parsed_questions").fetchone()
            unassigned = connection.execute("SELECT COUNT(*) AS amount FROM parser_unassigned_blocks").fetchone()["amount"]
        return {"questions": int(row["questions"] or 0), "confident": int(row["confident"] or 0), "unassigned": int(unassigned or 0)}

    def parsed_questions(self, limit: int = 100):
        with self.session() as connection:
            return connection.execute(
                """SELECT parsed_questions.*, documents.source_path
                   FROM parsed_questions JOIN documents ON documents.id=parsed_questions.document_id
                   ORDER BY parsed_questions.updated_at DESC, parsed_questions.id DESC LIMIT ?""", (limit,)
            ).fetchall()

    def save_match_reviews(self, outcomes: list[dict]) -> None:
        timestamp = now()
        with self.session() as connection:
            for item in outcomes:
                top = (item.get("top_matches") or [{}])[0]
                duplicate_score = float(item.get("match_score", 0)) if item.get("duplicate") else 0.0
                connection.execute(
                    """INSERT INTO match_reviews(parser_draft_id, matched_candidate_id, match_score, duplicate_score, status, decision_reason, ambiguity, score_breakdown_json, validation_json, source_context_json, normalized_parser_text, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(parser_draft_id) DO UPDATE SET matched_candidate_id=excluded.matched_candidate_id, match_score=excluded.match_score, duplicate_score=excluded.duplicate_score, status=excluded.status, decision_reason=excluded.decision_reason, ambiguity=excluded.ambiguity, score_breakdown_json=excluded.score_breakdown_json, validation_json=excluded.validation_json, source_context_json=excluded.source_context_json, normalized_parser_text=excluded.normalized_parser_text, updated_at=excluded.updated_at""",
                    (
                        item["parser_draft_id"],
                        item.get("matched_candidate_id"),
                        float(item.get("match_score", 0)),
                        duplicate_score,
                        item["status"],
                        item["reason"],
                        int(item.get("ambiguous", False)),
                        json.dumps(top.get("breakdown", {}), ensure_ascii=False),
                        json.dumps(item.get("validation", {}), ensure_ascii=False),
                        json.dumps(item.get("source_context", {}), ensure_ascii=False),
                        item.get("normalized_parser_data", ""),
                        timestamp,
                        timestamp,
                    ),
                )
                connection.execute(
                    "INSERT INTO match_audit_log(parser_draft_id, matched_candidate_id, decision, decision_reason, match_score, validation_json, approved_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        item["parser_draft_id"],
                        item.get("matched_candidate_id"),
                        item["status"],
                        item["reason"],
                        float(item.get("match_score", 0)),
                        json.dumps(item.get("validation", {}), ensure_ascii=False),
                        "SYSTEM_DRY_RUN",
                        timestamp,
                    ),
                )

    def match_summary(self) -> dict:
        with self.session() as connection:
            rows = connection.execute("SELECT status, COUNT(*) amount FROM match_reviews GROUP BY status").fetchall()
        return {row["status"]: row["amount"] for row in rows}

    def match_reviews(self, limit: int = 100, status: str | None = None):
        """Return review rows with their immutable parser/source context.

        This deliberately reads from the converter database only.  A reviewer
        decision is not a publication action and can therefore never change
        TrinhMath's student-facing question bank by accident.
        """
        query = """
            SELECT match_reviews.*, parsed_questions.question_number,
                   parsed_questions.question_type, parsed_questions.question_text,
                   parsed_questions.question_math_json, parsed_questions.options_json,
                   parsed_questions.correct_answer, parsed_questions.solution,
                   parsed_questions.images_json, parsed_questions.confidence AS parser_confidence,
                   parsed_questions.raw_ocr_text, parsed_questions.flags_json,
                   parsed_questions.validation_json AS parser_validation_json,
                   documents.source_path, parsed_questions.first_page_number,
                   parsed_questions.last_page_number
            FROM match_reviews
            JOIN parsed_questions ON parsed_questions.id=match_reviews.parser_draft_id
            JOIN documents ON documents.id=parsed_questions.document_id
        """
        values: list[object] = []
        if status and status != "Tất cả":
            query += " WHERE match_reviews.status=?"
            values.append(status)
        query += " ORDER BY match_reviews.updated_at DESC, match_reviews.id DESC LIMIT ?"
        values.append(limit)
        with self.session() as connection:
            return connection.execute(query, values).fetchall()

    def get_match_review_for_promotion(self, parser_draft_id: int):
        """Return the joined match/parser/document row needed by M3 promotion.

        This method is intentionally separate from the review-queue query. It
        returns explicit aliases so the promotion service can map evidence
        fields without depending on UI-facing column names.
        """
        with self.session() as connection:
            return connection.execute(
                """
                SELECT
                    mr.id AS match_review_id,
                    mr.parser_draft_id,
                    mr.matched_candidate_id,
                    mr.match_score,
                    mr.duplicate_score,
                    mr.status AS match_status,
                    mr.decision_reason,
                    mr.ambiguity,
                    mr.score_breakdown_json,
                    mr.validation_json AS match_validation_json,
                    mr.source_context_json,
                    mr.normalized_parser_text,
                    mr.created_at AS match_created_at,
                    mr.updated_at AS match_updated_at,
                    pq.document_id,
                    pq.first_page_number,
                    pq.last_page_number,
                    pq.question_number,
                    pq.question_type,
                    pq.question_text,
                    pq.question_math_json,
                    pq.options_json,
                    pq.correct_answer,
                    pq.solution,
                    pq.images_json,
                    pq.confidence AS parser_confidence,
                    pq.raw_ocr_text,
                    pq.flags_json,
                    pq.validation_json AS parser_validation_json,
                    pq.parser_version,
                    d.source_path,
                    d.kind
                FROM match_reviews mr
                JOIN parsed_questions pq ON pq.id = mr.parser_draft_id
                JOIN documents d ON d.id = pq.document_id
                WHERE mr.parser_draft_id = ?
                """,
                (parser_draft_id,),
            ).fetchone()

    def record_manual_match_decision(self, parser_draft_id: int, decision: str, reason: str, approved_by: str = "TEACHER") -> None:
        """Record an auditable reviewer decision without touching source questions."""
        allowed = {"REVIEW_REQUIRED", "APPROVED_MANUAL", "REJECTED"}
        if decision not in allowed:
            raise ValueError("Trạng thái duyệt không hợp lệ")
        timestamp = now()
        with self.session() as connection:
            row = connection.execute(
                "SELECT matched_candidate_id, match_score, validation_json FROM match_reviews WHERE parser_draft_id=?",
                (parser_draft_id,),
            ).fetchone()
            if not row:
                raise ValueError("Không tìm thấy kết quả ghép để duyệt")
            connection.execute(
                "UPDATE match_reviews SET status=?, decision_reason=?, updated_at=? WHERE parser_draft_id=?",
                (decision, reason.strip() or "manual_review", timestamp, parser_draft_id),
            )
            connection.execute(
                "INSERT INTO match_audit_log(parser_draft_id, matched_candidate_id, decision, decision_reason, match_score, validation_json, approved_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (parser_draft_id, row["matched_candidate_id"], decision, reason.strip() or "manual_review", float(row["match_score"]), row["validation_json"], approved_by, timestamp),
            )

    def trusted_question_summary(self) -> dict:
        with self.session() as connection:
            rows = connection.execute("SELECT status, COUNT(*) AS amount FROM trusted_questions GROUP BY status").fetchall()
            versions = connection.execute("SELECT COUNT(*) AS amount FROM trusted_question_versions").fetchone()["amount"]
        return {
            "questions": {row["status"]: row["amount"] for row in rows},
            "versions": int(versions or 0),
        }
