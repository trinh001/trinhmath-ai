# Current task — M2 Data Factory Slice 1

## Goal

Create a deterministic, read-only pipeline that turns candidate-question evidence into one of exactly three review outcomes:

- `MATCHED`
- `REVIEW_REQUIRED`
- `INVALID`

This task does **not** approve or release questions.

## Required pipeline

`candidate → source match → structural checks → duplicate checks → evidence/confidence → outcome + reason codes`

Reuse existing modules such as `candidate_triage.py`, `source_review.py`, `source_quality.py`, and `math_verifier.py` where appropriate. Avoid parallel duplicate implementations.

## Matching evidence

Use deterministic evidence where available, for example:

- source/file identity
- question number
- page/location
- normalized text similarity
- option/answer agreement
- formula/text fingerprint
- image dependency/proximity

The implementation may choose weights/thresholds, but they must be explicit, testable, and included in evidence rather than hidden heuristics.

## Outcome rules

`MATCHED`: source association and required structure are sufficiently supported, with no blocking ambiguity.

`REVIEW_REQUIRED`: plausible candidate but any important ambiguity remains, including formula/image dependence, conflicting answer evidence, multiple plausible source matches, or confidence below the safe threshold.

`INVALID`: candidate is unusable, e.g. missing essential stem/structure, impossible source association, unrecoverable parse, or deterministic invalidity.

Unknown/unclassified output is not allowed. If the classifier cannot assign one of the three outcomes, fail closed and report it.

## Deliverables

- deterministic data contract/evidence object
- matcher/classifier implementation
- duplicate detection or integration with existing duplicate logic
- read-only batch runner/report
- reason-code counts and outcome counts
- tests covering safe, ambiguous, duplicate, incomplete, image/formula-dependent, and conflicting cases
- regression test run
- concise HANDOFF update after completion

## Data safety

The batch runner may read local candidates/source metadata to measure the pipeline, but must not alter raw OCR/source files, production database records, approval states, release states, or student data. Do not send this data to external APIs.

## Done when

1. All fixtures receive exactly one of the three outcomes.
2. The read-only local run reports the full candidate population it can see and fails loudly if any candidate remains unclassified.
3. Tests pass.
4. Diff is reviewed for accidental DB/source/API changes.
5. Commit and push the branch; do not merge it automatically.
