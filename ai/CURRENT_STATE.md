# Current state

_Snapshot prepared 2026-09-19 from the existing project report and progress
record; do not treat counts as live database queries._

- 387 Word/PDF documents indexed.
- 4,843 source candidates extracted.
- 2,192 local image/formula reads cached.
- 7 approved source questions and 5 safely released student variants.
- 36 drafts await review; 21 local-parser drafts require teacher comparison.
- Formula/image ambiguity, uncertain question boundaries and incomplete
  solutions remain blocked from students.

The previously recorded automated state was 49 pytest tests passing and
`self_check.py` reporting `candidates=4843, ready_multiple_choice=4`. These
are historical results, not evidence that tests pass after new changes.

## Workspace note (2026-09-19)

- The source snapshot was checked and synchronized through a separate review branch. Obtain the live branch, commit and working-tree state from Git when needed; this record must not be used as a branch selector.
- Existing user changes were present before the preparation work and were not rewritten.
- Shallow reference clones are present in `external/` and intentionally
  ignored by the parent Git repo.
- No product architecture, app code, data record, API key, dependency lockfile
  or release state was changed.
