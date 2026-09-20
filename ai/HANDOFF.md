# TrinhMath AI — Persistent handoff

Đọc `AGENTS.md`, `ai/PROJECT_STATE.md`, `ai/CURRENT_TASK.md`, `ai/TASK_QUEUE.md`, `ai/DECISIONS.md`, `ai/TEST_STATUS.md`, tài liệu provider liên quan và Git state trước khi hành động. Không đưa secret, private source/OCR, database hay student data vào handoff.

## LAST COMPLETED

M2 Integration Pack (S2 + S3) is implemented on a dedicated branch. It adds a
tested adapter for the local schema, read-only aggregate measurement, a
deterministic review queue and teacher-screen integration. The queue reuses
`source_review.py` and `local_review_workflow.py`; its only action is the
existing reversible flag on eligible local drafts.

## CURRENT STATE

- Real local measurement processed 4,843 candidates; every row was classified
  and no raw report was committed. See `ai/M2_INTEGRATION_REPORT.md` for safe
  aggregate counts only.
- The source catalog has file metadata but lacks question-level comparison
  evidence, so all rows correctly remain `REVIEW_REQUIRED`; no candidate was
  auto-approved or released.

## ACTIVE BRANCH

Use `git branch --show-current`; this checkpoint is on the dedicated M2 branch
created from `origin/main` on 20/09/2026. Do not merge `main` automatically.

## TEST STATUS

Targeted adapter/queue/source-review tests, full `toan-ai-local` pytest,
syntax/import, diff check and secret scan are required before review. The real
measurement reports zero unclassified rows.

## KNOWN RISKS

- Thresholds are deterministic policy defaults, not teacher approval.
- File-level catalog metadata cannot establish question-level provenance.
- Image/formula ambiguity and unsupported Math verification remain teacher work.

## BLOCKERS

None for code verification. The next milestone needs curated question-level
source evidence and teacher review, not a weaker matching threshold.

## NEXT EXACT ACTION

Review this branch/PR. Do not auto-approve, release, merge `main`, rewrite
source/OCR, or send local data to a provider.
