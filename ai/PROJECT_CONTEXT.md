# TrinhMath project context

## Product

TrinhMath AI is a local-first Vietnamese high-school mathematics learning and
question-bank system. Teachers ingest Word/PDF material, inspect OCR/parser
outputs, approve safe questions and release valid variants. Students practise
only released variants and receive topic-level learning guidance.

The repository has two independent local applications:

- `toan-ai-local/`: the Streamlit teacher/student app, question bank and
  release gates.
- `math-document-converter/`: the separate local OCR/parser workbench. Its
  output does not become student content automatically.

## Non-negotiable safety model

`source -> OCR/parser -> candidate -> draft -> structural validation -> math
verification -> teacher review -> approved question -> student variant ->
release validation`.

An OCR result, AI draft, confidence score or verifier result is not teacher
approval. Never infer missing formulae, diagrams, answer keys or source facts.
Ambiguity means `BLOCK + REQUIRE TEACHER REVIEW`.

## Data and secrets

Source documents, scanned images, raw OCR, question records, learner records,
SQLite databases, API keys and machine login state are local/private. Do not
commit, upload, replace, delete, fabricate or paste them into a prompt.

Read `../AGENTS.md`, `../PROJECT_REPORT_2026-09-13.md`,
`../GPT_CODEX_WORKFLOW.md` and the relevant application README before a code
change.
