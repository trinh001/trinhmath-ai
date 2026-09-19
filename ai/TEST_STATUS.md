# Test status

## Historical project status

The existing documentation records a latest known state of 49 passing pytest
tests and a successful `self_check.py` result:

```text
OK: candidates=4843, ready_multiple_choice=4
```

Those results predate this documentation preparation and are not re-run claims.
They may rely on local/private data, so do not run broad checks casually.

## Current task checks

This task changes only documentation, an ignore rule and local reference clones.
Before closing it, run:

```powershell
git diff --check
git status --short --branch
```

No external clone test, model download, OCR run, package install, app test or
database check is necessary or authorized for this task.

## Future test expectations

- A pure module change: run the relevant pytest file(s) and `git diff --check`.
- App/data-flow change: add focused tests; run broader self-check only when it
  is safe for the intended local data copy.
- OCR-provider work: use a non-private golden set and assert provider failures
  cannot create approved/released questions.
- Word export: check the generated document in Word/LibreOffice and retain only
  non-private fixtures.
