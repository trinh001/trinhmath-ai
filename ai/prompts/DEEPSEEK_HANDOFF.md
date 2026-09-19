# DeepSeek handoff template

Dùng cho code/review sau khi DeepSeek provider đã được người dùng bật.

```text
ROLE: coding backup / reviewer for TrinhMath AI.

GOAL:
<one bounded task>

REPOSITORY CONTEXT:
- Read AGENTS.md
- Read ai/PROJECT_STATE.md
- Read ai/ARCHITECTURE.md
- Read ai/AI_RULES.md
- Read the target module and its tests

SCOPE:
<files/modules allowed>

DO NOT:
- touch secrets, OCR source, databases or student data
- approve/release math content
- refactor unrelated code
- push directly to main
- bypass tests

ACCEPTANCE:
<tests/behaviour that must pass>

OUTPUT:
1. concise plan
2. patch/review findings
3. tests run + result
4. remaining risks
5. files changed

If evidence is insufficient, return BLOCKED/NEEDS_CONTEXT instead of guessing.
```
