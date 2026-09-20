"""Local-only launcher for the first bounded DeepSeek pilot.

Default mode is dry-run and never opens a network connection.
Use --live explicitly to send exactly five synthetic FAST tasks.
No project source/OCR/student data is read by this launcher.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import replace
from pathlib import Path
from typing import Any

from ai_provider import (
    FAST,
    RESULT_DRY_RUN,
    RESULT_SUCCESS,
    DeepSeekConfig,
    DeepSeekProvider,
    UrllibDeepSeekTransport,
)
from deepseek_pilot import DeepSeekPilotRunner, PilotPolicy, PilotTask, PILOT_COMPLETED
from model_router import RoutingRequest, choose_route


FIXTURE_PATH = Path(__file__).parent / "tests" / "fixtures" / "deepseek_pilot_samples.json"
SAFE_TASK_CLASSES = ("structured_text_review", "code_review")
EXPECTED_TASK_COUNT = 5


class CountingTransport:
    """Counts HTTP sends without logging headers, payloads, or credentials."""

    def __init__(self) -> None:
        self._inner = UrllibDeepSeekTransport()
        self.calls = 0

    def send(
        self,
        *,
        endpoint: str,
        headers: dict[str, str] | Any,
        body: dict[str, Any] | Any,
        timeout_seconds: int,
    ):
        self.calls += 1
        return self._inner.send(
            endpoint=endpoint,
            headers=headers,
            body=body,
            timeout_seconds=timeout_seconds,
        )


def load_synthetic_tasks() -> list[PilotTask]:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    tasks = [PilotTask(**item) for item in raw]
    if len(tasks) != EXPECTED_TASK_COUNT:
        raise RuntimeError(f"Expected exactly {EXPECTED_TASK_COUNT} synthetic tasks.")
    return tasks


def ensure_fast_only(tasks: list[PilotTask]) -> None:
    for task in tasks:
        route = choose_route(
            RoutingRequest(
                task_class=task.task_class,
                is_vision=task.is_vision,
                fast_failed_attempts=task.fast_failed_attempts,
                requires_critical_review=task.requires_critical_review,
            )
        )
        if route.logical_model != FAST:
            raise RuntimeError(f"Task {task.task_id} is not FAST-only; refusing pilot.")
        if task.task_class not in SAFE_TASK_CLASSES:
            raise RuntimeError(f"Task {task.task_id} uses a non-pilot task class.")


def _live_environment_ready(environment: dict[str, str] | os._Environ[str]) -> tuple[bool, str]:
    config = DeepSeekConfig.from_environment(environment)
    if not config.enabled:
        return False, "TRINHMATH_DEEPSEEK_ENABLED is not enabled."
    if not environment.get("DEEPSEEK_API_KEY"):
        return False, "DEEPSEEK_API_KEY is not available in this PowerShell process."
    return True, ""


def run_pilot(*, live: bool, environment: dict[str, str] | os._Environ[str] | None = None) -> int:
    environment = environment or os.environ
    tasks = load_synthetic_tasks()
    ensure_fast_only(tasks)

    if live:
        ready, reason = _live_environment_ready(environment)
        if not ready:
            print("PREFLIGHT: BLOCKED")
            print(reason)
            print("API CALLS: 0")
            return 2

    base_config = DeepSeekConfig.from_environment(environment)
    config = replace(
        base_config,
        enabled=True if not live else base_config.enabled,
        allowed_task_classes=SAFE_TASK_CLASSES,
    )

    transport = CountingTransport() if live else None
    provider = DeepSeekProvider(
        config=config,
        environment=environment,
        transport=transport,
    )
    policy = PilotPolicy(
        enabled=True,
        kill_switch=False,
        min_tasks=EXPECTED_TASK_COUNT,
        max_tasks=EXPECTED_TASK_COUNT,
    )
    result = DeepSeekPilotRunner(provider, policy).run(tasks, dry_run=not live)

    success_count = sum(record.result_status == RESULT_SUCCESS for record in result.records)
    dry_run_count = sum(record.result_status == RESULT_DRY_RUN for record in result.records)
    fail_count = len(result.records) - success_count - dry_run_count
    input_tokens = sum(record.usage.input_tokens or 0 for record in result.records)
    output_tokens = sum(record.usage.output_tokens or 0 for record in result.records)
    schema_pass = sum(record.result_status == RESULT_SUCCESS for record in result.records)

    print(f"MODE: {'LIVE' if live else 'DRY_RUN'}")
    print(f"STATUS: {result.status}")
    print(f"TASKS RUN: {len(result.records)} / {EXPECTED_TASK_COUNT}")
    print(f"SUCCESS: {success_count}")
    print(f"DRY RUN: {dry_run_count}")
    print(f"FAIL: {fail_count}")
    print(f"SCHEMA PASS: {schema_pass if live else 'N/A'}")
    print(f"INPUT TOKENS: {input_tokens}")
    print(f"OUTPUT TOKENS: {output_tokens}")
    print(f"API CALLS: {transport.calls if transport is not None else 0}")
    print("COST: not computed locally; use token counts with current DeepSeek pricing/dashboard.")
    for record in result.records:
        print(
            f"- {record.task_id}: {record.logical_model} | "
            f"{record.routing_reason} | {record.result_status}"
            + (f" | {record.error_category}" if record.error_category else "")
        )

    if result.status != PILOT_COMPLETED:
        return 1
    if live and (len(result.records) != EXPECTED_TASK_COUNT or success_count != EXPECTED_TASK_COUNT):
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the bounded local DeepSeek pilot.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Actually call DeepSeek. Without this flag, the launcher is dry-run only.",
    )
    args = parser.parse_args()
    return run_pilot(live=args.live)


if __name__ == "__main__":
    raise SystemExit(main())
