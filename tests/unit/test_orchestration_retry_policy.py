from src.orchestration.retry_policy import PipelineError, ErrorCategory, is_retryable

def test_transient_is_retryable():
    exc = PipelineError("timeout", ErrorCategory.TRANSIENT_GRAPH_STORE)
    assert is_retryable(exc)

def test_transient_aggregate_is_retryable():
    exc = PipelineError("all models failed", ErrorCategory.TRANSIENT_PROVIDER_AGGREGATE)
    assert is_retryable(exc)

def test_invalid_config_is_not_retryable():
    exc = PipelineError("bad config", ErrorCategory.INVALID_CONFIGURATION)
    assert not is_retryable(exc)

def test_schema_violation_is_not_retryable():
    exc = PipelineError("schema err", ErrorCategory.SCHEMA_VIOLATION)
    assert not is_retryable(exc)

def test_generic_exception_is_not_retryable():
    exc = ValueError("unknown")
    assert not is_retryable(exc)
