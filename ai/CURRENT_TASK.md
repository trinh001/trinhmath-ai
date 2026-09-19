# Current task

## Goal

Complete Phase 3 pilot preparation: an offline-only, bounded sanitized pilot runner with fixtures and audit schema; no API request, key or app/data integration.

## Scope

- Standalone Python modules, sanitized test fixtures and offline tests only; do not modify `app.py`, database, source/OCR, question bank, approvals or release flow.
- Align active documentation with GPT -> Codex -> DeepSeek FAST/PRO. Qwen is not active.
- Commit/push only after regression checks and diff review; use a new branch/PR, never merge it.

## Completion criteria

- Pilot policy defaults OFF/kill-switch ON; missing config, budgets, unsafe payload and malformed output fail closed before a transport call.
- FAST/PRO routing records a deterministic valid reason code; fake transport is the only transport used in tests.
- Existing tests and new offline tests pass; CI has no API/key dependency.
- `TASK_QUEUE`, `TEST_STATUS`, `HANDOFF` and changelog identify the next safe action.
