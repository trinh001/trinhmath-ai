# Roadmap

## Now: safe content operations

1. Teacher-review a small, representative set of local drafts against source.
2. Resolve formula/MathType/image uncertainty with a clearer source or explicit
   teacher transcription; do not guess.
3. Release only variants that pass the existing structural and review gates.
4. Test a complete student journey once there is enough safe, balanced content.

## Next: evidence-driven OCR improvement

1. Build a consented, teacher-reviewed 100–300 page golden set.
2. Benchmark Pix2Text first, then PaddleOCR as an independent fallback.
3. Keep provider outputs versioned, separate and reviewable; choose a provider
   only after accuracy, performance, hardware and failure-mode evaluation.
4. Consider MinerU patterns only if a specific document-ingestion gap remains.

## Later: planned capabilities

- A reviewed structured conversion path from teacher-confirmed formulae to the
  Math Verifier, never direct raw OCR/LaTex inference.
- An isolated Node/TypeScript Word export proof of concept using `docx`, with
  visual compatibility checks.
- MathLive only when interactive equation entry is formally scoped.
- pgvector only after a PostgreSQL migration, retrieval design and privacy
  review; it is not a current prerequisite.
- Cloud deployment only after the local bank/review workflow is stable and
  secrets, storage, roles and costs have an approved design.
