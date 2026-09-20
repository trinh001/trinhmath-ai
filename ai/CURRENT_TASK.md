# Current task — M2 Integration Pack (S2 + S3)

## Goal

Turn M2-S1 from a standalone classifier into a usable teacher workflow and measure it against the real local candidate population without changing source data or release state.

This is one coherent package, not a sequence of tiny tasks.

## Workstream A — Real local read-only measurement

1. Locate the existing local candidate dataset and the minimum source metadata needed by M2-S1.
2. Build a tested adapter if the real schema differs from the classifier input contract.
3. Run classification locally, read-only.
4. Require every processed row to end in exactly:
   - `MATCHED`
   - `REVIEW_REQUIRED`
   - `INVALID`
5. Produce aggregate-only metrics:
   - total processed
   - outcome counts
   - top reason-code counts
   - duplicate counts
   - image/formula review counts
   - source-match ambiguity/low-confidence counts
   - math-conflict counts
   - unclassified count
6. Do not commit raw/private report contents.

## Workstream B — Review queue model

Create or extend a pure/testable module that converts classification results + existing source-review context into review rows.

Each row should expose, as available:
- candidate id
- outcome
- reason codes
- priority
- source file/name/question number
- candidate question/solution preview
- source-match confidence/evidence summary
- duplicate evidence
- image/formula dependency
- math-verifier status
- current teacher review state

Ordering should be explicit and deterministic. Prioritize actionable `REVIEW_REQUIRED` rows, not already-resolved rows.

Reuse `source_review.py` / `local_review_workflow.py` where possible.

## Workstream C — Teacher UX

Integrate the queue into the existing Streamlit teacher/review surface instead of creating a disconnected second app.

Minimum UX:
- outcome filter
- reason-code filter
- source/lesson filter when available
- concise row list with priority/reason
- detail panel showing candidate + source/provenance + evidence
- existing image/formula review context when present
- review-only action/note using an existing safe workflow or a narrowly scoped compatible extension
- next-item flow after a review action

Do not auto-approve. Do not auto-release. A review action here may classify/flag/correct, but approval remains behind the existing approval workflow.

## Workstream D — Verification

Add tests for:
- queue priority/order
- filter behavior
- evidence propagation
- already-reviewed rows
- invalid rows
- image/formula ambiguity
- duplicate rows
- no approval/release mutation
- real-schema adapter using sanitized fixtures

Run:
- targeted tests
- full `toan-ai-local` pytest
- syntax/import checks
- `git diff --check`
- secret scan
- safe read-only real batch aggregate report

## Deliverables

- real-schema adapter if needed
- review-queue module or safe extension of existing review module
- app integration
- tests
- aggregate measurement summary in non-private project docs
- concise HANDOFF update

## Stop conditions

Stop before:
- destructive DB migration;
- raw-source/OCR rewrite;
- external transfer of private data;
- automatic approval/release;
- a required change that weakens existing release gates.

Otherwise complete the package, commit, push, and stop for GPT/GitHub review. Do not merge `main`.
