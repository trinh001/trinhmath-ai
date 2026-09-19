"""Offline-first preparation runner for a small, sanitized DeepSeek pilot.

This module does not read project data and is not imported by ``app.py``.  It
can call only an injected provider after every policy check succeeds; tests use
the in-memory fake transport from ``ai_provider``.
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from ai_provider import (
    FAST,
    PRO,
    RESULT_DISABLED,
    RESULT_DRY_RUN,
    RESULT_SUCCESS,
    DeepSeekProvider,
    ProviderRequest,
    UsageMetadata,
    sanitize_metadata,
)
from model_router import (
    ROUTE_COMPLEX_PRO,
    ROUTE_CRITICAL_REVIEW_PRO,
    ROUTE_FAST_DEFAULT,
    ROUTE_FAST_FAILED_TWICE,
    ROUTE_VISION_FAST,
    RoutingRequest,
    choose_route,
)


PILOT_COMPLETED = "PILOT_COMPLETED"
PILOT_DISABLED = "PILOT_DISABLED"
PILOT_REJECTED = "PILOT_REJECTED"

ERROR_MISSING_PILOT_CONFIG = "MISSING_PILOT_CONFIG"
ERROR_PILOT_DISABLED = "PILOT_DISABLED"
ERROR_KILL_SWITCH = "KILL_SWITCH"
ERROR_PROVIDER_DISABLED = "PROVIDER_DISABLED"
ERROR_MIN_TASKS = "MIN_TASKS_NOT_MET"
ERROR_MAX_TASKS = "MAX_TASKS_EXCEEDED"
ERROR_MAX_ITEMS = "MAX_ITEMS_EXCEEDED"
ERROR_MAX_PAYLOAD = "MAX_PAYLOAD_EXCEEDED"
ERROR_MAX_TOKENS = "MAX_TOKEN_ESTIMATE_EXCEEDED"
ERROR_UNSANITIZED_TASK = "UNSANITIZED_TASK"
ERROR_SECRET_LIKE_PAYLOAD = "SECRET_LIKE_PAYLOAD"
ERROR_INVALID_ROUTE = "INVALID_ROUTE"

_VALID_ROUTE_REASONS = {
    ROUTE_FAST_DEFAULT,
    ROUTE_VISION_FAST,
    ROUTE_COMPLEX_PRO,
    ROUTE_FAST_FAILED_TWICE,
    ROUTE_CRITICAL_REVIEW_PRO,
}
_SECRET_LIKE_TEXT = re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|password|secret)\s*[:=]|\bsk-[a-z0-9_-]{8,}")


@dataclass(frozen=True)
class PilotTask:
    """One teacher-approved, sanitized task—never a source/OCR record."""

    task_id: str
    task_class: str
    prompt_version: str
    sanitized_text: str
    item_count: int = 1
    is_vision: bool = False
    fast_failed_attempts: int = 0
    requires_critical_review: bool = False
    sanitized: bool = True


@dataclass(frozen=True)
class PilotPolicy:
    """Explicit bounded policy.  Defaults are deliberately fail-closed."""

    enabled: bool = False
    kill_switch: bool = True
    min_tasks: int = 5
    max_tasks: int = 20
    max_items_per_task: int = 5
    max_retries: int = 2
    timeout_seconds: int = 60
    max_payload_bytes: int = 16_384
    max_estimated_input_tokens_per_task: int = 4_096
    max_estimated_input_tokens_total: int = 12_000


@dataclass(frozen=True)
class PilotRecord:
    started_at: str
    task_id: str
    task_class: str
    logical_model: str
    actual_model: str
    prompt_version: str
    routing_reason: str
    max_items: int
    max_retries: int
    timeout_seconds: int
    dry_run: bool
    estimated_input_tokens: int
    usage: UsageMetadata
    result_status: str
    error_category: str
    latency_ms: int
    review_outcome: str
    audit_metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PilotRunResult:
    status: str
    error_category: str
    records: tuple[PilotRecord, ...] = ()
    estimated_input_tokens: int = 0


class DeepSeekPilotRunner:
    """Validates every task before a provider can be invoked."""

    def __init__(self, provider: DeepSeekProvider, policy: PilotPolicy | None = None):
        self._provider = provider
        self._policy = policy

    def run(self, tasks: Iterable[PilotTask], *, dry_run: bool = True) -> PilotRunResult:
        task_list = tuple(tasks)
        policy_error = self._policy_error(task_list)
        if policy_error:
            status = PILOT_DISABLED if policy_error in {ERROR_PILOT_DISABLED, ERROR_KILL_SWITCH} else PILOT_REJECTED
            return PilotRunResult(status=status, error_category=policy_error)

        prepared: list[tuple[PilotTask, Any, int]] = []
        total_estimate = 0
        for task in task_list:
            error, route, estimate = self._prepare_task(task)
            if error:
                return PilotRunResult(status=PILOT_REJECTED, error_category=error)
            total_estimate += estimate
            if total_estimate > self._policy.max_estimated_input_tokens_total:
                return PilotRunResult(status=PILOT_REJECTED, error_category=ERROR_MAX_TOKENS)
            prepared.append((task, route, estimate))

        records = tuple(self._run_task(task, route, estimate, dry_run) for task, route, estimate in prepared)
        return PilotRunResult(
            status=PILOT_COMPLETED,
            error_category="",
            records=records,
            estimated_input_tokens=total_estimate,
        )

    def _policy_error(self, tasks: tuple[PilotTask, ...]) -> str:
        if self._policy is None:
            return ERROR_MISSING_PILOT_CONFIG
        if not self._policy.enabled:
            return ERROR_PILOT_DISABLED
        if self._policy.kill_switch:
            return ERROR_KILL_SWITCH
        if not self._provider.config.enabled:
            return ERROR_PROVIDER_DISABLED
        if len(tasks) < self._policy.min_tasks:
            return ERROR_MIN_TASKS
        if len(tasks) > self._policy.max_tasks:
            return ERROR_MAX_TASKS
        return ""

    def _prepare_task(self, task: PilotTask) -> tuple[str, Any, int]:
        if not task.sanitized or not task.task_id or not task.prompt_version:
            return ERROR_UNSANITIZED_TASK, None, 0
        if not 1 <= task.item_count <= self._policy.max_items_per_task:
            return ERROR_MAX_ITEMS, None, 0
        encoded = task.sanitized_text.encode("utf-8")
        if not task.sanitized_text or len(encoded) > self._policy.max_payload_bytes:
            return ERROR_MAX_PAYLOAD, None, 0
        if _SECRET_LIKE_TEXT.search(task.sanitized_text):
            return ERROR_SECRET_LIKE_PAYLOAD, None, 0
        estimate = _estimate_input_tokens(task.sanitized_text)
        if estimate > self._policy.max_estimated_input_tokens_per_task:
            return ERROR_MAX_TOKENS, None, 0
        route = choose_route(RoutingRequest(
            task_class=task.task_class,
            is_vision=task.is_vision,
            fast_failed_attempts=task.fast_failed_attempts,
            requires_critical_review=task.requires_critical_review,
        ))
        if route.reason_code not in _VALID_ROUTE_REASONS or route.logical_model not in {FAST, PRO}:
            return ERROR_INVALID_ROUTE, None, 0
        return "", route, estimate

    def _run_task(self, task: PilotTask, route: Any, estimate: int, dry_run: bool) -> PilotRecord:
        actual_model = self._provider.config.actual_model_for(route.logical_model)
        request = ProviderRequest(
            provider="deepseek",
            logical_model=route.logical_model,
            actual_model=actual_model,
            task_class=task.task_class,
            reasoning_effort=route.reasoning_effort,
            timeout_seconds=self._policy.timeout_seconds,
            max_retries=self._policy.max_retries,
            max_items=task.item_count,
            dry_run=dry_run,
            task_id=task.task_id,
            request_metadata={
                "prompt_version": task.prompt_version,
                "pilot": True,
                "sanitized": True,
                "routing_reason": route.reason_code,
            },
            payload={"messages": [{"role": "user", "content": task.sanitized_text}]},
        )
        started_at = datetime.now(timezone.utc).isoformat()
        started = time.monotonic()
        result = self._provider.run(request)
        latency_ms = max(0, round((time.monotonic() - started) * 1000))
        return PilotRecord(
            started_at=started_at,
            task_id=task.task_id,
            task_class=task.task_class,
            logical_model=route.logical_model,
            actual_model=actual_model,
            prompt_version=task.prompt_version,
            routing_reason=route.reason_code,
            max_items=task.item_count,
            max_retries=self._policy.max_retries,
            timeout_seconds=self._policy.timeout_seconds,
            dry_run=dry_run,
            estimated_input_tokens=estimate,
            usage=result.usage,
            result_status=result.status,
            error_category=result.error_category,
            latency_ms=latency_ms,
            review_outcome=_review_outcome(result.status, dry_run),
            audit_metadata=sanitize_metadata(result.request_metadata),
        )


def _estimate_input_tokens(text: str) -> int:
    """Conservative deterministic estimate for a pre-flight budget gate."""
    return max(1, math.ceil(len(text.encode("utf-8")) / 4))


def _review_outcome(result_status: str, dry_run: bool) -> str:
    if dry_run or result_status == RESULT_DRY_RUN:
        return "NOT_RUN"
    if result_status == RESULT_SUCCESS:
        return "PENDING_TEACHER_REVIEW"
    if result_status == RESULT_DISABLED:
        return "NOT_RUN"
    return "REJECTED"
