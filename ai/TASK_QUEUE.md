# TrinhMath AI — Task queue

_Current source of truth for branch/commit is Git, not this file._

## ACTIVE — M2 Data Factory

1. **M2-S1 Candidate classification pipeline** — source matching, structural validation, duplicate checks, evidence/confidence, `MATCHED | REVIEW_REQUIRED | INVALID`, read-only report.
2. **M2-S2 Review queue UX** — show source vs parsed candidate, reason/evidence, fast teacher actions; no auto-approval.
3. **M2-S3 Batch processing/reporting** — process the full candidate set locally, measure reason buckets, identify OCR/parser bottlenecks.
4. **M2-S4 Math verification expansion** — add deterministic solvers/checkers for high-volume supported problem classes; unsupported cases stay review-required.

## NEXT — M3 Trusted Question Bank

- Promote only teacher-approved/verified candidates into the stable question schema.
- Preserve provenance, versions, verification evidence, reviewer and timestamps.
- Build coverage/statistics toward a materially useful approved bank.

## THEN — M4 Teacher Product

- Exam blueprint/selection.
- Duplicate/difficulty/answer-distribution checks.
- DOCX/PDF/LaTeX export with answer key, solutions, matrix/specification.

## LATER

- M5 student practice/adaptive learning.
- M6 AI generation/tutor and scale tooling.
- Optional developer orchestration: Codex→DeepSeek fallback worker and 9Router only after it solves a measured workflow problem.

## Global rules

Local/deterministic first. External AI only when it adds measurable value. No AI auto-approves or releases content. Stop on destructive DB migration, external private-data transfer, production release, or other stop conditions in `AGENTS.md`.
