# Current task

## Goal

Prepare a source-review and project-memory package so later Codex work can
continue safely without rediscovering project context.

## Completed preparation scope (historical)

- Used a separate working branch for the preparation work; consult Git rather than this historical note for the active branch.
- Prepared ignored shallow clones in `external/`: Pix2Text, PaddleOCR, MinerU,
  docx.
- Added one factual review per source and an adoption/risk overview.
- Added the `ai/` memory pack, including roles and safety rules.
- Did not modify application architecture/code, dependencies, data, release
  state or secrets.

## Validation for handoff

- Run `git diff --check` and review tracked/untracked status after staging only
  these preparation files.
- Do not run application or OCR tests merely for documentation; source clones
  and current user changes make no claim about runtime verification.

## Next implementation task (not authorized by this task)

Design a small golden-set benchmark and a provider-neutral local OCR contract.
It must be approved before installing Pix2Text/PaddleOCR or changing Converter
code.
