from __future__ import annotations

import dataclasses
import json
import math
import re
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from src.tracking.contracts import MAX_SUMMARY_BYTES

_SECRET_KEY_TOKENS = {
    "api_key",
    "apikey",
    "access_token",
    "auth",
    "authorization",
    "client_secret",
    "credential",
    "credentials",
    "password",
    "secret",
    "token",
}
_SECRET_VALUE_PATTERN = re.compile(
    r"(?i)(?:bearer\s+|(?:^|\W)sk-[a-z0-9_-]{8,}|AIza[a-z0-9_-]{12,}|"
    r"nvapi-[a-z0-9_-]{8,}|must-not-persist|secret-value)"
)


class UnsafeTrackingPayload(ValueError):
    """Raised when a tracking payload violates the safe logging contract."""


def _normalized_key(key: object) -> str:
    return str(key).strip().lower().replace("-", "_")


def is_secret_key(key: object) -> bool:
    normalized = _normalized_key(key)
    return normalized in _SECRET_KEY_TOKENS or any(
        normalized.endswith(f"_{token}") for token in _SECRET_KEY_TOKENS
    )


def _safe_scalar(value: Any) -> str | int | float | bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise UnsafeTrackingPayload("Non-finite metric or parameter value")
        return value
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        value = value.as_posix()
    if value is None:
        return ""
    if not isinstance(value, str):
        raise UnsafeTrackingPayload(
            f"Unsupported scalar type: {type(value).__name__}"
        )
    if _SECRET_VALUE_PATTERN.search(value):
        raise UnsafeTrackingPayload("Secret-like value rejected")
    if len(value) > 500:
        raise UnsafeTrackingPayload("Tracking scalar exceeds 500 characters")
    return value


def sanitize_scalar_mapping(
    payload: Mapping[str, Any],
    *,
    allowed_keys: set[str] | frozenset[str],
) -> dict[str, str | int | float | bool]:
    unknown = set(payload) - set(allowed_keys)
    if unknown:
        raise UnsafeTrackingPayload(
            f"Unknown tracking keys: {', '.join(sorted(map(str, unknown)))}"
        )
    clean: dict[str, str | int | float | bool] = {}
    for key, value in payload.items():
        if value is None:
            continue
        if is_secret_key(key):
            raise UnsafeTrackingPayload(f"Secret-like tracking key rejected: {key}")
        clean[str(key)] = _safe_scalar(value)
    return clean


def sanitize_metrics(
    payload: Mapping[str, Any],
    *,
    allowed_keys: set[str] | frozenset[str] | None = None,
) -> dict[str, float]:
    if allowed_keys is not None:
        unknown = set(payload) - set(allowed_keys)
        if unknown:
            raise UnsafeTrackingPayload(
                f"Unknown metric keys: {', '.join(sorted(map(str, unknown)))}"
            )
    clean: dict[str, float] = {}
    for key, value in payload.items():
        if value is None:
            continue
        if is_secret_key(key):
            raise UnsafeTrackingPayload(f"Secret-like metric key rejected: {key}")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise UnsafeTrackingPayload(f"Metric {key!r} must be numeric")
        number = float(value)
        if not math.isfinite(number):
            raise UnsafeTrackingPayload(f"Metric {key!r} must be finite")
        clean[str(key)] = number
    return clean


def sanitize_json_payload(value: Any, *, path: str = "root") -> Any:
    if dataclasses.is_dataclass(value):
        value = dataclasses.asdict(value)
    if isinstance(value, Mapping):
        clean = {}
        for key, item in value.items():
            if is_secret_key(key):
                raise UnsafeTrackingPayload(f"Secret-like key rejected at {path}.{key}")
            clean[str(key)] = sanitize_json_payload(item, path=f"{path}.{key}")
        return clean
    if isinstance(value, (list, tuple, set, frozenset)):
        if len(value) > 1000:
            raise UnsafeTrackingPayload(f"Collection too large at {path}")
        return [
            sanitize_json_payload(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, (bytes, bytearray)):
        raise UnsafeTrackingPayload(f"Binary payload rejected at {path}")
    return _safe_scalar(value)


def encode_bounded_json(payload: Mapping[str, Any]) -> bytes:
    clean = sanitize_json_payload(payload)
    encoded = json.dumps(clean, sort_keys=True, indent=2).encode("utf-8")
    if len(encoded) > MAX_SUMMARY_BYTES:
        raise UnsafeTrackingPayload(
            f"Tracking summary exceeds {MAX_SUMMARY_BYTES} bytes"
        )
    return encoded


def safe_relative_path(path: str | Path, root: str | Path) -> str:
    resolved_path = Path(path).expanduser().resolve()
    resolved_root = Path(root).expanduser().resolve()
    try:
        return resolved_path.relative_to(resolved_root).as_posix()
    except ValueError:
        return resolved_path.name
