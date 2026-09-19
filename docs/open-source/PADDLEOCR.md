# PaddleOCR review

## Identity

- Official repository: https://github.com/PaddlePaddle/PaddleOCR
- Local review clone: `external/PaddleOCR`
- Reviewed commit: `dab3fe35379033fdcb2d0e9572fac0b36c9a9ebf` (2026-09-19)
- License: Apache License 2.0 (`external/PaddleOCR/LICENSE`)
- Stated capability: general OCR plus optional document parsing, layout,
  formula/table handling and document-to-Markdown workflows.

## Principal dependencies

The current package metadata requires `paddlex[ocr-core]`, PyYAML, requests,
aiohttp and typing extensions. Optional capability sets include document
parsing, document-to-Markdown and information extraction; actual inference
also needs a selected engine (PaddlePaddle or a supported Transformers stack).
Model, engine and GPU/CUDA compatibility are separate deployment concerns.

## TrinhMath fit and recommendation

PaddleOCR is a strong independent comparison/fallback for Pix2Text, especially
for page layout and conventional text OCR. Use it as a separately versioned
local package/service for a benchmark or retry route. Do not install it into
the existing Streamlit environment and do not import its source into the app.

If selected later, its output must map to the same provider-neutral raw OCR
record as Pix2Text. A retry must not overwrite the first provider's result or
advance an item beyond candidate/draft status.

## Risks and controls

- **Heavy and moving stack:** Paddlex, inference engine, models and GPU builds
  can conflict. Pin a tested environment and expose a small local interface.
- **Version churn:** current 3.x APIs differ from older examples. Follow the
  checked package version's documentation, not an unpinned snippet.
- **Formula reliability:** benchmark formulae separately from normal text;
  unsuccessful or incomplete formula extraction is a review block.
- **Data locality:** use only local inference unless a later task explicitly
  approves a remote provider and its data handling.

## Status

Prepared as a fallback/benchmark source only. No package, model or code was
integrated.
