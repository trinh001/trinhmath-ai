# M2 Integration — local read-only measurement

Measurement date: 20/09/2026. The run used local candidate records and source
catalog metadata only. It did not open raw source/OCR files, student data or
database records, and did not use an API key or external service. No raw
candidate/source content was emitted or committed.

## Schema coverage

- Candidate records processed: 4,843
- Source metadata records: 387
- Candidate records with a source reference: 4,843
- Candidate source references present in the source catalog: 4,843

## Classification aggregate

- `MATCHED`: 0
- `REVIEW_REQUIRED`: 4,843
- `INVALID`: 0
- Unclassified: 0

The source catalog currently contains file-level metadata but not question text,
answer or formula evidence. M2 therefore correctly fails closed: it does not
declare a source match from filename metadata alone.

## Top review signals

- `SOURCE_MATCH_LOW_CONFIDENCE`: 4,843
- `VISUAL_OR_FORMULA_REVIEW_REQUIRED`: 4,063
- `IMAGE_DEPENDENCY_UNCONFIRMED`: 4,063
- `SOURCE_QUALITY_REVIEW_REQUIRED`: 1,648
- `DUPLICATE_CANDIDATE`: 1,043
- `BOUNDARY_REVIEW_REQUIRED`: 57

This is an aggregate-only derived report. It is not an approval, release, or
data migration record.
