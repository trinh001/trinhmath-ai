from ai_provider import (
    DEEPSEEK_FAST_PROFILE,
    DEEPSEEK_PRO_PROFILE,
    ERROR_MALFORMED_RESPONSE,
    ERROR_MISSING_API_KEY,
    ERROR_NETWORK_NOT_IMPLEMENTED,
    FAST,
    PRO,
    RESULT_DISABLED,
    RESULT_DRY_RUN,
    RESULT_SUCCESS,
    RESULT_UNAVAILABLE,
    DeepSeekConfig,
    DeepSeekProvider,
    FakeProvider,
    ProviderRequest,
    ProviderResult,
    response_is_usable,
    sanitize_metadata,
)


def request(*, dry_run=False):
    return ProviderRequest(
        provider="deepseek",
        logical_model=FAST,
        actual_model="deepseek-flash",
        task_class="code_review",
        reasoning_effort="high",
        timeout_seconds=30,
        max_retries=2,
        max_items=5,
        dry_run=dry_run,
        task_id="safe-test-1",
        request_metadata={"prompt_version": "v1", "api_key": "must-not-leak"},
    )


def test_defaults_are_off_and_use_stable_logical_model_mappings():
    config = DeepSeekConfig.from_environment({})
    assert not config.enabled
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


def test_off_and_dry_run_fail_before_any_network_transport_exists():
    disabled = DeepSeekProvider(environment={}).run(request())
    dry_run = DeepSeekProvider(
        config=DeepSeekConfig(enabled=True), environment={"DEEPSEEK_API_KEY": "present"}
    ).run(request(dry_run=True))
    assert disabled.status == RESULT_DISABLED
    assert dry_run.status == RESULT_DRY_RUN
    assert dry_run.request_metadata["api_key"] == "[REDACTED]"


def test_missing_key_and_unimplemented_network_fail_closed():
    missing_key = DeepSeekProvider(config=DeepSeekConfig(enabled=True), environment={}).run(request())
    with_key = DeepSeekProvider(
        config=DeepSeekConfig(enabled=True), environment={"DEEPSEEK_API_KEY": "local-only"}
    ).run(request())
    assert (missing_key.status, missing_key.error_category) == (RESULT_UNAVAILABLE, ERROR_MISSING_API_KEY)
    assert (with_key.status, with_key.error_category) == (RESULT_UNAVAILABLE, ERROR_NETWORK_NOT_IMPLEMENTED)


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
    assert sanitize_metadata({"Token": "no", "safe": "yes", "password_hint": "no"}) == {
        "Token": "[REDACTED]",
        "safe": "yes",
        "password_hint": "[REDACTED]",
    }
