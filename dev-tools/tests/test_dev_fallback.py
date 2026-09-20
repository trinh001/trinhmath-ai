import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "dev_fallback.py"
SPEC = importlib.util.spec_from_file_location("dev_fallback", MODULE_PATH)
dev_fallback = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(dev_fallback)


def test_quota_detection_covers_common_codex_limit_messages():
    assert dev_fallback.quota_exhausted("You've hit your weekly usage limit.")
    assert dev_fallback.quota_exhausted("HTTP 429 rate_limit_exceeded")
    assert dev_fallback.quota_exhausted("Quota exceeded. Try again later.")
    assert not dev_fallback.quota_exhausted("pytest failed: assertion error")


def test_private_path_guard_blocks_local_question_and_database_data():
    blocked = [
        "toan-ai-local/question_candidates.json",
        "toan-ai-local/question_provenance.json",
        "toan-ai-local/results.db",
        "math-document-converter/data/converter.db",
        "toan-ai-local/sources/private.docx",
        ".env",
    ]
    assert all(dev_fallback.is_private_path(path) for path in blocked)
    assert not dev_fallback.is_private_path("toan-ai-local/candidate_classification.py")
    assert not dev_fallback.is_private_path("ai/HANDOFF.md")


def test_continuation_prompt_explicitly_resumes_existing_git_work():
    prompt = dev_fallback.continuation_prompt("Implement feature X.", "CODEX_QUOTA_EXHAUSTED")
    assert "Do NOT restart the task from scratch" in prompt
    assert "inspect git status" in prompt
    assert "CODEX_QUOTA_EXHAUSTED" in prompt
    assert "Implement feature X." in prompt


def test_codex_command_uses_noninteractive_workspace_write(monkeypatch):
    monkeypatch.setenv("TRINHMATH_CODEX_CMD", "codex")
    monkeypatch.delenv("TRINHMATH_CODEX_EXTRA_ARGS", raising=False)
    command = dev_fallback.codex_command("Do work")
    assert command[:2] == ["codex", "exec"]
    assert "--sandbox" in command
    assert "workspace-write" in command
    assert "--ephemeral" in command
    assert command[-1] == "Do work"
