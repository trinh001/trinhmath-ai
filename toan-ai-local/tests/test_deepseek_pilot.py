import json
from pathlib import Path

from ai_provider import (
    RESULT_DRY_RUN,
    RESULT_REJECTED,
    RESULT_SUCCESS,
    DeepSeekConfig,
    DeepSeekProvider,
    FakeDeepSeekTransport,
    TransportResponse,
)
from deepseek_pilot import (
    ERROR_KILL_SWITCH,
    ERROR_MAX_ITEMS,
    ERROR_MAX_PAYLOAD,
    ERROR_MAX_TASKS,
    ERROR_MAX_TOKENS,
    ERROR_MIN_TASKS,
    ERROR_MISSING_PILOT_CONFIG,
    ERROR_PROVIDER_DISABLED,
    ERROR_SECRET_LIKE_PAYLOAD,
    PILOT_COMPLETED,
    PILOT_DISABLED,
    PILOT_REJECTED,
    DeepSeekPilotRunner,
    PilotPolicy,
    PilotTask,
)
from model_router import ROUTE_COMPLEX_PRO, ROUTE_FAST_DEFAULT


def sample_tasks():
    path = Path(__file__).parent / "fixtures" / "deepseek_pilot_samples.json"
    return [PilotTask(**item) for item in json.loads(path.read_text(encoding="utf-8"))]


def policy(**overrides):
    values = {"enabled": True, "kill_switch": False}
    values.update(overrides)
    return PilotPolicy(**values)


def provider(transport=None, *, enabled=True):
    return DeepSeekProvider(
        config=DeepSeekConfig(enabled=enabled, allowed_task_classes=("structured_text_review", "code_review", "complex_refactor")),
        environment={"DEEPSEEK_API_KEY": "fixture-key"},
        transport=transport,
    )


def success_response():
    return TransportResponse(200, {
        "choices": [{"message": {"content": '{"ok": true}'}}],
        "usage": {"prompt_tokens": 9, "completion_tokens": 3},
    })


def test_missing_policy_and_disabled_or_killed_pilot_make_zero_calls():
    transport = FakeDeepSeekTransport([success_response()])
    missing = DeepSeekPilotRunner(provider(transport), None).run(sample_tasks())
    disabled = DeepSeekPilotRunner(provider(transport), PilotPolicy()).run(sample_tasks())
    killed = DeepSeekPilotRunner(provider(transport), PilotPolicy(enabled=True, kill_switch=True)).run(sample_tasks())
    assert (missing.status, missing.error_category) == (PILOT_REJECTED, ERROR_MISSING_PILOT_CONFIG)
    assert disabled.status == PILOT_DISABLED
    assert (killed.status, killed.error_category) == (PILOT_DISABLED, ERROR_KILL_SWITCH)
    assert transport.calls == []


def test_provider_feature_off_makes_zero_transport_calls():
    transport = FakeDeepSeekTransport([success_response()])
    result = DeepSeekPilotRunner(provider(transport, enabled=False), policy()).run(sample_tasks())
    assert (result.status, result.error_category) == (PILOT_REJECTED, ERROR_PROVIDER_DISABLED)
    assert transport.calls == []


def test_dry_run_is_auditable_but_never_calls_transport():
    transport = FakeDeepSeekTransport([success_response()])
    result = DeepSeekPilotRunner(provider(transport), policy()).run(sample_tasks(), dry_run=True)
    assert result.status == PILOT_COMPLETED
    assert all(record.result_status == RESULT_DRY_RUN for record in result.records)
    assert all(record.review_outcome == "NOT_RUN" for record in result.records)
    assert transport.calls == []


def test_budget_and_item_limits_reject_the_whole_pilot_before_calls():
    transport = FakeDeepSeekTransport([success_response()])
    over_tasks = DeepSeekPilotRunner(provider(transport), policy(max_tasks=1)).run(sample_tasks())
    too_many_items = PilotTask("safe-1", "code_review", "pilot-v1", "Return JSON.", item_count=6)
    oversized_payload = PilotTask("safe-2", "code_review", "pilot-v1", "x" * 80)
    oversized_tokens = PilotTask("safe-3", "code_review", "pilot-v1", "y" * 80)
    over_items = DeepSeekPilotRunner(provider(transport), policy(min_tasks=1, max_items_per_task=5)).run([too_many_items])
    over_payload = DeepSeekPilotRunner(provider(transport), policy(min_tasks=1, max_payload_bytes=20)).run([oversized_payload])
    over_tokens = DeepSeekPilotRunner(provider(transport), policy(min_tasks=1, max_estimated_input_tokens_per_task=5)).run([oversized_tokens])
    assert (over_tasks.status, over_tasks.error_category) == (PILOT_REJECTED, ERROR_MAX_TASKS)
    assert (over_items.status, over_items.error_category) == (PILOT_REJECTED, ERROR_MAX_ITEMS)
    assert (over_payload.status, over_payload.error_category) == (PILOT_REJECTED, ERROR_MAX_PAYLOAD)
    assert (over_tokens.status, over_tokens.error_category) == (PILOT_REJECTED, ERROR_MAX_TOKENS)
    assert transport.calls == []


def test_pilot_requires_at_least_five_tasks_by_default():
    result = DeepSeekPilotRunner(provider(), policy()).run(sample_tasks()[:4])
    assert (result.status, result.error_category) == (PILOT_REJECTED, ERROR_MIN_TASKS)


def test_secret_like_payload_is_rejected_before_transport():
    transport = FakeDeepSeekTransport([success_response()])
    unsafe = PilotTask("safe-1", "code_review", "pilot-v1", "api_key=not-a-real-key")
    result = DeepSeekPilotRunner(provider(transport), policy(min_tasks=1)).run([unsafe])
    assert (result.status, result.error_category) == (PILOT_REJECTED, ERROR_SECRET_LIKE_PAYLOAD)
    assert transport.calls == []


def test_fake_transport_pilot_records_usage_and_fast_routing_metadata():
    transport = FakeDeepSeekTransport([success_response(), success_response()])
    result = DeepSeekPilotRunner(provider(transport), policy()).run(sample_tasks(), dry_run=False)
    assert result.status == PILOT_COMPLETED
    assert len(result.records) == 5
    assert all(record.result_status == RESULT_SUCCESS for record in result.records)
    assert result.records[0].logical_model == "FAST"
    assert result.records[0].routing_reason == ROUTE_FAST_DEFAULT
    assert result.records[0].usage.input_tokens == 9
    assert result.records[0].usage.output_tokens == 3
    assert result.records[0].review_outcome == "PENDING_TEACHER_REVIEW"
    assert len(transport.calls) == 5


def test_pro_requires_router_reason_and_malformed_response_is_rejected():
    transport = FakeDeepSeekTransport([TransportResponse(200, {"choices": [{"message": {"content": "not-json"}}]})])
    task = PilotTask("complex-1", "complex_refactor", "pilot-v1", "Return JSON.")
    result = DeepSeekPilotRunner(provider(transport), policy(min_tasks=1)).run([task], dry_run=False)
    record = result.records[0]
    assert record.logical_model == "PRO"
    assert record.routing_reason == ROUTE_COMPLEX_PRO
    assert record.result_status == RESULT_REJECTED
    assert record.review_outcome == "REJECTED"
