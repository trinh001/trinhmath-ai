import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "dev_fallback.py"
SPEC = importlib.util.spec_from_file_location("dev_fallback", MODULE_PATH)
dev_fallback = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = dev_fallback
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


def test_deepseek_auto_route_uses_flash_for_simple_and_pro_for_core_work(monkeypatch):
    monkeypatch.delenv("TRINHMATH_DEEPSEEK_DEV_MODE", raising=False)

    simple = dev_fallback.choose_deepseek_route("Update README wording and typo fixes.", [])
    core = dev_fallback.choose_deepseek_route(
        "Fix provenance matching and parser data integrity.",
        ["toan-ai-local/candidate_classification.py"],
    )

    assert simple.model == dev_fallback.DEEPSEEK_FLASH_MODEL
    assert simple.reason_code == "SIMPLE_LOW_COST"
    assert core.model == dev_fallback.DEEPSEEK_PRO_MODEL
    assert core.reasoning_effort == "max"
    assert core.reason_code == "COMPLEX_OR_CORE_CHANGE"


def test_deepseek_route_can_be_forced(monkeypatch):
    monkeypatch.setenv("TRINHMATH_DEEPSEEK_DEV_MODE", "pro")
    route = dev_fallback.choose_deepseek_route("docs only", [])
    assert route.model == dev_fallback.DEEPSEEK_PRO_MODEL
    assert route.reason_code == "FORCED_PRO"


def test_safe_default_requires_explicit_commit_and_push(monkeypatch):
    monkeypatch.setattr("sys.argv", ["dev_fallback.py"])
    args = dev_fallback.parse_args()
    assert args.commit is False
    assert args.push is False


def test_safe_default_records_completion_values_without_commit(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    task = repo / "task.md"
    task.write_text("offline task", encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["dev_fallback.py", "--repo", str(repo), "--task-file", str(task)])
    monkeypatch.setattr(dev_fallback, "ensure_work_branch", lambda *_: "dev/test")
    monkeypatch.setattr(
        dev_fallback,
        "run_codex",
        lambda *_: dev_fallback.WorkerOutcome("codex", 0, False, ""),
    )
    monkeypatch.setattr(dev_fallback, "run_validation", lambda *_: True)
    monkeypatch.setattr(dev_fallback, "git", lambda *_args, **_kwargs: "abc123")

    assert dev_fallback.main() == 0
    state = (repo / dev_fallback.STATE_DIR / dev_fallback.STATE_FILE).read_text(encoding="utf-8")
    assert '"status": "COMPLETED"' in state
    assert '"commit_sha": "abc123"' in state
    assert '"push_status": "not-requested"' in state


def test_print_stream_line_survives_legacy_console_encoding(monkeypatch):
    class LegacyConsole:
        encoding = "cp1252"

        def __init__(self):
            self.writes = []
            self.calls = 0

        def write(self, value):
            self.calls += 1
            if self.calls == 1:
                value.encode(self.encoding)
            self.writes.append(value)

        def flush(self):
            pass

    console = LegacyConsole()
    monkeypatch.setattr(dev_fallback.sys, "stdout", console)

    dev_fallback.print_stream_line("M2 → candidate\n")

    assert "\\u2192" in "".join(console.writes)
