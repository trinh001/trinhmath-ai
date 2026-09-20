# TrinhMath AI — Current automated development task

Run this package through `RUN_DEV_TASK_AUTO.bat`.

The launcher runs Codex first. If Codex stops because quota/rate-limit is exhausted,
DeepSeek/Aider continues from the SAME git working tree.

AUTHORIZATION FOR THIS TASK:
- DeepSeek/Aider may process PUBLIC/TRACKED REPOSITORY CODE only;
- ordinary DeepSeek API usage on the already-configured account is authorized;
- do not read/send gitignored private runtime data, OCR/source documents, databases,
  question-bank JSON, student data, credentials, or secrets to external models;
- local deterministic scripts may process private runtime data and expose only aggregate/sanitized results.

## TASK — M3-S0 Teacher Confirm for pending provenance bridges

Goal: let the teacher explicitly confirm or reject pending provenance bridges produced from
unique `source_file + question_number` evidence, then rerun M2 using only confirmed links
as trusted provenance. No automatic trust, approval, or release.

### 0. Startup

- Inspect git branch/status/diff.
- Read only `AGENTS.md` and `ai/HANDOFF.md` first.
- Do not reread the whole repository.
- Preserve all existing fail-closed M2/M3 behavior.

### 1. Local confirmation store

Add a small local-only confirmation store for pending provenance bridges.

Requirements:
- gitignored runtime file;
- immutable/auditable event history;
- explicit states at minimum:
  - PENDING_TEACHER_CONFIRMATION
  - CONFIRMED
  - REJECTED
- record reviewer, reason, timestamp, source_record_id, candidate_id,
  source_file, page/question number, and previous state;
- never modify raw OCR/source documents or original Converter provenance export;
- confirmation records are local runtime data and must never be committed.

### 2. Teacher-confirm UI

In the local review UI, show only pending bridge rows.

For each pending row, show concise evidence:
- source file/name;
- page/page range if available;
- question number;
- candidate id;
- parser/source text snippet if already available in safe local structures;
- match score/breakdown if available;
- reason the bridge exists: unique source_file + question_number;
- current confirmation state and audit history.

Actions:
- Confirm provenance link
- Reject provenance link
- Return to pending / undo via an explicit audited action if practical

Never auto-confirm.
Never bulk-confirm.
Never treat confirmation as content approval or student release.

### 3. Confirmed provenance adapter

When a teacher confirms a pending bridge:
- derive a confirmed provenance record locally;
- preserve original source_record_id lineage;
- set an explicit provenance kind for teacher-confirmed bridge;
- only then set provenance_trusted=True for that derived confirmation record;
- do not rewrite the original Converter export;
- rejected/pending bridges stay untrusted.

The classifier may consume confirmed provenance through the existing adapter.
Do not lower matching thresholds.

### 4. Rerun local M2 measurement

After implementation, rerun the local-only M2 cycle using the confirmation store.

Report aggregate only:
- candidate_total
- question_provenance_total
- pending_bridge_total
- confirmed_bridge_total
- rejected_bridge_total
- trusted_question_provenance_total
- MATCHED
- REVIEW_REQUIRED
- INVALID
- unclassified
- top reason codes

Do not send private content externally.

### 5. Acceptance criteria

This package is complete when:
- pending bridges are visible to teacher;
- confirm/reject actions are explicit and audited;
- raw Converter provenance remains unchanged;
- only confirmed bridge records can become trusted;
- pending/rejected cannot become MATCHED through trust;
- no auto-approval/release exists;
- all runtime confirmation data is gitignored;
- local M2 rerun completes with aggregate metrics;
- tests cover state transitions and trust gating.

### 6. Tests

Run:
- `python -m pytest -q tests` in `toan-ai-local`
- `python -m pytest -q dev-tools/tests`
- Converter core/parser/matching/review/provenance/trusted-bank tests
- py_compile changed Python modules
- `git diff --check`
- verify no private/runtime/secret path is staged or tracked

Add regression tests for:
- pending bridge starts untrusted;
- CONFIRMED bridge becomes trusted only through teacher confirmation store;
- REJECTED stays untrusted;
- undo/re-pending stays untrusted;
- audit trail preserves prior state;
- M2 does not create MATCHED from unconfirmed bridge.

### 7. Git workflow

Work on the launcher-created branch.

Safe default:
code -> tests -> validated diff -> STOP

Do not merge main.
Do not commit/push unless explicitly permitted by launcher/user.
Do not commit private/runtime data.

### 8. Stop conditions

Stop only if:
- destructive DB migration is required;
- data loss risk appears;
- private data would need to go to an external model/service;
- a new paid service, top-up, or budget increase is required;
- production deployment is required;
- auto-approval or auto-release would be required.

Ordinary bugs/test failures should be fixed and the package should continue.

### 9. Final report

BRANCH:
PRIMARY WORKER:
FALLBACK USED:

TEACHER CONFIRM:
pending_bridge_total:
confirmed_bridge_total:
rejected_bridge_total:
audit_ready:

M2 AFTER CONFIRM:
trusted_provenance:
MATCHED:
REVIEW_REQUIRED:
INVALID:
unclassified:

TESTS:

SAFETY:
auto_confirmed:
auto_approved:
auto_released:
external_private_data_calls:
private_files_staged:

NEXT PACKAGE:
Give exactly one next package. Move to M3-S1 trusted seed review only after teacher-confirmed
trusted provenance exists.
