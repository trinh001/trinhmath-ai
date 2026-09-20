"""External development orchestrator: Codex primary, DeepSeek/Aider fallback.

This runs OUTSIDE Codex. If Codex exits because quota/rate-limit is exhausted,
the same local git working tree is handed to Aider using DeepSeek. The fallback
never depends on being able to type inside Codex.

The script is development tooling only. It is not imported by TrinhMath runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


DEEPSEEK_FLASH_MODEL = "deepseek/deepseek-flash"
DEEPSEEK_PRO_MODEL = "deepseek/deepseek-v4-pro"
DEEPSEEK_API_BASE = "https://api.deepseek.com"
STATE_DIR = ".dev-fallback"
STATE_FILE = "state.json"
LOCK_FILE = "running.lock"

QUOTA_PATTERNS = (
    r"\bquota\b",
    r"rate[ _-]?limit",
    r"usage[ _-]?limit",
    r"limit (?:has been )?reached",
    r"you(?:'ve| have) (?:hit|reached).{0,40}limit",
    r"too many requests",
    r"\b429\b",
    r"try again (?:later|after)",
    r"weekly limit",
    r"5[- ]hour limit",
)

PRIVATE_PATH_PATTERNS = (
    re.compile(r"(^|/)question_candidates(?:_triaged)?\.json$", re.I),
    re.compile(r"(^|/)question_bank\.json$", re.I),
    re.compile(r"(^|/)question_drafts\.json$", re.I),
    re.compile(r"(^|/)approved_questions\.json$", re.I),
    re.compile(r"(^|/)quiz_variants\.json$", re.I),
    re.compile(r"(^|/)image_analysis\.json$", re.I),
    re.compile(r"(^|/)source_catalog\.json$", re.I),
    re.compile(r"(^|/)question_provenance\.json$", re.I),
    re.compile(r"(^|/)results\.db$", re.I),
    re.compile(r"\.sqlite(?:\d+)?$", re.I),
    re.compile(r"\.db$", re.I),
    re.compile(r"(^|/)sources?/", re.I),
    re.compile(r"(^|/)data/", re.I),
    re.compile(r"(^|/)backups?/", re.I),
    re.compile(r"(^|/)\.env(?:\.|$)", re.I),
    re.compile(r"\.(?:key|pem|secret|bin)$", re.I),
)


@dataclass(frozen=True)
class DeepSeekDevRoute:
    model: str
    reasoning_effort: str
    reason_code: str


@dataclass
class WorkerOutcome:
    worker: str
    returncode: int
    quota_detected: bool
    output_tail: str


@dataclass
class DevState:
    task_sha256: str
    branch: str
    started_at: str
    status: str
    active_worker: str
    codex_returncode: int | None = None
    fallback_reason: str = ""
    fallback_model: str = ""
    fallback_reasoning_effort: str = ""
    fallback_route_reason: str = ""
    aider_returncode: int | None = None
    tests_passed: bool | None = None
    commit_sha: str = ""
    push_status: str = ""


def now_text() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def task_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def quota_exhausted(output: str) -> bool:
    lowered = output.lower()
    return any(re.search(pattern, lowered, flags=re.I | re.S) for pattern in QUOTA_PATTERNS)


def choose_deepseek_route(task: str, paths: Iterable[str] = ()) -> DeepSeekDevRoute:
    """Choose a cost/quality DeepSeek fallback route deterministically."""
    forced = os.environ.get("TRINHMATH_DEEPSEEK_DEV_MODE", "auto").strip().lower()
    if forced in {"flash", "fast"}:
        return DeepSeekDevRoute(DEEPSEEK_FLASH_MODEL, "high", "FORCED_FLASH")
    if forced in {"pro", "expert"}:
        return DeepSeekDevRoute(DEEPSEEK_PRO_MODEL, "max", "FORCED_PRO")

    text = task.lower()
    path_blob = " ".join(str(path).replace("\\", "/").lower() for path in paths)

    complex_markers = (
        "architecture", "kiến trúc", "security", "bảo mật", "migration",
        "schema", "database", "sqlite", "concurrency", "race condition",
        "cross-module", "multi-module", "math verifier", "parser", "matching",
        "provenance", "data integrity", "release gate", "approval gate",
        "root cause", "refactor lõi", "core refactor",
    )
    core_paths = (
        "candidate_classification.py", "math_verifier.py", "source_analyzer.py",
        "matching.py", "storage.py", "variant_validation.py", "ai_provider.py",
        "model_router.py",
    )
    if any(marker in text for marker in complex_markers) or any(name in path_blob for name in core_paths):
        return DeepSeekDevRoute(DEEPSEEK_PRO_MODEL, "max", "COMPLEX_OR_CORE_CHANGE")

    simple_markers = (
        "documentation", "docs", "readme", "typo", "format", "rename",
        "fixture", "test only", "tests only", "ui text", "copywriting",
    )
    if any(marker in text for marker in simple_markers):
        return DeepSeekDevRoute(DEEPSEEK_FLASH_MODEL, "high", "SIMPLE_LOW_COST")

    return DeepSeekDevRoute(DEEPSEEK_FLASH_MODEL, "high", "DAILY_AGENT_DEFAULT")


def is_private_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return any(pattern.search(normalized) for pattern in PRIVATE_PATH_PATTERNS)


def split_command(value: str) -> list[str]:
    if os.name == "nt":
        # shlex(posix=False) preserves Windows path quoting more predictably.
        return shlex.split(value, posix=False)
    return shlex.split(value)


def run_streaming(
    command: list[str],
    *,
    cwd: Path,
    stdin_text: str | None = None,
    env: dict[str, str] | None = None,
    tail_limit: int = 120_000,
) -> tuple[int, str]:
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        stdin=subprocess.PIPE if stdin_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        bufsize=1,
    )
    if stdin_text is not None and process.stdin is not None:
        process.stdin.write(stdin_text)
        process.stdin.close()

    chunks: list[str] = []
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="", flush=True)
        chunks.append(line)
        total = sum(len(item) for item in chunks)
        while total > tail_limit and len(chunks) > 1:
            total -= len(chunks.pop(0))
    return process.wait(), "".join(chunks)[-tail_limit:]


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if check and result.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{result.stdout}")
    return result.stdout.strip()


def ensure_repo(repo: Path) -> None:
    if not (repo / ".git").exists():
        raise RuntimeError(f"Not a git repository: {repo}")
    git(repo, "rev-parse", "--show-toplevel")


def current_branch(repo: Path) -> str:
    return git(repo, "branch", "--show-current") or "detached"


def ensure_work_branch(repo: Path, prefix: str) -> str:
    branch = current_branch(repo)
    if branch != "main" and branch != "master" and branch != "detached":
        return branch
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    new_branch = f"{prefix}/{stamp}"
    git(repo, "switch", "-c", new_branch)
    return new_branch


def write_state(repo: Path, state: DevState) -> None:
    directory = repo / STATE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / STATE_FILE
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(target)


def acquire_lock(repo: Path) -> Path:
    directory = repo / STATE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / LOCK_FILE
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise RuntimeError(
            f"Another dev fallback run appears active. Delete {lock} only if no run is active."
        ) from error
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(f"pid={os.getpid()}\nstarted={now_text()}\n")
    return lock


def resolve_aider(repo: Path) -> str | None:
    configured = os.environ.get("TRINHMATH_AIDER_CMD", "").strip()
    if configured:
        return configured
    candidates = [
        repo / ".dev-fallback-venv" / "Scripts" / "aider.exe",
        repo / ".dev-fallback-venv" / "bin" / "aider",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return shutil.which("aider")


def codex_command(task: str) -> list[str]:
    executable = os.environ.get("TRINHMATH_CODEX_CMD", "codex").strip() or "codex"
    command = split_command(executable)
    command += ["exec", "--sandbox", "workspace-write", "--ephemeral"]
    extra = os.environ.get("TRINHMATH_CODEX_EXTRA_ARGS", "").strip()
    if extra:
        command += split_command(extra)
    command.append(task)
    return command


def continuation_prompt(task: str, reason: str) -> str:
    return f"""Continue the CURRENT git working tree after the primary Codex worker stopped.

Fallback reason: {reason}

Rules:
- Do NOT restart the task from scratch.
- First inspect git status, git diff, current branch and existing partial edits.
- Read AGENTS.md and ai/HANDOFF.md only as needed for safety/project context.
- Preserve existing work that is correct.
- Complete the original task below.
- Run relevant tests and fix failures.
- Never merge main.
- Never commit or send private source/OCR/database/student data.
- Do not weaken TrinhMath review/release safety gates.
- Do not print or store API keys.

ORIGINAL TASK
=============
{task}
"""


def run_codex(repo: Path, task: str) -> WorkerOutcome:
    command = codex_command(task)
    try:
        code, output = run_streaming(command, cwd=repo)
    except FileNotFoundError:
        return WorkerOutcome("codex", 127, False, "Codex CLI command not found.")
    return WorkerOutcome("codex", code, quota_exhausted(output), output)


def run_aider(repo: Path, task: str, fallback_reason: str, route: DeepSeekDevRoute) -> WorkerOutcome:
    aider = resolve_aider(repo)
    if not aider:
        return WorkerOutcome("deepseek-aider", 127, False, "Aider is not installed.")
    if not os.environ.get("DEEPSEEK_API_KEY"):
        return WorkerOutcome("deepseek-aider", 126, False, "DEEPSEEK_API_KEY is not available.")

    runtime_dir = repo / STATE_DIR / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = runtime_dir / "deepseek_continuation.md"
    prompt_path.write_text(continuation_prompt(task, fallback_reason), encoding="utf-8")

    model_override = os.environ.get("TRINHMATH_DEEPSEEK_DEV_MODEL", "").strip()
    model = model_override or route.model
    environment = dict(os.environ)
    environment["OPENAI_API_BASE"] = DEEPSEEK_API_BASE
    environment["OPENAI_API_KEY"] = environment["DEEPSEEK_API_KEY"]
    command = split_command(aider) + [
        "--model", model,
        "--reasoning-effort", route.reasoning_effort,
        "--message-file", str(prompt_path),
        "--yes-always",
        "--no-auto-commits",
        "--no-dirty-commits",
        "--no-check-update",
        "--no-show-release-notes",
        "--aiderignore", str(repo / ".aiderignore"),
    ]
    code, output = run_streaming(command, cwd=repo, env=environment)
    return WorkerOutcome("deepseek-aider", code, False, output)


def changed_paths(repo: Path) -> list[str]:
    values = set()
    for args in (
        ("diff", "--name-only"),
        ("diff", "--name-only", "--cached"),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        for line in git(repo, *args, check=False).splitlines():
            if line.strip():
                values.add(line.strip().replace("\\", "/"))
    return sorted(values)


def staged_private_paths(repo: Path) -> list[str]:
    paths = git(repo, "diff", "--cached", "--name-only", check=False).splitlines()
    return sorted(path for path in paths if is_private_path(path))


def python_for(directory: Path) -> str:
    candidates = [
        directory / ".venv" / "Scripts" / "python.exe",
        directory / ".venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def run_validation(repo: Path, paths: Iterable[str]) -> bool:
    changed = list(paths)
    checks: list[tuple[list[str], Path]] = [(["git", "diff", "--check"], repo)]

    if any(path.startswith("toan-ai-local/") for path in changed):
        app_dir = repo / "toan-ai-local"
        checks.append(([python_for(app_dir), "-m", "pytest", "-q", "tests"], app_dir))

    if any(path.startswith("math-document-converter/") for path in changed):
        converter = repo / "math-document-converter"
        py = python_for(converter)
        for test in (
            "test_core.py",
            "test_question_parser.py",
            "test_matching.py",
            "test_review_storage.py",
            "test_question_provenance.py",
        ):
            if (converter / test).exists():
                checks.append(([py, test], converter))

    custom = os.environ.get("TRINHMATH_DEV_TEST_COMMAND", "").strip()
    if custom:
        checks.append((split_command(custom), repo))

    for command, cwd in checks:
        print(f"\n[validate] {' '.join(command)}")
        code, _ = run_streaming(command, cwd=cwd)
        if code:
            return False
    return True


def commit_and_push(repo: Path, *, push: bool) -> tuple[str, str]:
    paths = changed_paths(repo)
    if not paths:
        return git(repo, "rev-parse", "HEAD"), "nothing-to-push"

    git(repo, "add", "-A")
    private = staged_private_paths(repo)
    if private:
        git(repo, "reset")
        raise RuntimeError(
            "Refusing to commit private/local data: " + ", ".join(private)
        )

    message = os.environ.get(
        "TRINHMATH_DEV_COMMIT_MESSAGE",
        "dev-fallback: complete automated coding task",
    )
    git(repo, "commit", "-m", message)
    sha = git(repo, "rev-parse", "HEAD")
    if not push:
        return sha, "disabled"

    branch = current_branch(repo)
    result = subprocess.run(
        ["git", "push", "-u", "origin", branch],
        cwd=str(repo),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(result.stdout)
    return sha, "success" if result.returncode == 0 else f"failed:{result.returncode}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Codex; automatically fall back to DeepSeek/Aider on quota exhaustion."
    )
    parser.add_argument("--task-file", type=Path, default=Path("ai/DEV_TASK.md"))
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--branch-prefix", default="dev/auto")
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Explicitly allow a local git commit after validation. Default: leave changes uncommitted.",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Explicitly allow push after a successful local commit. Requires --commit.",
    )
    parser.add_argument(
        "--fallback-on-codex-unavailable",
        action="store_true",
        default=True,
        help="Use DeepSeek if Codex CLI itself is unavailable.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    ensure_repo(repo)

    task_file = args.task_file
    if not task_file.is_absolute():
        task_file = repo / task_file
    task = task_file.read_text(encoding="utf-8").strip()
    if not task:
        raise RuntimeError(f"Task file is empty: {task_file}")

    lock = acquire_lock(repo)
    try:
        branch = ensure_work_branch(repo, args.branch_prefix)
        state = DevState(
            task_sha256=task_digest(task),
            branch=branch,
            started_at=now_text(),
            status="RUNNING",
            active_worker="codex",
        )
        write_state(repo, state)

        print(f"[dev-fallback] branch={branch}")
        print("[dev-fallback] primary worker=Codex")
        codex = run_codex(repo, task)
        state.codex_returncode = codex.returncode

        needs_fallback = codex.quota_detected or codex.returncode == 127
        if codex.returncode == 0 and not codex.quota_detected:
            print("[dev-fallback] Codex completed without quota failure.")
        elif needs_fallback:
            reason = "CODEX_QUOTA_EXHAUSTED" if codex.quota_detected else "CODEX_UNAVAILABLE"
            route = choose_deepseek_route(task, changed_paths(repo))
            state.fallback_reason = reason
            state.fallback_model = route.model
            state.fallback_reasoning_effort = route.reasoning_effort
            state.fallback_route_reason = route.reason_code
            state.active_worker = "deepseek-aider"
            write_state(repo, state)
            print(
                f"[dev-fallback] {reason}; switching outside Codex to DeepSeek/Aider "
                f"model={route.model} effort={route.reasoning_effort} route={route.reason_code}."
            )
            fallback = run_aider(repo, task, reason, route)
            state.aider_returncode = fallback.returncode
            if fallback.returncode:
                state.status = "FAILED"
                write_state(repo, state)
                print(f"[dev-fallback] DeepSeek/Aider failed: {fallback.output_tail[-2000:]}")
                return fallback.returncode or 1
        else:
            state.status = "FAILED"
            write_state(repo, state)
            print("[dev-fallback] Codex failed for a non-quota reason; fail closed, no automatic provider switch.")
            return codex.returncode or 1

        paths = changed_paths(repo)
        state.active_worker = "validation"
        write_state(repo, state)
        tests_ok = run_validation(repo, paths)
        state.tests_passed = tests_ok
        if not tests_ok:
            state.status = "TEST_FAILED"
            write_state(repo, state)
            return 2

        if args.push and not args.commit:
            raise RuntimeError("--push requires explicit --commit")
        if args.commit:
            sha, push_status = commit_and_push(repo, push=args.push)
            state.commit_sha = sha
            state.push_status = push_status
        else:
            state.commit_sha = git(repo, "rev-parse", "HEAD")
            state.push_status = "not-requested"
            print("[dev-fallback] validation passed; safe default leaves changes uncommitted/unpushed.")
        state.status = "COMPLETED"
        state.active_worker = ""
        write_state(repo, state)
        print(f"[dev-fallback] completed commit={sha} push={push_status}")
        return 0
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
