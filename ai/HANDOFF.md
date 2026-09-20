# TrinhMath AI — Persistent handoff

Đọc `AGENTS.md`, `ai/PROJECT_STATE.md`, `ai/CURRENT_TASK.md`, `ai/TASK_QUEUE.md`, `ai/DECISIONS.md`, `ai/TEST_STATUS.md`, tài liệu provider liên quan và Git state trước khi hành động. Không đưa secret, private source/OCR, database hay student data vào handoff.

## LAST COMPLETED

M2-S1 Candidate Classification Pipeline is implemented as a deterministic,
read-only local slice.  It produces exactly `MATCHED`, `REVIEW_REQUIRED`, or
`INVALID`; it never changes approval or release state.

## CURRENT STATE

- `toan-ai-local/candidate_classification.py` combines explicit source-match
  evidence, structural/source-quality checks, duplicate detection, optional
  structured Math Verifier results, confidence scoring and clear reason codes.
- `run_candidate_classification_report.py` reads only explicitly supplied JSON
  candidate/source metadata and creates a derived report. It does not discover
  a database, OCR/source files, student data, or call any API.
- Ambiguous source/image/formula/math/duplicate cases fail closed to
  `REVIEW_REQUIRED`; missing essential structure, unrecoverable parse and
  mathematical contradiction are `INVALID`.

## ACTIVE BRANCH

Use `git branch --show-current`; this checkpoint is on the dedicated M2 branch
created from `origin/main` on 20/09/2026. Do not merge `main` automatically.

## TEST STATUS

M2 targeted tests and the full `toan-ai-local` suite pass locally (87 tests).
The synthetic CLI report classifies all 5 fixture rows with no unclassified
result. Empty injected environments remain isolated from system DeepSeek
variables.

## KNOWN RISKS

- Thresholds are deterministic policy defaults, not teacher approval.
- A real local batch must be supplied explicitly and its report reviewed; no
  classification is an approval/release decision.
- Image/formula ambiguity and unsupported Math verification remain teacher work.

## BLOCKERS

None for code verification. A real candidate/source batch is deliberately out
of scope until a user selects it for read-only local analysis.

## NEXT EXACT ACTION

Review this branch/PR, then choose a separately authorized, read-only local
batch for measurement. Do not auto-approve, release, merge `main`, or send data
to a provider.
