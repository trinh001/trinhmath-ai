# TrinhMath AI — Persistent handoff

Default startup context: read only `AGENTS.md` and this file, then inspect Git state. Read other `ai/*` docs only when the active task needs them. Never put secrets, private source/OCR, database contents, or student data in handoff files.

## LAST COMPLETED

M2-S1 Candidate Classification Pipeline is merged on `main` at `1aeb2279bc7aec24c0b635db09a4dd5e14fde40b`.

It deterministically produces exactly `MATCHED`, `REVIEW_REQUIRED`, or `INVALID` with auditable source-match/structure/duplicate/conflict/confidence evidence. It is read-only and never approves or releases content.

Review hardening already merged:
- math operators/signs are preserved during comparison;
- operator-mismatched questions cannot be confirmed;
- missing solution is review-required rather than destructively invalid;
- source catalogs keyed by source id are supported.

M1 AI Infrastructure remains operational: DeepSeek local pilot succeeded 5/5 synthetic FAST tasks. Do not expand AI infrastructure without a concrete product need, but any required infrastructure change must retain fail-closed, audit, budget, privacy and branch/test/review gates.

## CURRENT MILESTONE

M2 — Data Factory Integration Pack.

The next package is deliberately larger than a single micro-step:

1. Measure M2-S1 against the real local candidate population in read-only mode.
2. Build a review-queue model from classifications.
3. Integrate the queue into the teacher UX.
4. Preserve all approval/release gates.
5. Produce regression + batch statistics sufficient to decide the next M2 slice.

## ACTIVE TASK

Build M2-S2/S3 together:

`real local read-only classification → review queue model → teacher review UX → derived metrics/report`

Reuse existing `source_review.py`, `local_review_workflow.py`, `candidate_classification.py`, and current app review surfaces instead of creating a parallel review system.

## PRODUCT REQUIREMENTS

Teacher should be able to:
- filter by `MATCHED / REVIEW_REQUIRED / INVALID` and reason code;
- prioritize highest-value review cases;
- see candidate text next to source/provenance/evidence;
- see why a row was classified that way;
- record a review-only decision/correction note without automatically approving or releasing;
- move quickly to the next item.

A classification result is evidence, never teacher approval.

## REAL-BATCH RULES

- Local read-only use of the existing candidate/source metadata is allowed for this milestone.
- Do not commit private candidate/source/OCR data or generated reports containing source content.
- Aggregate counts/reason-code statistics may be documented if they contain no private content.
- Do not call external AI for the real batch.
- If the actual local schema does not match M2-S1 assumptions, adapt through a tested local adapter; do not rewrite raw source data.

## SAFETY BOUNDARIES

Do not:
- mutate raw OCR/source files;
- destructively migrate the production DB;
- alter student data;
- auto-set `APPROVED` or `RELEASED`;
- send source/student/private data to an external provider;
- bypass existing teacher/release validation.

## SUCCESS CRITERIA

- Real local batch runs read-only and every visible candidate receives one of the three M2 outcomes or the run fails loudly.
- Aggregate outcome/reason statistics are produced without committing private source content.
- Review queue is deterministic and testable.
- Teacher UX exposes classification evidence and existing source-review context.
- Review-only actions remain distinct from approval/release.
- Existing relevant tests and full `toan-ai-local` regression remain green.
- Diff review confirms no accidental provider/API/DB/source mutation.

## NEXT EXACT ACTION

From latest `origin/main`, create a dedicated branch and execute the whole M2 Integration Pack above. Use Codex for core integration. DeepSeek is not required for this package.
