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

## TASK — M3-S1 Teacher Review Pilot: create the first trusted seed set

Goal: turn the current 0 trusted provenance state into a small, teacher-reviewed,
versioned trusted seed set without weakening any safety threshold.

### 0. Startup

- Inspect git branch/status/diff.
- Read only `AGENTS.md` and `ai/HANDOFF.md` first.
- Do not reread the whole repository.
- Preserve all M2/M3 fail-closed rules already merged.

### 1. Build a local-only review pilot

Create or improve a teacher review workflow that works only on local data and does not
send private question content to external services.

The pilot should:
- rank REVIEW_REQUIRED rows by safest deterministic review priority;
- prefer rows with strongest source/question evidence first;
- never mark anything approved automatically;
- show enough evidence for a teacher to make a source-link decision quickly;
- support explicit actions:
  - APPROVED_MANUAL
  - REVIEW_REQUIRED
  - REJECTED
- record reviewer, reason, timestamp, previous state, and audit trail;
- be reversible where existing architecture allows it;
- clearly separate source-match approval from trusted-bank promotion and student release.

### 2. High-confidence review shortlist

Create a deterministic local shortlist generator for the first seed set.

Target:
- 20 to 50 questions maximum for the pilot;
- only rows with the strongest available evidence;
- exclude ambiguity, parser validation failure, source-quality hard failure,
  unresolved image/formula dependency, and contradictory math evidence;
- do not lower source-match thresholds;
- do not use an LLM to decide approval.

The shortlist may be exported locally as a gitignored JSON/CSV summary if useful,
but must not be committed.

### 3. Review UI efficiency

In the local Streamlit review queue, add only concrete usability improvements that reduce
teacher time, such as:
- next/previous;
- keyboard-friendly or single-click decision buttons;
- filters for evidence/reason;
- evidence summary;
- source file/page/question number;
- parser question text/options/answer/solution;
- formula/image flags;
- current match score/breakdown;
- audit history.

Do not expose raw OCR bulk unless explicitly requested in the UI.

### 4. Controlled promotion to M3 trusted bank

After a teacher sets APPROVED_MANUAL:
- allow an explicit separate "Promote to Trusted Bank" action;
- run all existing M3 fail-closed gates;
- create a versioned trusted question;
- show promotion success/failure reason;
- never auto-release to students;
- never bulk-promote without explicit teacher approval evidence.

Add a local summary:
- reviewed_total
- approved_manual
- rejected
- still_review_required
- promoted_to_trusted
- promotion_blocked
- trusted_bank_total
- trusted_bank_versions

### 5. Pilot acceptance criteria

Architecture is ready when:
- the review shortlist is deterministic;
- no automatic approval exists;
- every teacher decision is auditable;
- promotion is explicit and separate from review;
- trusted question history is versioned;
- student release remains a separate gate;
- private runtime data remains gitignored;
- tests cover review and promotion state transitions;
- no public/external API receives private question content.

### 6. Tests

Run:
- `python -m pytest -q tests` in `toan-ai-local`
- `python -m pytest -q dev-tools/tests`
- Converter core/parser/matching/review/provenance/trusted-bank tests
- py_compile changed Python modules
- `git diff --check`
- check private/runtime/secret files are not staged/tracked

Add regression tests for:
- shortlist exclusion rules
- APPROVED_MANUAL audit trail
- rejected/re-review states
- promotion success
- promotion fail-closed cases
- version history remains immutable

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

REVIEW PILOT:
shortlist_count:
review_ui_ready:
audit_ready:
promotion_ready:

TESTS:

SAFETY:
auto_approved:
auto_released:
external_private_data_calls:
private_files_staged:

NEXT PACKAGE:
Give exactly one next package. Prefer exam-generation/export only after at least a small
teacher-approved trusted seed set exists.
