# External open-source references

This directory contains **shallow, local clones for review only**. They are not
submodules, vendored production code, or part of either TrinhMath runtime.
Their contents are deliberately ignored by Git so a later `git add .` cannot
accidentally import a large dependency tree or its nested Git metadata.

| Source | Official repository | Checked-out commit | Intended status |
| --- | --- | --- | --- |
| Pix2Text | https://github.com/breezedeus/Pix2Text | `f52e671247c14a29aa59b44e99849e00aee984cd` | first local OCR/formula candidate; package/service only |
| PaddleOCR | https://github.com/PaddlePaddle/PaddleOCR | `dab3fe35379033fdcb2d0e9572fac0b36c9a9ebf` | fallback benchmark; package/service only |
| MinerU | https://github.com/opendatalab/MinerU | `fb2cba72aa7dc114d50c0dd1187c876d2280eaa5` | document-pipeline reference; no integration planned |
| docx | https://github.com/dolanmiu/docx | `fda088d1da3772474bec9c40feb210cebb304f97` | future TypeScript Word-export reference; no integration planned |

Checked out on 2026-09-19. Read `../docs/open-source/OVERVIEW.md` before
installing or incorporating any source. Do not copy code or model weights into
TrinhMath without a separate, reviewed task.
