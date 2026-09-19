# Architecture snapshot

## Components

```text
Teacher Word/PDF/source files
        |
        v
Math Document Converter (local queue, cache, OCR, parser, source references)
        |
        v
TrinhMath candidate/draft records -- teacher comparison/review --> approved bank
        |                                                         |
        +-- raw source/OCR preserved                              v
                                                release validation -> student practice
                                                                          |
                                                                          v
                                                           grading + topic guidance
```

`toan-ai-local/app.py` is the existing Streamlit entry point. Risk-sensitive
logic is progressively extracted into testable modules such as
`variant_validation.py`, `grading.py`, `adaptive_learning.py`,
`math_verifier.py`, `source_quality.py`, `source_review.py`,
`candidate_triage.py`, `curriculum_coverage.py` and
`variant_review_service.py`. Preserve their public compatibility with the app
unless a separate migration is approved.

## Boundaries

- OCR providers create evidence/candidates; they never release student content.
- Math Verifier V1 accepts only reviewed structured SymPy expressions and may
  return `VERIFIED`, `CONTRADICTED`, `INCONCLUSIVE` or `UNSUPPORTED`.
- `INCONCLUSIVE` and `UNSUPPORTED` are not successful verification.
- The Converter may link artifacts to source material but cannot approve or
  publish a question.
- This repository has no approved cloud deployment boundary yet.

## External-source boundary

`external/` holds ignored shallow source clones for human/Codex inspection.
They are not runtime dependencies or submodules. See `../docs/open-source/`.
