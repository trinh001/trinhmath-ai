# Current task

## Goal

Complete the reversible Phase 2 transport-adapter checkpoint on a branch from current main: injected transport contract and guardrails, with no external network/API usage and no app/data integration.

## Scope

- Standalone Python modules and offline tests only; do not modify `app.py`, database, source/OCR, question bank, approvals or release flow.
- Align active documentation with GPT -> Codex -> DeepSeek FAST/PRO. Qwen is not active.
- Commit/push only after regression checks and diff review; use a new branch/PR, never merge it.

## Completion criteria

- Provider is OFF by default; dry-run/missing key/malformed output fail closed. An injected fake transport is the only transport used in tests.
- Router emits named deterministic reason codes for FAST/PRO policy.
- Existing tests and new offline tests pass; CI has no API/key dependency.
- `TASK_QUEUE`, `TEST_STATUS`, `HANDOFF` and changelog identify the next safe action.
