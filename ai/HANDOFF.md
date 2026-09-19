# Handoff for the next Codex task

Start by reading, in order:

1. `AGENTS.md`
2. `ai/PROJECT_CONTEXT.md`, `ai/ARCHITECTURE.md`, `ai/CURRENT_STATE.md`
3. `ai/DECISIONS.md`, `ai/AI_RULES.md`, `ai/TEST_STATUS.md`
4. `docs/open-source/OVERVIEW.md` and the one source review relevant to the task
5. the target module, its tests and current Git diff

## Safe next handoff prompt

```text
Read AGENTS.md and ai/*.md first. Plan a local-only benchmark of Pix2Text and
PaddleOCR using a teacher-approved non-private golden set. Do not install any
package, download models, call paid/remote APIs, alter OCR/provider code, touch
source records, or release questions. Return only: proposed contract, benchmark
schema, measurements, file plan, license/privacy risks, test plan and decisions
that require approval.
```

## Guardrails

- Preserve raw source/OCR and every review decision; do not mutate approval or
  release state in bulk.
- Keep source clones in `external/` out of Git and out of runtime imports.
- Never include API keys, database files, source documents, learner data or
  local machine state in commits, tests or prompts.
- Stop for a human decision before installing models, enabling a remote/VLM
  path, spending API credits, changing data schema or changing release logic.
