"""Deterministic FAST/PRO routing policy for optional provider work."""

from __future__ import annotations

from dataclasses import dataclass

from ai_provider import FAST, PRO


ROUTE_FAST_DEFAULT = "ROUTE_FAST_DEFAULT"
ROUTE_VISION_FAST = "ROUTE_VISION_FAST"
ROUTE_COMPLEX_PRO = "ROUTE_COMPLEX_PRO"
ROUTE_FAST_FAILED_TWICE = "ROUTE_FAST_FAILED_TWICE"
ROUTE_CRITICAL_REVIEW_PRO = "ROUTE_CRITICAL_REVIEW_PRO"

_COMPLEX_TASKS = {"architecture", "complex_refactor", "difficult_debugging", "cross_module_invariant", "security_review", "data_integrity_review"}


@dataclass(frozen=True)
class RoutingRequest:
    task_class: str
    is_vision: bool = False
    fast_failed_attempts: int = 0
    requires_critical_review: bool = False


@dataclass(frozen=True)
class ModelRoute:
    logical_model: str
    reasoning_effort: str
    reason_code: str


def choose_route(request: RoutingRequest) -> ModelRoute:
    """Route by explicit, reviewable conditions—not intuition or confidence."""
    if request.requires_critical_review:
        return ModelRoute(PRO, "max", ROUTE_CRITICAL_REVIEW_PRO)
    if request.fast_failed_attempts >= 2:
        return ModelRoute(PRO, "max", ROUTE_FAST_FAILED_TWICE)
    if request.task_class in _COMPLEX_TASKS:
        return ModelRoute(PRO, "high", ROUTE_COMPLEX_PRO)
    # Current provider capability: PRO is not selected for vision work.
    if request.is_vision:
        return ModelRoute(FAST, "high", ROUTE_VISION_FAST)
    return ModelRoute(FAST, "high", ROUTE_FAST_DEFAULT)
