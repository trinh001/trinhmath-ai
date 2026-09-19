from ai_provider import FAST, PRO
from model_router import (
    ROUTE_COMPLEX_PRO,
    ROUTE_CRITICAL_REVIEW_PRO,
    ROUTE_FAST_DEFAULT,
    ROUTE_FAST_FAILED_TWICE,
    ROUTE_VISION_FAST,
    RoutingRequest,
    choose_route,
)


def test_routine_work_routes_to_fast_by_default():
    route = choose_route(RoutingRequest(task_class="formatting"))
    assert (route.logical_model, route.reason_code) == (FAST, ROUTE_FAST_DEFAULT)


def test_vision_stays_on_fast_because_pro_has_no_vision_capability():
    route = choose_route(RoutingRequest(task_class="document_processing", is_vision=True))
    assert (route.logical_model, route.reason_code) == (FAST, ROUTE_VISION_FAST)


def test_complex_work_and_two_failed_fast_attempts_escalate_with_reason_codes():
    complex_route = choose_route(RoutingRequest(task_class="complex_refactor"))
    retry_route = choose_route(RoutingRequest(task_class="routine_bugfix", fast_failed_attempts=2))
    assert (complex_route.logical_model, complex_route.reason_code) == (PRO, ROUTE_COMPLEX_PRO)
    assert (retry_route.logical_model, retry_route.reason_code) == (PRO, ROUTE_FAST_FAILED_TWICE)


def test_critical_review_overrides_other_routing_conditions():
    route = choose_route(RoutingRequest(
        task_class="document_processing", is_vision=True, requires_critical_review=True
    ))
    assert (route.logical_model, route.reason_code) == (PRO, ROUTE_CRITICAL_REVIEW_PRO)
