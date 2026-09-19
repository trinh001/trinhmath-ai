# Open-source preparation overview

_Prepared 2026-09-19. This is an evaluation record, not an integration plan._

## Scope and rules

Four official repositories were cloned shallowly to `external/` for local
inspection. Their nested repositories are ignored by the parent Git repository;
only this documentation and `external/README.md` are intended to be committed.
No package was installed, no model was downloaded, no source document was sent
to a remote service, and no secret was created or copied.

TrinhMath's release gate remains unchanged:

```text
source -> OCR/parser -> candidate -> draft -> structural validation
       -> math verification -> teacher review -> approved question
       -> student variant -> release validation
```

OCR output is evidence to review, never a reason to approve or release a
question. Unclear formulae, diagrams, page boundaries, answer keys or OCR text
remain `BLOCK + REQUIRE TEACHER REVIEW`.

## Decision summary

| Source | License at reviewed revision | Main TrinhMath use | Recommendation | Review |
| --- | --- | --- | --- | --- |
| [Pix2Text](PIX2TEXT.md) | MIT | local image/PDF text, layout and mathematical-formula OCR | Use its Python package behind the existing local OCR provider only after a small benchmark; do not copy code. | First priority |
| [PaddleOCR](PADDLEOCR.md) | Apache-2.0 | OCR/layout/formula fallback and benchmark | Run in a separate environment/service. Do not put its large runtime into the current app environment. | Second priority |
| [MinerU](MINERU.md) | MinerU Open Source License (Apache-2.0 plus terms) | learn document-to-Markdown/JSON pipeline patterns | Architecture/reference only for now. Re-review the license and attribution before product use. | Research only |
| [docx](DOCX.md) | MIT | future `.docx` export with Word equations | Use the npm package in a future isolated TypeScript export service; do not vendor source. | Later |

## References to add later, not cloned

| Source | Why it matters | Recommended adoption point |
| --- | --- | --- |
| [SymPy](https://github.com/sympy/sympy) | structured algebraic verification | Already a constrained dependency of `toan-ai-local`; keep the existing verifier boundary. Do not make it parse raw OCR/LaTeX without a reviewed conversion step. |
| [MathLive](https://github.com/arnog/mathlive) | browser math-field and LaTeX input | Evaluate only when a web/teacher equation-entry UI is scoped. Keep teacher transcription separate from raw source. |
| [pgvector](https://github.com/pgvector/pgvector) | similarity retrieval inside PostgreSQL | Evaluate only after the question-bank schema and a RAG privacy/quality design are approved. It is not needed for current local SQLite work. |

## Before any adoption

1. Create a separate implementation task and pin the package/model versions.
2. Benchmark with a consented, non-student, teacher-reviewed golden set of
   100–300 representative pages, including Vietnamese text, equations, tables,
   MathType renderings and diagrams.
3. Measure formula fidelity, layout fidelity, throughput, VRAM/RAM, install
   repeatability and failure behaviour—not just a single accuracy number.
4. Preserve source image, raw output, provider/version/model, settings,
   confidence and timestamps. Route every ambiguous result to teacher review.
5. Recheck license, bundled-model terms, notices and third-party dependencies
   at the exact version being released. Do not treat this review as legal advice.

## Risk register

| Risk | Control |
| --- | --- |
| Formula OCR silently changes meaning | retain image and raw OCR; structural/Math Verifier checks; teacher approval |
| GPU/CPU packages conflict with the Streamlit environment | use a dedicated environment or local service with a narrow versioned contract |
| Downloaded models consume storage or contact external hosts | explicit approval before installation; cache location and hashes documented |
| License/attribution changes | pin commit/version, retain notices, re-review at upgrade/release |
| OCR output bypasses the bank gate | provider may only create candidates/drafts; it cannot write approved/released records |
