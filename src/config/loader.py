from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping, Union

from src.config.defaults import DEFAULT_CONFIG
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
        from src.config.settings import get_interpolated_env_vars

        env_vars = get_interpolated_env_vars()
        return ENV_VAR_RE.sub(lambda match: env_vars.get(match.group(1), ""), value)
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

    # Ensure orchestration defaults are populated. Cross-run analytical reuse is
    # content/config/code addressed and does not expire on an arbitrary TTL.
    orch = merged_config.setdefault("orchestration", {})
    orch.setdefault("artifact_reuse", True)
    # Keep expensive monthly LDA jobs sequential by default. Each job already
    # uses LdaMulticore; running several months concurrently otherwise creates
    # nested process pools, memory spikes, and CPU oversubscription.
    orch.setdefault("month_workers", 1)
    # Theme-provider concurrency is I/O-bound and remains independently tunable.
    orch.setdefault("max_workers", 4)

    translation = merged_config.setdefault("translation", {})
    translation.setdefault("enabled", False)
    translation.setdefault("provider", "azure")
    translation.setdefault("target_language", "en")
    translation.setdefault("contract_version", "v1")
    translation.setdefault("cache_path", ".cache/translation_cache.sqlite3")
    translation.setdefault("timeout_seconds", 30.0)

    dashboard = merged_config.setdefault("dashboard", {})
    # The complete graph remains a thesis artifact; this bounded additive sample
    # is used only for the global dashboard visualization endpoint.
    dashboard.setdefault("graph_sample_max_edges", 50_000)

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


def validate_lda_config(lda_config: Mapping[str, Any] | None = None) -> None:
    """Validate the supported production LDA implementation and priors."""
    raw = dict(lda_config or {})
    implementation = str(
        raw.get("implementation", DEFAULT_CONFIG.lda.implementation)
    ).strip()
    if implementation != DEFAULT_CONFIG.lda.implementation:
        raise ValueError(
            "lda.implementation must be 'ldamulticore'; " f"got {implementation!r}"
        )

    alpha = raw.get("alpha", DEFAULT_CONFIG.lda.alpha)
    if isinstance(alpha, str) and alpha.strip().lower() == "auto":
        raise ValueError(
            "LdaMulticore does not support lda.alpha='auto'; "
            "use the approved production default lda.alpha='symmetric'"
        )


def validate_theme_provider_config_policy(config: Mapping[str, Any]) -> None:
    """Reject provider-routing keys from the analytical ``theme`` namespace."""
    theme = config.get("theme", {})
    if not isinstance(theme, Mapping):
        return

    stale_keys = [key for key in ("fallback", "fallback_chain") if key in theme]
    if stale_keys:
        stale_paths = ", ".join(f"theme.{key}" for key in stale_keys)
        canonical_paths = ", ".join(f"theme_provider.{key}" for key in stale_keys)
        raise ValueError(
            f"Unsupported provider-routing setting(s): {stale_paths}. "
            f"Use {canonical_paths} instead; the `theme` section is reserved "
            "for analytical theme-processing settings."
        )


def validate_database_config_policy(config: Mapping[str, Any]) -> None:
    """Reject graph-database connection settings in analytical YAML configs."""
    locations: list[str] = []
    if "database" in config:
        locations.append("database")

    for collection_key in ("datasets", "longitudinal_datasets"):
        entries = config.get(collection_key, [])
        if not isinstance(entries, list):
            continue
        for index, entry in enumerate(entries):
            if isinstance(entry, Mapping) and "database" in entry:
                locations.append(f"{collection_key}[{index}].database")

    if locations:
        location_text = ", ".join(locations)
        raise ValueError(
            "Database connection settings are environment-only. "
            f"Remove YAML section(s): {location_text}. "
            "Configure GRAPH_DB_ENGINE, GRAPH_DB_URI, GRAPH_DB_USER, and "
            "GRAPH_DB_PASSWORD instead."
        )


def validate_run_config(config: dict[str, Any]) -> None:
    validate_database_config_policy(config)
    validate_theme_provider_config_policy(config)

    required = (
        "data_type",
        "content_type",
        "year",
        "output_base_path",
        "creator_relation",
        "spreader_relation",
        "creator_node_column",
        "spreader_node_column",
        "text_node_column",
        "date_column",
    )
    if "longitudinal_datasets" not in config:
        required += ("month", "input_path")

    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"Missing required config keys: {', '.join(missing)}")

    validate_lda_config(config.get("lda"))

    thresholds = config.get("graph_thresholds", {})
    for key in ("min_total_post", "min_shared_post", "min_members"):
        if key in thresholds and int(thresholds[key]) < 0:
            raise ValueError(f"graph_thresholds.{key} must be non-negative")

    orchestration = config.get("orchestration", {})
    if isinstance(orchestration, Mapping) and "artifact_reuse" in orchestration:
        if not isinstance(orchestration["artifact_reuse"], bool):
            raise ValueError("orchestration.artifact_reuse must be a boolean")

    translation = config.get("translation", {})
    if not isinstance(translation, Mapping):
        raise ValueError("translation must be a mapping")
    if not isinstance(translation.get("enabled", False), bool):
        raise ValueError("translation.enabled must be a boolean")
    provider = str(translation.get("provider", "azure")).strip().lower()
    if provider not in {"azure", "aws"}:
        raise ValueError("translation.provider must be one of: azure, aws")
    target_language = str(translation.get("target_language", "en")).strip().lower()
    if target_language != "en":
        raise ValueError(
            "translation.target_language must be 'en' in translation contract v1"
        )
    contract_version = str(translation.get("contract_version", "v1")).strip()
    if not contract_version:
        raise ValueError("translation.contract_version must be non-empty")
    cache_path = str(
        translation.get("cache_path", ".cache/translation_cache.sqlite3")
    ).strip()
    if not cache_path:
        raise ValueError("translation.cache_path must be non-empty")
    try:
        timeout_seconds = float(translation.get("timeout_seconds", 30.0))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "translation.timeout_seconds must be a positive number"
        ) from exc
    if timeout_seconds <= 0:
        raise ValueError("translation.timeout_seconds must be a positive number")

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
    # Runtime graph-database connectivity is environment-only. Reject stale YAML
    # sections explicitly instead of silently ignoring operator configuration.
    validate_database_config_policy(config)
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
