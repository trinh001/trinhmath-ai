# TrinhMath AI — Task queue

Git is the source of truth for branch/commit state.

## ACTIVE — M2 Data Factory Integration

### M2-S2/S3 Integration Pack
- Run M2-S1 on the real local candidate population in read-only mode.
- Adapt real local schema to the classifier contract if needed.
- Produce aggregate-only outcome/reason metrics.
- Build deterministic review queue from classification + existing source-review context.
- Integrate queue into teacher Streamlit UX.
- Keep review-only actions separate from approval/release.
- Test and push for review.

## NEXT — M2-S4 Verification expansion

After S2/S3 metrics identify the high-volume reason buckets:
- expand deterministic Math Verifier support only where it meaningfully reduces teacher review;
- improve formula/image/source adapters where evidence shows a real bottleneck;
- keep unsupported/ambiguous cases in teacher review.

## THEN — M3 Trusted Question Bank

- Stable approved-question schema with provenance/versioning/evidence/reviewer.
- Controlled promotion from reviewed candidates.
- Coverage goals and quality metrics.
- No AI-only approval.

## THEN — M4 Teacher Product

- Exam blueprint/selection.
- Duplicate/difficulty/answer-distribution validation.
- DOCX/PDF/LaTeX export with answer key, solutions, matrix/specification.

## PARALLEL AI INFRASTRUCTURE TRACK

Build only when a measured workflow needs it, but build it rigorously:
- task dispatcher / coding worker for Codex↔DeepSeek fallback;
- audit log: planner, executor, model/profile, branch, commit, tests, review;
- quota/budget/fallback policy;
- secrets isolation;
- fail-closed provider handling;
- optional 9Router only if multi-provider orchestration gives measurable benefit.

AI infrastructure must not bypass product safety, source privacy, DB controls, or review/release gates.

## GLOBAL RULES

Local/deterministic first. External AI only when it adds measurable value. No AI auto-approves or releases content.
