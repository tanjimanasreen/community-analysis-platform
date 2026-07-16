from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Union

from src.config.settings import get_database_settings

ENV_VAR_RE = re.compile(r"\$\{([^}]+)\}")
MONTH_NAME_TO_NUMBER = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

# Resolved at import time so callers can rely on a stable reference.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PROVIDERS_CONFIG = _PROJECT_ROOT / "configs" / "providers.yml"
_DEFAULT_ALGORITHMS_CONFIG = _PROJECT_ROOT / "configs" / "algorithms.yml"


def interpolate_env(value: Any) -> Any:
    if isinstance(value, str):
        return ENV_VAR_RE.sub(lambda match: os.environ.get(match.group(1), ""), value)
    if isinstance(value, dict):
        return {key: interpolate_env(val) for key, val in value.items()}
    if isinstance(value, list):
        return [interpolate_env(item) for item in value]
    return value


def _coerce_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.lower() in {"null", "none"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the small config subset used by this repo when PyYAML is absent."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if ":" not in stripped:
            continue

        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if raw_value == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _coerce_scalar(raw_value)

    return root


PathLike = Union[str, Path]


def load_config(config_path: PathLike) -> dict[str, Any]:
    path = Path(config_path)
    text = path.read_text(encoding="utf-8")
    try:
        import yaml

        config = yaml.safe_load(text) or {}
    except ModuleNotFoundError:
        config = _parse_simple_yaml(text)

    if not isinstance(config, dict):
        raise ValueError(f"Config must be a mapping: {config_path}")

    # Handle includes — resolved relative to the config file's directory
    includes = config.pop("include", [])
    if isinstance(includes, str):
        includes = [includes]

    merged_config: dict[str, Any] = {}
    for inc in includes:
        inc_path = path.parent / inc
        if inc_path.exists():
            inc_config = load_config(inc_path)
            _deep_merge(merged_config, inc_config)

    # Current config wins over included defaults
    _deep_merge(merged_config, config)

    return interpolate_env(merged_config)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> None:
    """Recursively merge override into base in-place. Override wins on conflicts."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def load_providers_config(base_dir: Path | None = None) -> dict[str, Any]:
    """Load configs/providers.yml as a standalone dict.

    Used to inject provider settings into run configs that don't include
    providers.yml themselves (e.g. ad-hoc invocations without a dataset config).
    """
    providers_path = (base_dir or _PROJECT_ROOT) / "configs" / "providers.yml"
    if not providers_path.exists():
        return {}
    return load_config(providers_path)


def validate_run_config(config: dict[str, Any]) -> None:
    required = (
        "data_type",
        "content_type",
        "month",
        "year",
        "input_path",
        "output_base_path",
        "creator_relation",
        "spreader_relation",
        "creator_node_column",
        "spreader_node_column",
        "text_node_column",
        "date_column",
    )
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"Missing required config keys: {', '.join(missing)}")

    thresholds = config.get("graph_thresholds", {})
    for key in ("min_total_post", "min_shared_post", "min_members"):
        if key in thresholds and int(thresholds[key]) < 0:
            raise ValueError(f"graph_thresholds.{key} must be non-negative")

    # Validate tracking shape and repository-relative local storage paths without
    # importing MLflow or creating any local tracking state.
    from src.tracking.factory import parse_tracking_settings

    parse_tracking_settings(config, _PROJECT_ROOT)


def validate_provider_config(config: dict[str, Any]) -> None:
    """Validate theme_provider settings in a merged config dict."""
    known_prefixes = {"gemini", "nvidia", "llm7", "openai", "mock", "keyword_baseline"}
    theme_provider = config.get("theme_provider", {})
    primary = theme_provider.get("primary", "mock")
    prefix = primary.split(":", 1)[0] if ":" in primary else primary
    if prefix not in known_prefixes:
        raise ValueError(
            f"Unknown theme_provider.primary prefix: {prefix!r}. "
            f"Known prefixes: {sorted(known_prefixes)}"
        )
    fallback_chain = theme_provider.get("fallback_chain", [])
    for entry in fallback_chain:
        pfx = entry.split(":", 1)[0] if ":" in entry else entry
        if pfx not in known_prefixes:
            raise ValueError(
                f"Unknown provider in fallback_chain: {entry!r}. "
                f"Known prefixes: {sorted(known_prefixes)}"
            )


def get_database_config(config: dict[str, Any]) -> dict[str, Any]:
    # Strictly load from the environment via Pydantic — config dict is ignored.
    db_settings = get_database_settings()
    return {
        "engine": db_settings.engine,
        "uri": db_settings.uri,
        "user": db_settings.user,
        "password": db_settings.password,
    }


def normalize_month(value: Any) -> int:
    """Return a 1-12 month integer from numeric or month-name config values."""
    if isinstance(value, int):
        month = value
    else:
        text = str(value).strip()
        if text.isdigit():
            month = int(text)
        else:
            month = MONTH_NAME_TO_NUMBER.get(text.lower())
            if month is None:
                raise ValueError(f"Unknown month value: {value!r}")

    if month < 1 or month > 12:
        raise ValueError(f"Month must be between 1 and 12: {value!r}")
    return month
