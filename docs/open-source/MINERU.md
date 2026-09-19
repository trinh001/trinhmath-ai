# MinerU review

## Identity

- Official repository: https://github.com/opendatalab/MinerU
- Local review clone: `external/MinerU`
- Reviewed commit: `fb2cba72aa7dc114d50c0dd1187c876d2280eaa5` (2026-09-19)
- License: **MinerU Open Source License**—based on Apache-2.0 but with extra
  commercial thresholds and an online-service attribution obligation
  (`external/MinerU/LICENSE.md`). It is not plain Apache-2.0.
- Stated capability: parse PDF/OFD/EPUB/HTML/images and several office formats
  into Markdown and JSON.

## Principal dependencies

The package requires Python 3.10–3.14 and a substantial stack including
DocVortex, Gradio, OpenAI client library, pypdfium2, ModelScope,
Hugging Face Hub, OpenCV, FastAPI, ONNX Runtime and others. Optional extras add
Torch/Transformers and platform-specific VLM runtimes (`vllm` on Linux or
`lmdeploy`/Qwen utilities on Windows). Some tests explicitly use a remote
parse-server.

## TrinhMath fit and recommendation

MinerU is valuable as a reference for durable document ingestion: page-level
artifacts, Markdown/JSON outputs, rendering and pipeline boundaries. It is too
broad and operationally heavy for the present local Converter, which already
has a queue, cache, source links and a teacher-release gate.

Use it for architecture study only. Do not vendor it, install it into the
current app, or depend on its remote/server paths. A future standalone proof of
concept would require an explicit licensing, attribution, model, privacy and
resource review before it can touch real teaching documents.

## Risks and controls

- **License conditions:** a third-party online service needs prominent MinerU
  attribution; high MAU/revenue thresholds require a separate commercial
  license. Legal/product review is required before any release.
- **Large dependency surface:** isolate it completely if tested.
- **Remote-capable components:** prohibit remote parsing/API use by default;
  inspect configuration before a test.
- **Duplicate scope:** adopting it wholesale risks bypassing or duplicating the
  existing source-to-review workflow.

## Status

Reference-only. No package, model or endpoint was configured.
