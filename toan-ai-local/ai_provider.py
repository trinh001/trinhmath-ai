"""Fail-closed contracts for optional, bounded external AI assistance.

The module deliberately ships no HTTP client.  A future transport must be
injected, so imports, unit tests and the Streamlit app remain offline by
default.  DeepSeek is disabled unless an explicit configuration enables it.
"""

from __future__ import annotations

import json
import os
from urllib import request as urllib_request
from urllib import error as urllib_error
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence


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
ERROR_TRANSPORT_NOT_CONFIGURED = "TRANSPORT_NOT_CONFIGURED"
ERROR_MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
ERROR_REQUEST_NOT_ALLOWED = "REQUEST_NOT_ALLOWED"
ERROR_SENSITIVE_PAYLOAD = "SENSITIVE_PAYLOAD"
ERROR_TRANSPORT_FAILURE = "TRANSPORT_FAILURE"

_SENSITIVE_METADATA_PARTS = ("api_key", "apikey", "token", "secret", "password", "credential")


def _is_enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _has_sensitive_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            any(part in str(key).lower() for part in _SENSITIVE_METADATA_PARTS)
            or _has_sensitive_key(item)
            for key, item in value.items()
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_has_sensitive_key(item) for item in value)
    return False


def sanitize_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return reviewable metadata without values that look like credentials."""
    clean: dict[str, Any] = {}
    for key, value in (metadata or {}).items():
        if any(part in str(key).lower() for part in _SENSITIVE_METADATA_PARTS):
            clean[str(key)] = "[REDACTED]"
        else:
            clean[str(key)] = _sanitize_value(value)
    return clean


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return sanitize_metadata(value)
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_value(item) for item in value)
    return value


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
    max_output_tokens: int
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


@dataclass(frozen=True)
class TransportResponse:
    """Normalized response returned by an injected transport implementation."""

    status_code: int
    body: Mapping[str, Any] | None


class ProviderAdapter(Protocol):
    def run(self, request: ProviderRequest) -> ProviderResult:
        """Execute a bounded provider request, or fail closed."""


class DeepSeekTransport(Protocol):
    """Network boundary; production HTTP is intentionally not implemented."""

    def send(
        self,
        *,
        endpoint: str,
        headers: Mapping[str, str],
        body: Mapping[str, Any],
        timeout_seconds: int,
    ) -> TransportResponse:
        """Return a normalized response without logging credentials."""


@dataclass(frozen=True)
class DeepSeekConfig:
    enabled: bool = False
    fast_model: str = "deepseek-flash"
    pro_model: str = "deepseek-v4-pro"
    endpoint: str = "https://api.deepseek.com/chat/completions"
    allowed_task_classes: tuple[str, ...] = ()
    max_timeout_seconds: int = 60
    max_retries: int = 2
    max_items: int = 20
    max_output_tokens: int = 2_048
    max_payload_bytes: int = 131_072

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> "DeepSeekConfig":
        environment = os.environ if environment is None else environment
        return cls(
            enabled=_is_enabled(environment.get("TRINHMATH_DEEPSEEK_ENABLED")),
            fast_model=environment.get("DEEPSEEK_FAST_MODEL", "deepseek-flash"),
            pro_model=environment.get("DEEPSEEK_PRO_MODEL", "deepseek-v4-pro"),
            endpoint=environment.get("DEEPSEEK_ENDPOINT", "https://api.deepseek.com/chat/completions"),
        )

    def actual_model_for(self, logical_model: str) -> str:
        if logical_model == FAST:
            return self.fast_model
        if logical_model == PRO:
            return self.pro_model
        raise ValueError("logical_model must be FAST or PRO")


class FakeDeepSeekTransport:
    """Deterministic test transport. It records calls and never opens a socket."""

    def __init__(self, responses: Sequence[TransportResponse] | None = None):
        self.responses = list(responses or [])
        self.calls: list[dict[str, Any]] = []

    def send(self, *, endpoint: str, headers: Mapping[str, str], body: Mapping[str, Any], timeout_seconds: int) -> TransportResponse:
        self.calls.append({
            "endpoint": endpoint,
            "headers": dict(headers),
            "body": dict(body),
            "timeout_seconds": timeout_seconds,
        })
        if self.responses:
            return self.responses.pop(0)
        return TransportResponse(200, {"choices": [{"message": {"content": "{}"}}]})


class UrllibDeepSeekTransport:
    """Explicit stdlib HTTP transport; never constructed by default.

    The provider guards feature state, allow-list, limits and credentials before
    this transport is called. Tests inject an opener, so this class is never
    allowed to contact the Internet during local checks or CI.
    """

    def __init__(self, opener: Any = urllib_request.urlopen):
        self._opener = opener

    def send(self, *, endpoint: str, headers: Mapping[str, str], body: Mapping[str, Any], timeout_seconds: int) -> TransportResponse:
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib_request.Request(endpoint, data=encoded, headers=dict(headers), method="POST")
        try:
            with self._opener(request, timeout=timeout_seconds) as response:
                status_code = response.getcode()
                raw_body = response.read()
        except urllib_error.HTTPError as error:
            status_code = error.code
            raw_body = error.read()
        try:
            response_body = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            response_body = None
        return TransportResponse(status_code, response_body if isinstance(response_body, Mapping) else None)


class DeepSeekProvider:
    """OpenAI-compatible request adapter guarded before its injected transport.

    It has no default transport. Therefore an application cannot accidentally
    make a paid request merely by setting an environment variable.
    """

    provider_name = "deepseek"

    def __init__(
        self,
        config: DeepSeekConfig | None = None,
        environment: Mapping[str, str] | None = None,
        transport: DeepSeekTransport | None = None,
    ):
        self.config = config or DeepSeekConfig.from_environment(environment)
        self._environment = os.environ if environment is None else environment
        self._transport = transport

    def run(self, request: ProviderRequest) -> ProviderResult:
        common = self._common_result_fields(request)
        if not self.config.enabled:
            return ProviderResult(status=RESULT_DISABLED, **common)
        if request.dry_run:
            return ProviderResult(status=RESULT_DRY_RUN, **common)
        error = self._request_guard_error(request)
        if error:
            return ProviderResult(status=RESULT_REJECTED, error_category=error, **common)
        api_key = self._environment.get("DEEPSEEK_API_KEY")
        if not api_key:
            return ProviderResult(status=RESULT_UNAVAILABLE, error_category=ERROR_MISSING_API_KEY, **common)
        if self._transport is None:
            return ProviderResult(status=RESULT_UNAVAILABLE, error_category=ERROR_TRANSPORT_NOT_CONFIGURED, **common)
        return self._send_bounded(request, api_key, common)

    def _common_result_fields(self, request: ProviderRequest) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "logical_model": request.logical_model,
            "actual_model": request.actual_model,
            "task_id": request.task_id,
            "request_metadata": sanitize_metadata(request.request_metadata),
        }

    def _request_guard_error(self, request: ProviderRequest) -> str:
        if request.provider != self.provider_name:
            return ERROR_REQUEST_NOT_ALLOWED
        try:
            expected_model = self.config.actual_model_for(request.logical_model)
        except ValueError:
            return ERROR_REQUEST_NOT_ALLOWED
        if request.actual_model != expected_model:
            return ERROR_REQUEST_NOT_ALLOWED
        if request.task_class not in self.config.allowed_task_classes:
            return ERROR_REQUEST_NOT_ALLOWED
        if not 1 <= request.timeout_seconds <= self.config.max_timeout_seconds:
            return ERROR_REQUEST_NOT_ALLOWED
        if not 0 <= request.max_retries <= self.config.max_retries:
            return ERROR_REQUEST_NOT_ALLOWED
        if not 1 <= request.max_items <= self.config.max_items:
            return ERROR_REQUEST_NOT_ALLOWED
        if not 1 <= request.max_output_tokens <= self.config.max_output_tokens:
            return ERROR_REQUEST_NOT_ALLOWED
        if _has_sensitive_key(request.payload):
            return ERROR_SENSITIVE_PAYLOAD
        try:
            if len(json.dumps(request.payload, ensure_ascii=False).encode("utf-8")) > self.config.max_payload_bytes:
                return ERROR_REQUEST_NOT_ALLOWED
        except (TypeError, ValueError):
            return ERROR_REQUEST_NOT_ALLOWED
        return ""

    def _send_bounded(self, request: ProviderRequest, api_key: str, common: Mapping[str, Any]) -> ProviderResult:
        body = {
            "model": request.actual_model,
            "messages": request.payload.get("messages"),
            "reasoning_effort": request.reasoning_effort,
            "max_tokens": request.max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        if not _valid_messages(body["messages"]):
            return ProviderResult(status=RESULT_REJECTED, error_category=ERROR_REQUEST_NOT_ALLOWED, **common)
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        for attempt in range(1, request.max_retries + 2):
            try:
                response = self._transport.send(
                    endpoint=self.config.endpoint,
                    headers=headers,
                    body=body,
                    timeout_seconds=request.timeout_seconds,
                )
            except Exception:
                return ProviderResult(
                    status=RESULT_UNAVAILABLE,
                    error_category=ERROR_TRANSPORT_FAILURE,
                    attempts=attempt,
                    **common,
                )
            if response.status_code in {408, 429} or 500 <= response.status_code <= 599:
                if attempt <= request.max_retries:
                    continue
                return ProviderResult(
                    status=RESULT_UNAVAILABLE,
                    error_category=ERROR_TRANSPORT_FAILURE,
                    attempts=attempt,
                    **common,
                )
            if not 200 <= response.status_code <= 299:
                return ProviderResult(
                    status=RESULT_UNAVAILABLE,
                    error_category=ERROR_TRANSPORT_FAILURE,
                    attempts=attempt,
                    **common,
                )
            output, usage = _parse_response(response.body)
            if output is None:
                return ProviderResult(
                    status=RESULT_REJECTED,
                    error_category=ERROR_MALFORMED_RESPONSE,
                    attempts=attempt,
                    **common,
                )
            return ProviderResult(
                status=RESULT_SUCCESS,
                output=output,
                usage=usage,
                attempts=attempt,
                **common,
            )
        raise AssertionError("bounded retry loop must return")


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


def _valid_messages(messages: Any) -> bool:
    return isinstance(messages, list) and bool(messages) and all(
        isinstance(message, Mapping)
        and isinstance(message.get("role"), str)
        and isinstance(message.get("content"), str)
        for message in messages
    )


def _parse_response(body: Mapping[str, Any] | None) -> tuple[Mapping[str, Any] | None, UsageMetadata]:
    if not isinstance(body, Mapping):
        return None, UsageMetadata()
    try:
        choice = body["choices"][0]
        finish_reason = choice.get("finish_reason")
        if finish_reason not in {None, "stop"}:
            return None, UsageMetadata()
        content = choice["message"]["content"]
        output = json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None, UsageMetadata()
    if not isinstance(output, Mapping):
        return None, UsageMetadata()
    usage = body.get("usage") if isinstance(body.get("usage"), Mapping) else {}
    return dict(output), UsageMetadata(
        input_tokens=_safe_int(usage.get("prompt_tokens")),
        output_tokens=_safe_int(usage.get("completion_tokens")),
    )


def _safe_int(value: Any) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None


def response_is_usable(result: ProviderResult) -> bool:
    """Accept only an explicit successful mapping; malformed output fails closed."""
    return result.status == RESULT_SUCCESS and isinstance(result.output, Mapping)
