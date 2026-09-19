# Pix2Text review

## Identity

- Official repository: https://github.com/breezedeus/Pix2Text
- Local review clone: `external/Pix2Text`
- Reviewed commit: `f52e671247c14a29aa59b44e99849e00aee984cd` (2026-09-19)
- License: MIT (`external/Pix2Text/LICENSE`)
- Stated capability: Python OCR for layout, tables, text and mathematical
  formulae, emitting Markdown; it can process images and PDFs.

## Principal dependencies

Its `setup.py` lists `torch`, `torchvision`, `transformers`, `optimum` with
ONNX Runtime, `opencv-python`, `PyMuPDF`, `cnocr`, `cnstd`, `doclayout-yolo`
and related image/model packages. Optional extras add multilingual OCR,
FastAPI/Uvicorn serving, or LiteLLM-backed VLM calls. Model downloads and the
licenses of their weights must be evaluated separately from the MIT code.

## TrinhMath fit and recommendation

Pix2Text matches the existing local Converter's intended role: extract a
reviewable representation from scanned pages and preserve formula/image
context. The current Converter already describes Pix2Text as its default
provider, so use the published package or an isolated local service rather than
copying source files into `toan-ai-local`.

Start with a pinned package version in a dedicated OCR environment, exposing a
narrow local contract: input page/image path; output raw Markdown/LaTeX,
regions/confidence, provider+model versions and diagnostics. The main app must
record the result as a candidate/draft only.

## Risks and controls

- **Meaning loss:** a syntactically plausible formula can still be wrong.
  Preserve the source crop and require teacher comparison before approval.
- **Runtime weight:** PyTorch/model stacks are large and hardware-dependent;
  benchmark CPU and the GTX 1650 separately, one page at a time initially.
- **Vietnamese quality:** the README notes multilingual support through a
  different engine; measure Vietnamese/math pages explicitly rather than assume
  parity with English or Chinese.
- **Remote/VLM extras:** do not enable LiteLLM or online services in the local
  pipeline without an explicit privacy, cost and provider decision.

## Status

Approved only for a future, controlled local benchmark. No dependency,
model, service endpoint or product code was added by this preparation task.
