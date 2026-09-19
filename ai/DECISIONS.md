# Decision log

| Date | Decision | Reason and consequence |
| --- | --- | --- |
| 2026-09-19 | Keep the current architecture unchanged. | The task is preparation, not integration. Existing apps and release gates remain the source of truth. |
| 2026-09-19 | Clone Pix2Text, PaddleOCR, MinerU and docx shallowly under ignored `external/`. | Enables source review without committing nested repositories or importing code. Exact commits live in `external/README.md`. |
| 2026-09-19 | Pix2Text is the first OCR candidate. | It matches local formula/layout OCR needs and the Converter already documents it as the default provider. It still requires a benchmark and isolation. |
| 2026-09-19 | PaddleOCR is a fallback/benchmark, not a replacement. | It gives an independent OCR/layout path but brings an incompatible/heavy inference stack. |
| 2026-09-19 | MinerU is reference-only. | Its current license has additional terms and its stack is broad; no production adoption is authorized. |
| 2026-09-19 | docx is a later isolated export candidate. | It does not belong in the current Python app without a scoped Word-export architecture. |
| 2026-09-19 | Keep SymPy, MathLive and pgvector unvendored. | SymPy is already constrained in the current verifier; MathLive and pgvector solve later, unapproved scopes. |
| 2026-09-19 | Model roles: GPT planner/reviewer; Codex primary coder; DeepSeek batch reviewer/backup; Qwen optional vision/backup. | These are workflow roles, not an authorization to call paid APIs or auto-approve content. |

All source/license decisions require a fresh check at the exact version used in
a release. This log is technical preparation, not legal advice.
