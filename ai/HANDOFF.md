# TrinhMath AI — Persistent handoff

Default startup context: read only `AGENTS.md` and this file, then inspect Git state. Read other docs only when the active task needs them. Never put secrets, private source/OCR, database contents, or student data in handoff files.

## LAST COMPLETED

Merged to `main`:

- M2 deterministic candidate classification
- M2 Review Queue integration
- real local-schema adapter
- question-level provenance bridge
- one-shot local M2 provenance cycle
- external Codex -> DeepSeek development fallback

Current main includes the external fallback launcher at commit:

`91dcb817b8c1343c9999387ace27ed1267d5a7ba`

The last known real M2 measurement before question-level provenance was:

- candidates: 4,843
- MATCHED: 0
- REVIEW_REQUIRED: 4,843
- INVALID: 0
- unclassified: 0

That result reflected file-level source metadata only and must not be treated as the post-provenance result.

## LATEST LOCAL M2 / M3 CHECKPOINT — 20/09/2026

- The local-only provenance cycle completed with 4,843 candidates and 779 question-level provenance records; none are trusted until an explicit teacher-approved source match exists.
- Outcomes remain fail-closed: `MATCHED=0`, `REVIEW_REQUIRED=4,843`, `INVALID=0`, `unclassified=0`. No approval or release state changed.
- Main review bottlenecks are low-confidence source matching (4,829), image/formula review (4,063), source-quality review (1,648), and duplicate candidates (1,043). Do not lower matching thresholds to improve these counts.
- The Converter now has a versioned M3 trusted-question foundation. Promotion requires an `APPROVED_MANUAL` teacher match, non-empty teacher evidence, source provenance, complete question structure, and non-contradicted math evidence. Promotion itself never releases content to students.
- Latest local checks: 110 `toan-ai-local` pytest tests, 9 fallback-tooling pytest tests, and six Converter checks (including trusted-bank gates) passed. No private runtime file is staged.

## DEVELOPMENT WORKFLOW

For long coding packages requiring automatic quota fallback:

1. put the complete task in `ai/DEV_TASK.md`;
2. prefer `START_DEV_TASK_AUTO.bat` for one-click Windows launch. It checks for a clean tree, syncs `main`, clears only a stale lock whose PID is no longer running, then starts `RUN_DEV_TASK_AUTO.bat` in a separate window;
3. do not launch `RUN_DEV_TASK_AUTO.bat` from inside an interactive Codex session, because the outer Codex can waste quota polling the inner Codex process;
4. direct `RUN_DEV_TASK_AUTO.bat` remains available for a normal terminal/external shell;
5. Codex is primary;
6. if Codex stops on quota/rate-limit, the external orchestrator switches to DeepSeek/Aider on the same git working tree;
7. DeepSeek route is selected by task complexity;
8. default completion is code + tests + validated diff, with no automatic commit/push;
9. the configured DeepSeek/Aider fallback is pre-authorized for public/tracked repository code and ordinary usage on the existing DeepSeek account; private/gitignored runtime data remains forbidden.

Private/local runtime files remain excluded from the DeepSeek fallback and Git.

## CURRENT TASK

`ai/DEV_TASK.md` now contains one cohesive package:

M2 real local cycle
-> diagnose deterministic bottlenecks
-> finish M2 gates
-> expand Math Verifier only if measurements justify it
-> build M3 Trusted Question Bank foundation
-> build controlled teacher-approved promotion service
-> full tests
-> validated diff

Do not weaken thresholds just to increase MATCHED.

Do not allow any AI to auto-approve or auto-release content.

## SAFETY

- file metadata alone is not trusted question-level provenance;
- ambiguous/conflicting evidence fails closed;
- raw source/OCR/student data stays local;
- no external AI should receive private source/OCR/student content;
- sending public/tracked repository code to the configured DeepSeek fallback is allowed for this development workflow;
- ordinary use of the existing DeepSeek API key for that fallback is authorized; additional paid services/top-ups are not;
- trusted provenance is source-link evidence, not content approval;
- teacher approval and student release remain separate gates.

## NEXT AFTER CURRENT TASK

The pending provenance bridge is merged on main. The immediate next package is M3-S0 Teacher Confirm:
- show pending source_file + question_number bridge evidence locally;
- explicit teacher Confirm / Reject with audit history;
- keep raw Converter provenance unchanged;
- only teacher-confirmed derived bridge records may set provenance_trusted=True;
- rerun local M2 and report aggregates only.

After at least some teacher-confirmed trusted provenance exists, proceed to M3-S1 trusted seed review and explicit promotion into the versioned trusted bank.
