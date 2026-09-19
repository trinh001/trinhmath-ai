"""Regression checks for constants used by Streamlit-only review paths."""

import app
from local_review_workflow import LOCAL_DRAFT_PROVENANCE


def test_review_page_has_the_local_draft_provenance_constant():
    """The batch-blocking UI must not fail only after a teacher opens it."""
    assert app.LOCAL_DRAFT_PROVENANCE == LOCAL_DRAFT_PROVENANCE
    assert callable(app.build_local_source_batches)
    assert callable(app.flag_local_source_batch_after_teacher_review)
