from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Union


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
    return interpolate_env(config)


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


def get_database_config(config: dict[str, Any]) -> dict[str, Any]:
    database = config.get("database", {})
    return {
        "engine": database.get("engine", os.environ.get("GRAPH_DB_BACKEND", "memgraph")),
        "uri": database.get("uri", os.environ.get("GRAPH_DB_URI", "bolt://localhost:7687")),
        "user": database.get("user", os.environ.get("GRAPH_DB_USER", "")),
        "password": database.get(
            "password", os.environ.get("GRAPH_DB_PASSWORD", "")
        ),
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
