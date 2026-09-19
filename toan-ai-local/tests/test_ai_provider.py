from ai_provider import (
    DEEPSEEK_FAST_PROFILE,
    DEEPSEEK_PRO_PROFILE,
    ERROR_MALFORMED_RESPONSE,
    ERROR_MISSING_API_KEY,
    ERROR_REQUEST_NOT_ALLOWED,
    ERROR_SENSITIVE_PAYLOAD,
    ERROR_TRANSPORT_NOT_CONFIGURED,
    FAST,
    PRO,
    RESULT_DISABLED,
    RESULT_DRY_RUN,
    RESULT_REJECTED,
    RESULT_SUCCESS,
    RESULT_UNAVAILABLE,
    DeepSeekConfig,
    DeepSeekProvider,
    FakeDeepSeekTransport,
    FakeProvider,
    ProviderRequest,
    ProviderResult,
    TransportResponse,
    UrllibDeepSeekTransport,
    response_is_usable,
    sanitize_metadata,
)


def request(*, dry_run=False, **overrides):
    values = {
        "provider": "deepseek",
        "logical_model": FAST,
        "actual_model": "deepseek-flash",
        "task_class": "code_review",
        "reasoning_effort": "high",
        "timeout_seconds": 30,
        "max_retries": 2,
        "max_items": 5,
        "dry_run": dry_run,
        "task_id": "safe-test-1",
        "request_metadata": {"prompt_version": "v1", "api_key": "must-not-leak"},
        "payload": {"messages": [{"role": "user", "content": "Return JSON only."}]},
    }
    values.update(overrides)
    return ProviderRequest(**values)


def enabled_config(**overrides):
    values = {"enabled": True, "allowed_task_classes": ("code_review",)}
    values.update(overrides)
    return DeepSeekConfig(**values)


def success_response(content='{"accepted": true}'):
    return TransportResponse(200, {
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 5},
    })


class FakeHttpResponse:
    def __init__(self, status_code=200, body=b'{"choices": []}'):
        self.status_code = status_code
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def getcode(self):
        return self.status_code

    def read(self):
        return self.body


def test_defaults_are_off_and_use_stable_logical_model_mappings():
    config = DeepSeekConfig.from_environment({})
    assert not config.enabled
    assert not config.allowed_task_classes
    assert config.actual_model_for(FAST) == "deepseek-flash"
    assert config.actual_model_for(PRO) == "deepseek-v4-pro"
    assert (DEEPSEEK_FAST_PROFILE, DEEPSEEK_PRO_PROFILE) == ("deepseek-fast", "deepseek-pro")


def test_model_mappings_are_configurable_without_scattering_model_strings():
    config = DeepSeekConfig.from_environment({
        "TRINHMATH_DEEPSEEK_ENABLED": "true",
        "DEEPSEEK_FAST_MODEL": "custom-fast",
        "DEEPSEEK_PRO_MODEL": "custom-pro",
    })
    assert config.enabled
    assert config.actual_model_for(FAST) == "custom-fast"
    assert config.actual_model_for(PRO) == "custom-pro"


def test_off_and_dry_run_never_reach_injected_transport():
    transport = FakeDeepSeekTransport([success_response()])
    disabled = DeepSeekProvider(environment={}, transport=transport).run(request())
    dry_run = DeepSeekProvider(
        config=enabled_config(), environment={"DEEPSEEK_API_KEY": "fixture-key"}, transport=transport
    ).run(request(dry_run=True))
    assert disabled.status == RESULT_DISABLED
    assert dry_run.status == RESULT_DRY_RUN
    assert dry_run.request_metadata["api_key"] == "[REDACTED]"
    assert transport.calls == []


def test_missing_key_and_no_transport_fail_closed_before_a_call():
    missing_key = DeepSeekProvider(config=enabled_config(), environment={}).run(request())
    no_transport = DeepSeekProvider(
        config=enabled_config(), environment={"DEEPSEEK_API_KEY": "fixture-key"}
    ).run(request())
    assert (missing_key.status, missing_key.error_category) == (RESULT_UNAVAILABLE, ERROR_MISSING_API_KEY)
    assert (no_transport.status, no_transport.error_category) == (RESULT_UNAVAILABLE, ERROR_TRANSPORT_NOT_CONFIGURED)


def test_transport_receives_bounded_request_but_result_never_exposes_key():
    transport = FakeDeepSeekTransport([success_response()])
    result = DeepSeekProvider(
        config=enabled_config(), environment={"DEEPSEEK_API_KEY": "fixture-key"}, transport=transport
    ).run(request())
    assert result.status == RESULT_SUCCESS
    assert result.output == {"accepted": True}
    assert result.usage.input_tokens == 12
    assert result.usage.output_tokens == 5
    assert result.request_metadata["api_key"] == "[REDACTED]"
    assert len(transport.calls) == 1
    assert transport.calls[0]["body"]["model"] == "deepseek-flash"
    assert "fixture-key" not in str(result)


def test_urllib_transport_is_injectable_and_tested_without_network():
    calls = []

    def opener(http_request, timeout):
        calls.append((http_request, timeout))
        return FakeHttpResponse(body=b'{"choices": [{"message": {"content": "{}"}}]}')

    response = UrllibDeepSeekTransport(opener=opener).send(
        endpoint="https://example.invalid/chat/completions",
        headers={"Authorization": "Bearer fixture-key", "Content-Type": "application/json"},
        body={"model": "deepseek-flash", "messages": []},
        timeout_seconds=7,
    )
    assert response.status_code == 200
    assert response.body == {"choices": [{"message": {"content": "{}"}}]}
    assert calls[0][1] == 7
    assert calls[0][0].full_url == "https://example.invalid/chat/completions"


def test_unapproved_or_sensitive_requests_do_not_reach_transport():
    transport = FakeDeepSeekTransport([success_response()])
    provider = DeepSeekProvider(
        config=enabled_config(), environment={"DEEPSEEK_API_KEY": "fixture-key"}, transport=transport
    )
    unapproved = provider.run(request(task_class="bounded_batch_transform"))
    sensitive = provider.run(request(payload={"api_token": "do-not-send"}))
    over_limit = provider.run(request(max_items=21))
    unknown_model = provider.run(request(logical_model="UNKNOWN", actual_model="unknown"))
    assert (unapproved.status, unapproved.error_category) == (RESULT_REJECTED, ERROR_REQUEST_NOT_ALLOWED)
    assert (sensitive.status, sensitive.error_category) == (RESULT_REJECTED, ERROR_SENSITIVE_PAYLOAD)
    assert (over_limit.status, over_limit.error_category) == (RESULT_REJECTED, ERROR_REQUEST_NOT_ALLOWED)
    assert (unknown_model.status, unknown_model.error_category) == (RESULT_REJECTED, ERROR_REQUEST_NOT_ALLOWED)
    assert transport.calls == []


def test_retry_is_bounded_and_records_attempt_count_with_fake_transport():
    transport = FakeDeepSeekTransport([TransportResponse(429, {}), success_response()])
    result = DeepSeekProvider(
        config=enabled_config(), environment={"DEEPSEEK_API_KEY": "fixture-key"}, transport=transport
    ).run(request(max_retries=1))
    assert result.status == RESULT_SUCCESS
    assert result.attempts == 2
    assert len(transport.calls) == 2


def test_malformed_transport_response_is_rejected_not_guessed():
    transport = FakeDeepSeekTransport([success_response("not-json")])
    result = DeepSeekProvider(
        config=enabled_config(), environment={"DEEPSEEK_API_KEY": "fixture-key"}, transport=transport
    ).run(request())
    assert (result.status, result.error_category) == (RESULT_REJECTED, ERROR_MALFORMED_RESPONSE)
    assert not response_is_usable(result)


def test_fake_provider_is_offline_and_malformed_output_is_not_usable():
    fake = FakeProvider()
    result = fake.run(request())
    malformed = ProviderResult(
        status=RESULT_SUCCESS,
        provider="fake",
        logical_model=FAST,
        actual_model="fake",
        task_id="safe-test-2",
        request_metadata={},
        output=None,
        error_category=ERROR_MALFORMED_RESPONSE,
    )
    assert len(fake.requests) == 1
    assert response_is_usable(result)
    assert not response_is_usable(malformed)


def test_metadata_redacts_secret_like_fields():
    assert sanitize_metadata({"Token": "no", "safe": "yes", "password_hint": "no", "nested": {"secret": "no"}}) == {
        "Token": "[REDACTED]",
        "safe": "yes",
        "password_hint": "[REDACTED]",
        "nested": {"secret": "[REDACTED]"},
    }
