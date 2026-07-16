from src.orchestration.retry_policy import (
    PipelineError,
    ErrorCategory,
    is_retryable,
    TransientProviderAggregateError,
    ProviderChainExhaustedError,
)


def test_transient_is_retryable():
    exc = PipelineError("timeout", ErrorCategory.TRANSIENT_GRAPH_STORE)
    assert is_retryable(exc)


def test_transient_aggregate_is_retryable():
    exc = TransientProviderAggregateError("all models failed transiently")
    assert is_retryable(exc)


def test_provider_chain_exhausted_all_transient_is_retryable():
    attempts = [
        PipelineError("timeout", ErrorCategory.TRANSIENT_GRAPH_STORE),
        PipelineError("rate limit", ErrorCategory.TRANSIENT_INFRASTRUCTURE),
    ]
    exc = ProviderChainExhaustedError("chain failed", attempt_exceptions=attempts)
    assert is_retryable(exc)


def test_provider_chain_exhausted_mixed_is_terminal():
    attempts = [
        PipelineError("timeout", ErrorCategory.TRANSIENT_INFRASTRUCTURE),
        PipelineError("invalid auth", ErrorCategory.MISSING_CREDENTIALS),
    ]
    exc = ProviderChainExhaustedError("chain failed", attempt_exceptions=attempts)
    assert not is_retryable(exc)


def test_provider_chain_exhausted_unsupported_model_is_terminal():
    attempts = [ValueError("unsupported model")]
    exc = ProviderChainExhaustedError("chain failed", attempt_exceptions=attempts)
    assert not is_retryable(exc)


def test_provider_chain_exhausted_empty_is_terminal():
    exc = ProviderChainExhaustedError("chain failed", attempt_exceptions=[])
    assert not is_retryable(exc)


def test_provider_chain_exhausted_none_is_terminal():
    exc = ProviderChainExhaustedError("chain failed")
    assert not is_retryable(exc)


def test_invalid_config_is_not_retryable():
    exc = PipelineError("bad config", ErrorCategory.INVALID_CONFIGURATION)
    assert not is_retryable(exc)


def test_schema_violation_is_not_retryable():
    exc = PipelineError("schema err", ErrorCategory.SCHEMA_VIOLATION)
    assert not is_retryable(exc)


def test_programming_error_is_not_retryable():
    exc = PipelineError("logic err", ErrorCategory.PROGRAMMING_ERROR)
    assert not is_retryable(exc)


def test_generic_exception_is_not_retryable():
    exc = ValueError("unknown")
    assert not is_retryable(exc)
