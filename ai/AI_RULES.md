# AI roles and operating rules

## Roles

| Role | Responsibility | Boundary |
| --- | --- | --- |
| GPT | planner and reviewer; turns discussion into a bounded handoff | does not silently alter the repository or approve mathematics/content |
| Codex | primary coder; reads project context, makes minimal changes, tests and reports evidence | does not call paid APIs, commit secrets, overwrite data or release questions |
| DeepSeek | batch reviewer/backup; may assist with structured text review when explicitly approved | does not replace OCR evidence, teacher review or Math Verifier |
| Qwen | optional vision/backup candidate | evaluate only through a controlled benchmark; it is not mandatory |
| Teacher | final authority over source, formulae, solutions, answers and release | never delegate final approval to a model |

## Required behaviour

1. Keep context compact: GPT provides a short `CODEX_HANDOFF`; Codex reads the
   relevant repository files and executes only the approved scope.
2. Never equate model confidence with correctness. Preserve raw inputs,
   provenance, version and review evidence.
3. Do not send private source material, student data, database content or
   secrets to an external model/service unless a separate explicit approval
   defines provider, data scope, retention, cost and consent.
4. An unclear diagram, MathType fragment, formula, answer or page boundary is
   `BLOCK + REQUIRE TEACHER REVIEW`.
5. No model may create an approval/release state transition. Automation may
   create a candidate/draft and a review queue only.
6. Treat `INCONCLUSIVE` and `UNSUPPORTED` verifier outcomes as non-verification.
7. Log reviewable AI activity with provider/model/version, prompt class (never
   secrets), input artifact reference, timestamp, output and human decision.

## Handoff template

```text
Mục tiêu: ...
Phạm vi: ...
Không được đổi: ...
Hoàn thành khi: ...
Kiểm tra cần chạy: ...
Rủi ro/quyết định còn mở: ...
```

Do not include credentials, private OCR/source images, learner data, databases
or unreviewed question content in a handoff.
