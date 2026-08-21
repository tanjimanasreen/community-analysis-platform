from __future__ import annotations

import importlib
import os
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 support
    import tomli as tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.config.settings import (
    DEFAULT_CLUSTERING_MODEL_ID,
    DEFAULT_CLUSTERING_MODEL_REVISION,
    DEFAULT_SIMILARITY_MODEL_ID,
    DEFAULT_SIMILARITY_MODEL_REVISION,
    get_clustering_tei_client_settings,
    get_provider_settings,
    get_tei_client_settings,
)
from src.themes.tei_health import embedding_dimensions

_REQUIRED_IMPORTS = (
    "numpy",
    "pandas",
    "scipy",
    "networkx",
    "gensim",
    "sklearn",
    "pyarrow",
    "kneed",
    "spacy",
    "demoji",
    "prefect",
)
_PROVIDER_SECRET_FIELDS = {
    "openai": "openai_api_key",
    "gemini": "gemini_api_key",
    "llm7": "llm7_api_key",
    "mistral": "mistral_api_key",
    "nvidia": "nvidia_api_key",
}
_PROVIDER_BASE_URL_FIELDS = {
    "llm7": "llm7_base_url",
    "mistral": "mistral_base_url",
    "nvidia": "nvidia_base_url",
}


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    ok: bool
    detail: str


class PipelinePreflightError(RuntimeError):
    def __init__(self, checks: Sequence[PreflightCheck]):
        self.checks = tuple(checks)
        failures = [check for check in checks if not check.ok]
        super().__init__(
            "pipeline preflight failed: "
            + "; ".join(f"{item.name}: {item.detail}" for item in failures)
        )


def run_pipeline_preflight(
    config: Mapping[str, Any],
    *,
    project_root: str | Path = ".",
    check_services: bool = True,
    check_credentials: bool = True,
) -> tuple[PreflightCheck, ...]:
    """Validate local prerequisites before an expensive longitudinal run.

    The check is intentionally scoped to resources used by the evolution
    pipeline. Memgraph is not required because this workflow consumes exported
    relationship CSVs directly.
    """
    root = Path(project_root).resolve()
    checks: list[PreflightCheck] = []

    checks.append(
        PreflightCheck(
            "python",
            sys.version_info >= (3, 10),
            (
                f"{sys.version_info.major}.{sys.version_info.minor}."
                f"{sys.version_info.micro}"
            ),
        )
    )
    checks.extend(_dependency_checks(config))
    tracking = config.get("tracking", {})
    lock_extras = ["orchestration"]
    if isinstance(tracking, Mapping) and bool(tracking.get("enabled", False)):
        lock_extras.append("tracking")
    checks.append(_lock_check(root, extras=lock_extras))
    checks.extend(_input_checks(config))
    checks.append(_output_check(config))
    if check_credentials:
        checks.extend(_credential_checks(config))
    checks.extend(_embedding_profile_checks(config, check_services=check_services))

    if any(not check.ok for check in checks):
        raise PipelinePreflightError(checks)
    return tuple(checks)


def _dependency_checks(config: Mapping[str, Any]) -> list[PreflightCheck]:
    modules = list(_REQUIRED_IMPORTS)
    tracking = config.get("tracking", {})
    if isinstance(tracking, Mapping) and bool(tracking.get("enabled", False)):
        modules.append("mlflow")

    broken: list[str] = []
    for module in modules:
        try:
            importlib.import_module(module)
        except Exception as exc:
            broken.append(f"{module} ({type(exc).__name__}: {exc})")

    checks = [
        PreflightCheck(
            "python-dependencies",
            not broken,
            (
                "all required imports available"
                if not broken
                else f"unavailable/broken imports: {', '.join(sorted(broken))}"
            ),
        )
    ]
    try:
        import sklearn
        from sklearn.cluster import HDBSCAN  # noqa: F401

        version = _version_tuple(sklearn.__version__)
        supported = (1, 7) <= version < (2, 0)
        checks.append(
            PreflightCheck(
                "sklearn-hdbscan",
                supported,
                f"scikit-learn={sklearn.__version__}; requires >=1.7,<2",
            )
        )
    except Exception as exc:
        checks.append(
            PreflightCheck("sklearn-hdbscan", False, f"{type(exc).__name__}: {exc}")
        )
    return checks


def _lock_check(
    root: Path, *, extras: Sequence[str] = ("orchestration",)
) -> PreflightCheck:
    root = Path(root)
    pyproject_path = root / "pyproject.toml"
    lock_path = root / "uv.lock"
    if not pyproject_path.is_file() or not lock_path.is_file():
        return PreflightCheck(
            "dependency-lock",
            False,
            "pyproject.toml and uv.lock must both exist at the project root",
        )
    try:
        with pyproject_path.open("rb") as handle:
            pyproject = tomllib.load(handle)
        with lock_path.open("rb") as handle:
            lock = tomllib.load(handle)
        expected = _requirements_from_pyproject(pyproject, extras=extras)
        actual = _requirements_from_uv_lock(lock, extras=extras)
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        return PreflightCheck(
            "dependency-lock", False, f"cannot parse dependency files: {exc}"
        )

    differences = [
        f"{name}: pyproject={specifier!r} lock={actual.get(name)!r}"
        for name, specifier in sorted(expected.items())
        if actual.get(name) != specifier
    ]
    stale = sorted(set(actual) - set(expected))
    # Extras are intentionally present in lock metadata and excluded by helper;
    # only core project requirements participate in this comparison.
    if stale:
        differences.extend(
            f"unexpected direct dependency in lock: {name}" for name in stale
        )
    external_hdbscan = any(
        str(package.get("name", "")).lower() == "hdbscan"
        for package in lock.get("package", [])
        if isinstance(package, Mapping)
    )
    if external_hdbscan:
        differences.append("external hdbscan package remains in uv.lock")
    if "hdbscan" in expected:
        differences.append("external hdbscan remains in pyproject.toml")

    return PreflightCheck(
        "dependency-lock",
        not differences,
        (
            "pyproject.toml and uv.lock direct dependencies agree"
            if not differences
            else "; ".join(differences)
        ),
    )


def _input_checks(config: Mapping[str, Any]) -> list[PreflightCheck]:
    datasets = config.get("longitudinal_datasets")
    if isinstance(datasets, list) and datasets:
        rows = datasets
    else:
        rows = [
            {
                "month": config.get("month", "single"),
                "input_path": config.get("input_path"),
            }
        ]
    checks: list[PreflightCheck] = []
    for row in rows:
        if not isinstance(row, Mapping):
            checks.append(
                PreflightCheck("input", False, f"invalid dataset entry: {row!r}")
            )
            continue
        month = str(row.get("month", "unknown"))
        raw_path = row.get("input_path")
        path = Path(str(raw_path)).expanduser() if raw_path else None
        ok = bool(path and path.is_file())
        checks.append(
            PreflightCheck(
                f"input-{month}",
                ok,
                str(path) if ok else f"missing relationship CSV: {path or raw_path!r}",
            )
        )
    return checks


def _output_check(config: Mapping[str, Any]) -> PreflightCheck:
    raw = config.get("output_base_path")
    if not raw:
        return PreflightCheck(
            "output-path", False, "output_base_path is not configured"
        )
    target = Path(str(raw)).expanduser()
    probe = target
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    ok = probe.exists() and probe.is_dir() and os.access(probe, os.W_OK)
    return PreflightCheck(
        "output-path",
        ok,
        (
            f"writable via {probe}"
            if ok
            else f"nearest existing parent is not writable: {probe}"
        ),
    )


def _credential_checks(config: Mapping[str, Any]) -> list[PreflightCheck]:
    theme_provider = config.get("theme_provider", {})
    if not isinstance(theme_provider, Mapping):
        return [
            PreflightCheck("theme-provider", False, "theme_provider must be a mapping")
        ]
    provider_specs = [str(theme_provider.get("primary", "mock"))]
    if bool(theme_provider.get("fallback", False)):
        fallback = theme_provider.get("fallback_chain", [])
        if isinstance(fallback, list):
            provider_specs.extend(str(value) for value in fallback)
    settings = get_provider_settings()
    checks: list[PreflightCheck] = []
    for spec in provider_specs:
        prefix = spec.split(":", 1)[0].strip().lower()
        secret_field = _PROVIDER_SECRET_FIELDS.get(prefix)
        if secret_field is None:
            checks.append(
                PreflightCheck(
                    f"provider-{prefix}",
                    prefix in {"mock", "keyword_baseline"},
                    (
                        "offline provider"
                        if prefix in {"mock", "keyword_baseline"}
                        else f"no credential contract is defined for provider {prefix!r}"
                    ),
                )
            )
            continue
        secret = getattr(settings, secret_field, None)
        present = secret is not None and bool(secret.get_secret_value().strip())
        base_field = _PROVIDER_BASE_URL_FIELDS.get(prefix)
        base_url = getattr(settings, base_field, None) if base_field else None
        base_ok = base_field is None or base_url is not None
        missing_parts = []
        if not present:
            missing_parts.append(secret_field.upper())
        if not base_ok and base_field:
            missing_parts.append(base_field.upper())
        checks.append(
            PreflightCheck(
                f"provider-{prefix}",
                present and base_ok,
                (
                    "provider credentials/config configured"
                    if present and base_ok
                    else f"missing {', '.join(missing_parts)}"
                ),
            )
        )
    return checks


def _embedding_profile_checks(
    config: Mapping[str, Any], *, check_services: bool
) -> list[PreflightCheck]:
    theme = config.get("theme", {})
    theme = theme if isinstance(theme, Mapping) else {}
    checks: list[PreflightCheck] = []

    if (
        bool(theme.get("clustering_enabled", False))
        and str(theme.get("clustering_provider", "tei")).strip().lower() == "tei"
    ):
        settings = get_clustering_tei_client_settings()
        expected_model = str(
            theme.get("clustering_model", DEFAULT_CLUSTERING_MODEL_ID)
        ).strip()
        expected_revision = str(
            theme.get("clustering_model_revision", DEFAULT_CLUSTERING_MODEL_REVISION)
        ).strip()
        checks.append(
            _profile_contract_check(
                "clustering",
                actual_model=str(settings.model_id),
                actual_revision=str(settings.revision),
                expected_model=expected_model,
                expected_revision=expected_revision,
            )
        )
        if check_services:
            checks.append(
                _profile_service_check(
                    "clustering",
                    base_url=str(settings.base_url),
                    api_key=(
                        settings.api_key.get_secret_value()
                        if settings.api_key
                        else None
                    ),
                    timeout=float(settings.timeout_seconds),
                    normalize=False,
                )
            )

    # Similarity TEI is required only when the evolution run renders similarity
    # heatmaps. The canonical evolution configs keep render_visuals=false.
    if bool(theme.get("render_visuals", False)):
        settings = get_tei_client_settings()
        expected_model = str(
            theme.get("similarity_model", DEFAULT_SIMILARITY_MODEL_ID)
        ).strip()
        if "/" not in expected_model:
            expected_model = f"sentence-transformers/{expected_model}"
        expected_revision = str(
            theme.get("similarity_model_revision", DEFAULT_SIMILARITY_MODEL_REVISION)
        ).strip()
        checks.append(
            _profile_contract_check(
                "similarity",
                actual_model=str(settings.model_id),
                actual_revision=str(settings.revision),
                expected_model=expected_model,
                expected_revision=expected_revision,
            )
        )
        if check_services:
            checks.append(
                _profile_service_check(
                    "similarity",
                    base_url=str(settings.base_url),
                    api_key=(
                        settings.api_key.get_secret_value()
                        if settings.api_key
                        else None
                    ),
                    timeout=float(settings.timeout_seconds),
                    normalize=True,
                )
            )
    return checks


def _profile_contract_check(
    profile: str,
    *,
    actual_model: str,
    actual_revision: str,
    expected_model: str,
    expected_revision: str,
) -> PreflightCheck:
    ok = actual_model == expected_model and actual_revision == expected_revision
    return PreflightCheck(
        f"tei-{profile}-contract",
        ok,
        (
            f"model={actual_model} revision={actual_revision}"
            if ok
            else (
                f"runtime model/revision {actual_model}@{actual_revision} does not match "
                f"config {expected_model}@{expected_revision}"
            )
        ),
    )


def _profile_service_check(
    profile: str,
    *,
    base_url: str,
    api_key: str | None,
    timeout: float,
    normalize: bool,
) -> PreflightCheck:
    try:
        dimensions = embedding_dimensions(
            base_url,
            api_key,
            timeout=min(timeout, 5.0),
            normalize=normalize,
        )
    except Exception as exc:  # Render network/HTTP failures as preflight diagnostics.
        return PreflightCheck(f"tei-{profile}-service", False, f"{base_url}: {exc}")
    return PreflightCheck(
        f"tei-{profile}-service",
        dimensions == 384,
        f"{base_url} dimensions={dimensions}; expected 384",
    )


def _requirements_from_pyproject(
    payload: Mapping[str, Any], *, extras: Sequence[str] = ()
) -> dict[str, str]:
    project = payload.get("project", {})
    dependencies = (
        project.get("dependencies", []) if isinstance(project, Mapping) else []
    )
    result: dict[str, str] = {}
    for requirement in dependencies:
        name, specifier, marker = _split_requirement(str(requirement))
        if _marker_applies(marker, extras=extras):
            result[name] = specifier
    optional = (
        project.get("optional-dependencies", {}) if isinstance(project, Mapping) else {}
    )
    if isinstance(optional, Mapping):
        for extra in extras:
            for requirement in optional.get(extra, []):
                name, specifier, marker = _split_requirement(str(requirement))
                if _marker_applies(marker, extras=extras):
                    result[name] = specifier
    return result


def _requirements_from_uv_lock(
    payload: Mapping[str, Any], *, extras: Sequence[str] = ()
) -> dict[str, str]:
    for package in payload.get("package", []):
        if (
            not isinstance(package, Mapping)
            or package.get("name") != "community-analysis"
        ):
            continue
        metadata = package.get("metadata", {})
        rows = (
            metadata.get("requires-dist", []) if isinstance(metadata, Mapping) else []
        )
        return {
            _normalize_name(str(row.get("name", ""))): str(row.get("specifier", ""))
            for row in rows
            if isinstance(row, Mapping)
            and row.get("name")
            and _marker_applies(str(row.get("marker", "")), extras=extras)
        }
    return {}


def _split_requirement(requirement: str) -> tuple[str, str, str]:
    requirement_text, separator, marker = requirement.partition(";")
    match = re.match(r"^([A-Za-z0-9_.-]+)\s*(.*)$", requirement_text.strip())
    if not match:
        raise ValueError(f"invalid requirement: {requirement!r}")
    return (
        _normalize_name(match.group(1)),
        match.group(2).replace(" ", ""),
        marker.strip() if separator else "",
    )


def _marker_applies(marker: str, *, extras: Sequence[str]) -> bool:
    marker = marker.strip()
    if not marker:
        return True
    extra_match = re.fullmatch(r"extra\s*==\s*['\"]([^'\"]+)['\"]", marker)
    if extra_match:
        return extra_match.group(1) in extras
    python_match = re.fullmatch(
        r"python_(?:full_)?version\s*(<=|>=|==|!=|<|>)\s*['\"]([^'\"]+)['\"]",
        marker,
    )
    if python_match:
        operator, expected = python_match.groups()
        current = (
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro,
        )
        expected_parts = tuple(int(part) for part in expected.split("."))
        expected_value = expected_parts + (0,) * (3 - len(expected_parts))
        comparisons = {
            "<": current < expected_value,
            "<=": current <= expected_value,
            ">": current > expected_value,
            ">=": current >= expected_value,
            "==": current[: len(expected_parts)] == expected_parts,
            "!=": current[: len(expected_parts)] != expected_parts,
        }
        return comparisons[operator]
    # A direct requirement marker we cannot safely evaluate should fail closed
    # in the dependency-lock check rather than silently accepting drift.
    raise ValueError(f"unsupported dependency marker in preflight: {marker!r}")


def _normalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _version_tuple(value: str) -> tuple[int, int]:
    parts = re.findall(r"\d+", value)
    if len(parts) < 2:
        return (0, 0)
    return int(parts[0]), int(parts[1])
