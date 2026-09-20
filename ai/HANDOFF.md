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

## DEVELOPMENT WORKFLOW

For long coding packages requiring automatic quota fallback:

1. put the complete task in `ai/DEV_TASK.md`;
2. start with `RUN_DEV_TASK_AUTO.bat`;
3. Codex is primary;
4. if Codex stops on quota/rate-limit, the external orchestrator switches to DeepSeek/Aider on the same git working tree;
5. DeepSeek route is selected by task complexity;
6. default completion is code + tests + validated diff, with no automatic commit/push;
7. the configured DeepSeek/Aider fallback is pre-authorized for public/tracked repository code and ordinary usage on the existing DeepSeek account; private/gitignored runtime data remains forbidden.

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

Use the real post-provenance M2 aggregate and the resulting M3 foundation to choose one next product package. Prefer moving toward the teacher workflow: trusted bank -> exam generation -> Word/PDF export, unless measured M2 bottlenecks still block safe promotion.
