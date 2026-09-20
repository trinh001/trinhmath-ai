# TrinhMath AI — Persistent handoff

Default startup context: read only `AGENTS.md` and this file, then inspect Git state. Read other docs only when the active task needs them. Never put secrets, private source/OCR, database contents, or student data in handoff files.

## LAST COMPLETED

M2 Integration Pack is merged on `main` at `144c98484e2f1fa9e5a68bfa20d37781bad03eb0`.

Real local measurement:
- candidates: 4,843
- MATCHED: 0
- REVIEW_REQUIRED: 4,843
- INVALID: 0
- unclassified: 0

This is expected because the source catalog contains file-level metadata only.

## CURRENT PACKAGE

M2-S4 Question-level Provenance Bridge is implemented on branch `gpt/m2-question-provenance-2026-09-20`.

It adds:
- Converter question-level provenance export from parsed questions + match review data;
- explicit provenance trust rules;
- candidate-linked provenance index;
- M2 classifier requirement that confirmed matches use trusted provenance;
- TrinhMath loading of local `question_provenance.json`;
- one-click Windows cycle `M2_PROVENANCE_ONE_SHOT.bat`;
- CI coverage for both TrinhMath and Converter provenance modules.

Trusted provenance statuses are `APPROVED` and `APPROVED_MANUAL` from the Converter matching layer. This means trusted *source linkage*, not approved student content. Approval/release gates remain separate.

## IMPORTANT SAFETY

- file catalog metadata is explicitly `provenance_trusted=False`;
- REVIEW_REQUIRED / ambiguous / validation-failed Converter matches cannot become trusted provenance;
- trusted provenance can support M2 `MATCHED` but never sets `APPROVED` or `RELEASED`;
- no external API is used;
- raw source/OCR/student data remain local;
- `question_provenance.json` is gitignored.

## ONE-SHOT LOCAL ACTION

After this branch is merged, run `M2_PROVENANCE_ONE_SHOT.bat` from repo root.

It will:
1. read local Converter DB match/parser rows;
2. create local `toan-ai-local/question_provenance.json`;
3. rerun M2 classification on all 4,843 candidates;
4. print aggregate counts only.

Then open TrinhMath → “Phân tích kho đề” → “Hàng kiểm duyệt M2 — chỉ đối chiếu”.

## NEXT DECISION

Use the new aggregate after the one-shot cycle:
- if trusted provenance yields meaningful MATCHED rows, continue expanding trusted source linkage;
- if almost none are trusted, the bottleneck is Converter match-review coverage, not classifier thresholds;
- do not weaken source-match thresholds just to increase MATCHED.
