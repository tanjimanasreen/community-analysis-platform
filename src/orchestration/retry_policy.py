from enum import Enum
import typing

class ErrorCategory(str, Enum):
    TRANSIENT_INFRASTRUCTURE = "TRANSIENT_INFRASTRUCTURE"
    TRANSIENT_GRAPH_STORE = "TRANSIENT_GRAPH_STORE"
    TRANSIENT_PROVIDER_AGGREGATE = "TRANSIENT_PROVIDER_AGGREGATE"
    PROVIDER_CHAIN_EXHAUSTED = "PROVIDER_CHAIN_EXHAUSTED"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"
    MISSING_CREDENTIALS = "MISSING_CREDENTIALS"
    MISSING_REQUIRED_INPUT = "MISSING_REQUIRED_INPUT"
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"
    PROGRAMMING_ERROR = "PROGRAMMING_ERROR"
    UNKNOWN_TERMINAL = "UNKNOWN_TERMINAL"

class PipelineError(Exception):
    def __init__(self, message: str, category: ErrorCategory):
        super().__init__(message)
        self.category = category

class TransientProviderAggregateError(PipelineError):
    def __init__(self, message: str):
        super().__init__(message, ErrorCategory.TRANSIENT_PROVIDER_AGGREGATE)

class ProviderChainExhaustedError(PipelineError):
    """
    Raised when all providers in a fallback chain fail.
    It is only considered retryable if *all* individual failures were transient.
    """
    def __init__(self, message: str, all_transient: bool = False):
        category = (
            ErrorCategory.TRANSIENT_PROVIDER_AGGREGATE
            if all_transient else ErrorCategory.PROVIDER_CHAIN_EXHAUSTED
        )
        super().__init__(message, category)

def classify_error(exc: Exception) -> ErrorCategory:
    """Classify an exception into an explicit retry category."""
    if isinstance(exc, PipelineError):
        return exc.category
    return ErrorCategory.UNKNOWN_TERMINAL

def is_retryable(exc: Exception) -> bool:
    """Determine if an exception is considered transient and retryable."""
    category = classify_error(exc)
    return category in (
        ErrorCategory.TRANSIENT_INFRASTRUCTURE,
        ErrorCategory.TRANSIENT_GRAPH_STORE,
        ErrorCategory.TRANSIENT_PROVIDER_AGGREGATE
    )

def prefect_retry_condition(task: typing.Any, task_run: typing.Any, state: typing.Any) -> bool:
    """Prefect 3 compatibility wrapper for retry condition."""
    try:
        exc = state.result(raise_on_failure=False)
    except Exception as e:
        exc = e
    if isinstance(exc, Exception):
        return is_retryable(exc)
    return False
