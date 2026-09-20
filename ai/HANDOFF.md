# TrinhMath AI — Persistent handoff

Default startup context: read only `AGENTS.md` and this file, then inspect Git state. Read other `ai/*` docs only when the active task needs them. Never put secrets, private source/OCR, database contents, or student data in handoff files.

## LAST COMPLETED

Milestone M1 AI Infrastructure is closed for now.

- DeepSeek transport/router/pilot guards are merged on `main`.
- Local launcher is merged in PR #7 at `37dd5a0a1fe7159be45bc640d80fb0499bde1014`.
- First real local pilot succeeded: 5/5 synthetic FAST tasks, 5 API calls, 326 input tokens, 1,912 output tokens, 0 failures.
- No real source/OCR/student data was sent and the API key was not printed or logged.

Do not keep expanding provider infrastructure unless a concrete product task requires it. 9Router and automatic Codex→DeepSeek coding handoff remain future tooling, not blockers for M2.

## CURRENT MILESTONE

M2 — Data Factory.

Target outcome: every candidate can be deterministically classified into `MATCHED`, `REVIEW_REQUIRED`, or `INVALID`, with auditable evidence. No candidate may become `APPROVED` or `RELEASED` automatically.

## ACTIVE TASK

Build the first production M2 slice:

source matching → structural validation → duplicate detection → confidence/evidence → review classification → read-only stats report.

Prefer deterministic/local logic. Use existing modules where possible instead of duplicating them.

## SAFETY BOUNDARIES

- Do not mutate raw source/OCR files, production database, student data, approval state, or release state.
- No external AI/API is required for this slice.
- Math/image ambiguity must route to `REVIEW_REQUIRED`.
- Work on a dedicated branch, run tests, inspect diff, commit, push, and stop for review before merge.

## SUCCESS CRITERIA

- Stable evidence schema for every classification.
- Deterministic tests for matching, duplicate detection, incomplete/broken questions, ambiguous formula/image cases, and confidence thresholds.
- A read-only CLI/report can process the local candidate set without changing source data or DB.
- Report counts by outcome/reason and surfaces unclassified cases as a failure.
- Existing regression tests remain green.

## NEXT EXACT ACTION

From latest `origin/main`, create a dedicated M2 branch. Inspect only the existing matcher/triage/source-review/verifier modules needed for this task, then implement the slice above. Do not reread the full project history.
