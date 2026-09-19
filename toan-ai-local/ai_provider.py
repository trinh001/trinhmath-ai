"""Offline-first provider contracts for optional external AI assistance.

This module deliberately has no HTTP client.  It is safe to import from the
local application and tests: DeepSeek is disabled unless explicitly enabled,
and a future network transport must pass the same guards before it is added.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


FAST = "FAST"
PRO = "PRO"
DEEPSEEK_FAST_PROFILE = "deepseek-fast"
DEEPSEEK_PRO_PROFILE = "deepseek-pro"

RESULT_DISABLED = "DISABLED"
RESULT_DRY_RUN = "DRY_RUN"
RESULT_SUCCESS = "SUCCESS"
RESULT_REJECTED = "REJECTED"
RESULT_UNAVAILABLE = "UNAVAILABLE"

ERROR_MISSING_API_KEY = "MISSING_API_KEY"
ERROR_NETWORK_NOT_IMPLEMENTED = "NETWORK_NOT_IMPLEMENTED"
ERROR_MALFORMED_RESPONSE = "MALFORMED_RESPONSE"

_SENSITIVE_METADATA_PARTS = ("api_key", "apikey", "token", "secret", "password", "credential")


def _is_enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def sanitize_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return reviewable metadata without values that look like credentials."""
    clean: dict[str, Any] = {}
    for key, value in (metadata or {}).items():
        if any(part in str(key).lower() for part in _SENSITIVE_METADATA_PARTS):
            clean[str(key)] = "[REDACTED]"
        else:
            clean[str(key)] = value
    return clean


@dataclass(frozen=True)
class ProviderRequest:
    provider: str
    logical_model: str
    actual_model: str
    task_class: str
    reasoning_effort: str
    timeout_seconds: int
    max_retries: int
    max_items: int
    dry_run: bool
    task_id: str
    request_metadata: Mapping[str, Any] = field(default_factory=dict)
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UsageMetadata:
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost: float | None = None
    actual_cost: float | None = None


@dataclass(frozen=True)
class ProviderResult:
    status: str
    provider: str
    logical_model: str
    actual_model: str
    task_id: str
    request_metadata: Mapping[str, Any]
    usage: UsageMetadata = field(default_factory=UsageMetadata)
    output: Mapping[str, Any] | None = None
    error_category: str = ""
    attempts: int = 0


class ProviderAdapter(Protocol):
    def run(self, request: ProviderRequest) -> ProviderResult:
        """Execute a bounded provider request, or fail closed."""


@dataclass(frozen=True)
class DeepSeekConfig:
    enabled: bool = False
    fast_model: str = "deepseek-flash"
    pro_model: str = "deepseek-v4-pro"

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> "DeepSeekConfig":
        environment = environment or os.environ
        return cls(
            enabled=_is_enabled(environment.get("TRINHMATH_DEEPSEEK_ENABLED")),
            fast_model=environment.get("DEEPSEEK_FAST_MODEL", "deepseek-flash"),
            pro_model=environment.get("DEEPSEEK_PRO_MODEL", "deepseek-v4-pro"),
        )

    def actual_model_for(self, logical_model: str) -> str:
        if logical_model == FAST:
            return self.fast_model
        if logical_model == PRO:
            return self.pro_model
        raise ValueError("logical_model must be FAST or PRO")


class DeepSeekProvider:
    """Fail-closed placeholder for the future DeepSeek transport.

    No request is ever sent by this implementation.  API keys are inspected
    only to provide a safe missing-key result once the feature flag is enabled.
    """

    provider_name = "deepseek"

    def __init__(self, config: DeepSeekConfig | None = None, environment: Mapping[str, str] | None = None):
        self.config = config or DeepSeekConfig.from_environment(environment)
        self._environment = environment or os.environ

    def run(self, request: ProviderRequest) -> ProviderResult:
        metadata = sanitize_metadata(request.request_metadata)
        common = dict(
            provider=self.provider_name,
            logical_model=request.logical_model,
            actual_model=request.actual_model,
            task_id=request.task_id,
            request_metadata=metadata,
        )
        if not self.config.enabled:
            return ProviderResult(status=RESULT_DISABLED, **common)
        if request.dry_run:
            return ProviderResult(status=RESULT_DRY_RUN, **common)
        if not self._environment.get("DEEPSEEK_API_KEY"):
            return ProviderResult(
                status=RESULT_UNAVAILABLE,
                error_category=ERROR_MISSING_API_KEY,
                **common,
            )
        return ProviderResult(
            status=RESULT_UNAVAILABLE,
            error_category=ERROR_NETWORK_NOT_IMPLEMENTED,
            **common,
        )


class FakeProvider:
    """Deterministic, in-memory provider for tests; it never uses a network."""

    provider_name = "fake"

    def __init__(self, result: ProviderResult | None = None):
        self.result = result
        self.requests: list[ProviderRequest] = []

    def run(self, request: ProviderRequest) -> ProviderResult:
        self.requests.append(request)
        if self.result is not None:
            return self.result
        return ProviderResult(
            status=RESULT_SUCCESS,
            provider=self.provider_name,
            logical_model=request.logical_model,
            actual_model=request.actual_model,
            task_id=request.task_id,
            request_metadata=sanitize_metadata(request.request_metadata),
            output={"accepted": True},
            attempts=1,
        )


def response_is_usable(result: ProviderResult) -> bool:
    """Accept only an explicit successful mapping; malformed output fails closed."""
    return result.status == RESULT_SUCCESS and isinstance(result.output, Mapping)
