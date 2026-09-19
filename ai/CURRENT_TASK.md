# Current task

## Goal

Push the completed reversible Phase 1 checkpoint and observe CI: optional DeepSeek provider contract and FAST/PRO router, with no external network/API usage and no app/data integration.

## Scope

- Standalone Python modules and offline tests only; do not modify `app.py`, database, source/OCR, question bank, approvals or release flow.
- Align active documentation with GPT -> Codex -> DeepSeek FAST/PRO. Qwen is not active.
- Commit/push only after regression checks and diff review; update existing PR #3, never merge it.

## Completion criteria

- Provider is OFF by default; dry-run/missing key/malformed output fail closed.
- Router emits named deterministic reason codes for FAST/PRO policy.
- Existing tests and new offline tests pass; CI has no API/key dependency.
- `TASK_QUEUE`, `TEST_STATUS`, `HANDOFF` and changelog identify the next safe action.
