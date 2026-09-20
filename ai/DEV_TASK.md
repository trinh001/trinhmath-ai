# TrinhMath AI — Current automated development task

Run this package through `RUN_DEV_TASK_AUTO.bat`.

The launcher runs Codex first. If Codex stops because quota/rate-limit is exhausted,
DeepSeek/Aider continues from the SAME git working tree. Do not restart from scratch.

## TASK — Finish M2 on real local data, then build M3 foundation

### 0. Startup

- Inspect current git branch/status/diff.
- Read only `AGENTS.md` and `ai/HANDOFF.md` first.
- Read other files only when required by the current subtask.
- Do not reread the whole repository.
- Never weaken review/release safety to improve metrics.

### 1. Run the real local M2 cycle

Use the existing deterministic/local pipeline:

`M2_PROVENANCE_ONE_SHOT.bat`

or run its underlying local commands directly if that is more reliable.

Important privacy rule:
- do NOT open/cat/include raw private files such as `question_candidates.json`,
  `source_catalog.json`, `question_provenance.json`, Converter DB contents,
  OCR text, source documents, or student data in model context;
- scripts may process them locally;
- inspect only aggregate/sanitized outputs needed to make engineering decisions;
- no external API calls on private source/OCR/student data.

Record the aggregate result:

- candidate_total
- question_provenance_total
- trusted_question_provenance_total
- MATCHED
- REVIEW_REQUIRED
- INVALID
- unclassified
- duplicate_count
- visual_formula_review_count
- source_match_low_confidence_count
- ambiguity_count
- source_quality_review_count
- math_conflict_count
- top reason codes

### 2. Diagnose the real bottleneck

Do not force MATCHED upward.

If trusted provenance is low or MATCHED remains low:
- inspect code/schema, not private raw content;
- trace deterministic evidence flow:
  source identity -> question number/page -> parser match -> text/math-sensitive match ->
  answer/options -> formula/image association -> validation -> provenance trust.

Fix only genuine pipeline defects or missing deterministic evidence.

Preserve math-sensitive distinctions:
- x+1 != x-1
- -1 != 1
- operators and inequalities must survive normalization
- conflicting answer/formula/operator/image evidence must fail closed.

Do NOT lower thresholds merely to improve counts.

### 3. Complete M2 architecture

M2 is considered architecture-complete when:

- 100% candidates end with MATCHED / REVIEW_REQUIRED / INVALID;
- unclassified = 0;
- file-level metadata cannot by itself produce trusted MATCHED;
- question-level provenance has an auditable schema;
- trusted/untrusted provenance is explicit;
- ambiguous/conflicting evidence stays REVIEW_REQUIRED;
- Review Queue exposes the evidence needed by a teacher;
- teacher actions are auditable/reversible;
- no AI can auto-approve or auto-release;
- source/OCR raw data is unchanged;
- local/private data remains excluded from Git.

Improve the Streamlit Review Queue only if the current implementation has a concrete usability or correctness gap.

### 4. Expand deterministic Math Verifier only when justified by measurements

Use aggregate M2 reason buckets to decide whether deterministic verification would materially reduce review load.

Good candidates include structured:
- arithmetic;
- numeric short answers;
- simple equations;
- algebraic equivalence;
- function evaluation;
- elementary combinatorics/probability where claims are machine-checkable.

Do not add risky free-form geometry heuristics merely to increase pass rate.

Verifier outcomes remain:
- VERIFIED
- CONTRADICTED
- INCONCLUSIVE
- UNSUPPORTED

Only VERIFIED counts as verified evidence.

### 5. Build M3 Trusted Question Bank foundation after M2 gates pass

Do not wait for all 4,843 questions to be teacher-approved.

Create a versioned trusted-question model/service that can promote an already teacher-approved
candidate/review record into a durable trusted bank entry.

Minimum fields should support:

- question_id
- version
- candidate_id
- source_record_id / provenance references
- source_file
- source_page / page range
- question_number
- grade
- chapter/topic/lesson/skill
- cognitive_level
- difficulty
- question_type
- stem
- options
- correct_answer
- solution
- formulas/latex
- image assets/references
- source-match evidence
- math-verification evidence
- teacher-review evidence
- reviewer
- reviewed_at
- created_at
- updated_at
- content_hash
- status

Statuses at minimum:
- DRAFT
- REVIEW_REQUIRED
- APPROVED
- RETIRED

If release is already modeled separately, preserve that separation.

Rules:
- only explicit teacher-approved content can become APPROVED;
- no LLM can call promotion and create APPROVED autonomously;
- editing approved content creates a new version instead of silently overwriting history;
- provenance/review/math evidence remains traceable;
- existence in the trusted bank does not bypass student release validation.

### 6. Promotion service

If not already cleanly represented, implement a controlled promotion service:

candidate/review
-> validate required evidence
-> require teacher approval evidence
-> create immutable/versioned trusted question

Fail closed when:
- question text is missing;
- source provenance is unresolved;
- source/answer/math evidence is contradicted;
- teacher approval evidence is absent/invalid;
- required structure for the question type is incomplete.

Add tests for all promotion gates.

### 7. Tests

Run all relevant tests and fix failures.

Minimum:

TrinhMath:
`python -m pytest -q tests`

Dev fallback:
`python -m pytest -q dev-tools/tests`

Converter:
- `python test_core.py`
- `python test_question_parser.py`
- `python test_matching.py`
- `python test_review_storage.py`
- `python test_question_provenance.py`

Also:
- py_compile changed Python modules
- git diff --check
- verify private runtime data remains ignored/untracked
- verify no secret/private-data path is staged

Add regression coverage for any bug you fix.

### 8. Git workflow

Work on the branch created by the external launcher.

Do not merge main.

Do not commit/push unless the launcher was explicitly started with those permissions.
The safe default is:

code -> tests -> validated diff -> STOP

Do not commit:
- API keys
- DB files
- source documents
- OCR output
- question_candidates.json
- source_catalog.json
- question_provenance.json
- student data
- generated private review artifacts

### 9. Stop conditions

Stop only for a real safety/product boundary:

- destructive DB/schema migration required;
- potential data loss;
- private data would need to be sent to an external model/service;
- paid external API beyond existing authorization is required;
- production deployment is required;
- auto-approval or auto-release would be required;
- local schema/data is unreadable enough that continuing risks corruption.

Ordinary bugs, test failures, imports, schema adapters, UI defects and deterministic matching defects:
fix them and continue.

### 10. Final report

Keep the final report concise:

BRANCH:
PRIMARY WORKER:
FALLBACK WORKER USED:
DEEPSEEK ROUTE IF USED:

M2:
candidate_total:
trusted_provenance:
MATCHED:
REVIEW_REQUIRED:
INVALID:
unclassified:

TOP BOTTLENECKS:
1.
2.
3.

M2 CHANGES:
-

M3 FOUNDATION:
done / partial / blocked
-

TESTS:
-

SAFETY:
auto-approved:
auto-released:
external private-data API calls:
private files staged:

NEXT PACKAGE:
Give exactly one recommended next package.
