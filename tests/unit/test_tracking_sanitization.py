import json

import pytest

from src.tracking.sanitization import (
    UnsafeTrackingPayload,
    encode_bounded_json,
    sanitize_json_payload,
    sanitize_metrics,
    sanitize_scalar_mapping,
)


def test_nested_secret_keys_are_rejected():
    payload = {
        "safe": "value",
        "provider": {
            "credentials": {
                "token": "secret-a",
                "password": "secret-b",
            }
        },
    }
    with pytest.raises(UnsafeTrackingPayload, match="Secret-like key"):
        sanitize_json_payload(payload)


def test_secret_like_scalar_value_is_rejected():
    with pytest.raises(UnsafeTrackingPayload, match="Secret-like value"):
        sanitize_scalar_mapping(
            {"run_status": "Bearer secret-value"},
            allowed_keys={"run_status"},
        )


def test_unknown_scalar_key_is_rejected():
    with pytest.raises(UnsafeTrackingPayload, match="Unknown tracking keys"):
        sanitize_scalar_mapping(
            {"allowed": "yes", "authorization": "no"},
            allowed_keys={"allowed"},
        )


def test_json_summary_is_deterministic_and_bounded():
    first = encode_bounded_json({"b": 2, "a": [1, "x"]})
    second = encode_bounded_json({"a": [1, "x"], "b": 2})
    assert first == second
    assert json.loads(first) == {"a": [1, "x"], "b": 2}


def test_json_summary_rejects_large_payload():
    with pytest.raises(UnsafeTrackingPayload, match="exceeds"):
        encode_bounded_json({"values": ["x" * 500] * 200})


def test_unknown_metric_key_is_rejected():
    with pytest.raises(UnsafeTrackingPayload, match="Unknown metric keys"):
        sanitize_metrics(
            {"unexpected_metric": 1},
            allowed_keys={"artifact_count"},
        )
