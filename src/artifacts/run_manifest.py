from __future__ import annotations

import calendar
import csv
import hashlib
import json
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Sequence

import yaml

from src.artifacts.models import (
    ArtifactCategory,
    ArtifactRecord,
    RunManifest,
    RunStatus,
)

if TYPE_CHECKING:
    from src.orchestration.models import (
        ArtifactReference,
        DatasetIdentity,
        PipelineRunContext,
        ValidatedRunConfiguration,
    )

MANIFEST_FILE = "manifest.json"
RESOLVED_CONFIG_FILE = "resolved_config.yaml"
DATASETS_FILE = "inputs/datasets.json"

_RUN_DIRECTORIES = (
    "inputs",
    "intermediate/topic_inputs",
    "intermediate/theme_inputs",
    "data/network",
    "data/communities",
    "data/metrics",
    "data/topics",
    "data/themes",
    "reports/tables",
    "reports/figures",
    "logs",
)

_NETWORK_KEYS = {"network_data"}
_COMMUNITY_PATHS = {
    "communities_absolute": "absolute",
    "communities_weighted": "weighted",
    "communities_matched": "matched",
    "communities_partially_matched": "partially_matched",
}
_COMMUNITY_SUMMARY_PATHS = {
    "community_summary_absolute": "absolute",
    "community_summary_weighted": "weighted",
}
_COMMUNITY_GRAPH_SAMPLE_PATHS = {
    "community_graph_sample_absolute": "absolute",
    "community_graph_sample_weighted": "weighted",
}
_COMMUNITY_NODE_INDEX_PATHS = {
    "community_node_index_absolute": "absolute",
    "community_node_index_weighted": "weighted",
}
_COMMUNITY_INTERACTION_PATHS = {
    "community_interactions_absolute": "absolute",
    "community_interactions_weighted": "weighted",
}
_METRIC_KEYS = {
    "user_centrality",
    "count_user_messages",
    "daily_messages_stat",
}
_TOPIC_PATHS = {
    "lda_scores": "scores",
    "matched_communities_topics": "matched",
    "partial_matched_communities_topics": "partial_matched",
    "translation_provenance": "translations",
}

_PUBLIC_SCHEMA_ALIASES = {
    "network_data": "network_data",
    "communities_absolute": "absolute_community_graph",
    "communities_weighted": "weighted_community_graph",
    "communities_matched": "matched_communities",
    "communities_partially_matched": "partial_matched_communities",
    "community_summary_absolute": "community_summary",
    "community_summary_weighted": "community_summary",
    "community_graph_sample_absolute": "absolute_community_graph",
    "community_graph_sample_weighted": "weighted_community_graph",
    "community_node_index_absolute": "community_node_index",
    "community_node_index_weighted": "community_node_index",
    "community_interactions_absolute": "community_interactions",
    "community_interactions_weighted": "community_interactions",
    "user_centrality": "user_centrality",
    "count_user_messages": "count_user_messages",
    "daily_messages_stat": "daily_messages_stat",
    "lda_scores": "lda_scores",
    "matched_communities_topics": "matched_lda",
    "partial_matched_communities_topics": "partial_matched_lda",
    "translation_provenance": "translation_provenance",
    "community_transitions": "community_transition",
    "community_paths": "community_path",
    "community_path_membership": "community_path_membership",
    "community_path_theme_similarity": "community_path_theme_similarity",
    "theme_generation_provenance": "theme_generation_provenance",
    "theme_canonical_families": "theme_canonical_family",
    "theme_embeddings_clustering": "theme_embedding",
    "theme_embeddings_similarity": "theme_embedding",
}

_EXPECTED_MEDIA_TYPES = {
    ".csv": {"text/csv", "text/plain"},
    ".html": {"text/html"},
    ".json": {"application/json"},
    ".jpeg": {"image/jpeg"},
    ".jpg": {"image/jpeg"},
    ".parquet": {"application/vnd.apache.parquet", "application/octet-stream"},
    ".pdf": {"application/pdf"},
    ".png": {"image/png"},
    ".svg": {"image/svg+xml"},
}


_MONTH_SUFFIXES = {
    *(f"{month:02d}" for month in range(1, 13)),
    *(str(month) for month in range(1, 13)),
    *(name.lower() for name in calendar.month_name if name),
    *(name.lower() for name in calendar.month_abbr if name),
}


def _base_artifact_key(key: str) -> str:
    """Remove one configured month suffix while preserving the artifact identity.

    Artifact-producing tasks suffix keys with numeric, abbreviated, or full month
    values. Canonical routing and schema lookup must normalize all three forms in
    exactly the same way.
    """
    normalized = str(key).strip()
    prefix, separator, suffix = normalized.rpartition("_")
    if separator and suffix.casefold() in _MONTH_SUFFIXES:
        return prefix
    return normalized


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_root_path(output_root: str | Path, run_id: str) -> Path:
    """Return a traversal-safe canonical run root below the artifact root."""
    normalized_run_id = str(run_id).strip()
    if (
        not normalized_run_id
        or normalized_run_id in {".", ".."}
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", normalized_run_id) is None
    ):
        raise ValueError("run_id must be a non-empty filesystem-safe identifier")

    runs_root = Path(output_root).expanduser().resolve() / "runs"
    run_root = (runs_root / normalized_run_id).resolve()
    try:
        run_root.relative_to(runs_root)
    except ValueError as exc:
        raise ValueError("run_id escapes the configured artifact root") from exc
    return run_root


def initialize_run_bundle(
    *,
    context: PipelineRunContext,
    config: ValidatedRunConfiguration,
    started_at: str | None = None,
    mlflow_run_id: str | None = None,
) -> Path:
    """Create the run layout and atomically persist a RUNNING manifest."""
    root = run_root_path(context.output_root, context.pipeline_run_id)
    _assert_manifest_absent(root)
    _ensure_layout(root)
    _write_resolved_config(root, config.raw_config)
    _write_dataset_inputs(root, context.dataset_identities)
    manifest = _build_manifest(
        context=context,
        config=config,
        status=RunStatus.RUNNING,
        artifacts=(),
        started_at=started_at or utc_now(),
        completed_at=None,
        mlflow_run_id=mlflow_run_id,
        failure=None,
    )
    _atomic_write_json(root / MANIFEST_FILE, manifest.to_dict())
    return root / MANIFEST_FILE


def complete_run_bundle(
    *,
    context: PipelineRunContext,
    config: ValidatedRunConfiguration,
    artifacts: Sequence[ArtifactReference],
    started_at: str,
    completed_at: str | None = None,
    mlflow_run_id: str | None = None,
) -> RunManifest:
    """Publish canonical artifacts and atomically mark the run completed."""
    root = run_root_path(context.output_root, context.pipeline_run_id)
    _require_running_manifest(root, context.pipeline_run_id)
    _ensure_layout(root)
    records = _publish_artifacts(root, artifacts)
    manifest = _build_manifest(
        context=context,
        config=config,
        status=RunStatus.COMPLETED,
        artifacts=records,
        started_at=started_at,
        completed_at=completed_at or utc_now(),
        mlflow_run_id=mlflow_run_id,
        failure=None,
    )
    validate_run_manifest(manifest, root)
    _atomic_write_json(root / MANIFEST_FILE, manifest.to_dict())
    return manifest


def fail_run_bundle(
    *,
    context: PipelineRunContext,
    config: ValidatedRunConfiguration,
    started_at: str,
    failure_stage: str,
    failure_type: str,
    failure_category: str,
    artifacts: Sequence[ArtifactReference] = (),
    completed_at: str | None = None,
    mlflow_run_id: str | None = None,
) -> RunManifest:
    """Persist a terminal FAILED manifest without exposing exception text."""
    root = run_root_path(context.output_root, context.pipeline_run_id)
    _require_running_manifest(root, context.pipeline_run_id)
    _ensure_layout(root)
    records: tuple[ArtifactRecord, ...] = ()
    if artifacts:
        try:
            records = _publish_artifacts(root, artifacts)
        except (OSError, ValueError):
            # Failure finalization must not be blocked by a malformed partial output.
            records = ()
    manifest = _build_manifest(
        context=context,
        config=config,
        status=RunStatus.FAILED,
        artifacts=records,
        started_at=started_at,
        completed_at=completed_at or utc_now(),
        mlflow_run_id=mlflow_run_id,
        failure={
            "stage": failure_stage,
            "type": failure_type,
            "category": failure_category,
        },
    )
    validate_run_manifest(manifest, root)
    _atomic_write_json(root / MANIFEST_FILE, manifest.to_dict())
    return manifest


def load_run_manifest(path_or_root: str | Path) -> RunManifest:
    path = Path(path_or_root)
    if path.is_dir():
        path = path / MANIFEST_FILE
    payload = json.loads(path.read_text(encoding="utf-8"))
    return RunManifest.from_dict(payload)


def validate_run_manifest(
    manifest_or_path: RunManifest | str | Path,
    run_root: str | Path | None = None,
) -> RunManifest:
    """Validate lifecycle invariants and every referenced canonical artifact."""
    if isinstance(manifest_or_path, RunManifest):
        manifest = manifest_or_path
        if run_root is None:
            raise ValueError(
                "run_root is required when validating a RunManifest object"
            )
        root = Path(run_root).resolve()
    else:
        path = Path(manifest_or_path)
        if path.is_dir():
            path = path / MANIFEST_FILE
        manifest = load_run_manifest(path)
        root = path.parent.resolve()

    if root.name != manifest.run_id:
        raise ValueError("run manifest identifier does not match its directory")

    started_at = manifest.pipeline.get("started_at")
    if not started_at:
        raise ValueError("run manifests require started_at")
    completed_at = manifest.pipeline.get("completed_at")
    if manifest.status is RunStatus.RUNNING and completed_at:
        raise ValueError("running manifests must not have completed_at")
    if manifest.status in {RunStatus.COMPLETED, RunStatus.FAILED} and not completed_at:
        raise ValueError("terminal manifests require completed_at")
    if manifest.status is RunStatus.COMPLETED and not manifest.artifacts:
        raise ValueError("completed manifests require at least one artifact")

    for required_path in (root / RESOLVED_CONFIG_FILE, root / DATASETS_FILE):
        if not required_path.is_file():
            raise ValueError(f"run metadata file is missing: {required_path}")

    for record in manifest.artifacts:
        _validate_artifact_record(root, record)
    return manifest


def _assert_manifest_absent(root: Path) -> None:
    manifest_path = root / MANIFEST_FILE
    if manifest_path.exists():
        raise ValueError(f"run manifest already exists: {manifest_path}")


def _require_running_manifest(root: Path, run_id: str) -> RunManifest:
    manifest_path = root / MANIFEST_FILE
    if not manifest_path.is_file():
        raise ValueError(f"running run manifest is missing: {manifest_path}")
    manifest = load_run_manifest(manifest_path)
    if manifest.run_id != run_id:
        raise ValueError("run manifest identifier does not match the run context")
    if manifest.status is not RunStatus.RUNNING:
        raise ValueError(
            "run manifest is terminal and cannot be finalized again: "
            f"{manifest.status.value}"
        )
    return manifest


def _ensure_layout(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for relative in _RUN_DIRECTORIES:
        (root / relative).mkdir(parents=True, exist_ok=True)


def _write_resolved_config(root: Path, config: Mapping[str, Any]) -> None:
    payload = yaml.safe_dump(dict(config), sort_keys=True, allow_unicode=True)
    _atomic_write_text(root / RESOLVED_CONFIG_FILE, payload)


def _write_dataset_inputs(root: Path, datasets: Sequence[DatasetIdentity]) -> None:
    payload = {
        "schema_version": "1.0",
        "datasets": [
            {
                "dataset_id": dataset.dataset_id,
                "source_name": Path(dataset.path).name,
                "sha256": dataset.sha256,
                "platform": dataset.platform,
                "interaction_type": dataset.interaction_type,
                "period": dataset.period,
                "identity_source": dataset.identity_source,
                "dvc_pointer_name": (
                    Path(dataset.dvc_pointer).name if dataset.dvc_pointer else None
                ),
                "dvc_content_hash": dataset.dvc_content_hash,
                "dvc_revision": dataset.dvc_revision,
            }
            for dataset in datasets
        ],
    }
    _atomic_write_json(root / DATASETS_FILE, payload)


def _build_manifest(
    *,
    context: PipelineRunContext,
    config: ValidatedRunConfiguration,
    status: RunStatus,
    artifacts: Sequence[ArtifactRecord],
    started_at: str,
    completed_at: str | None,
    mlflow_run_id: str | None,
    failure: Mapping[str, Any] | None,
) -> RunManifest:
    raw = config.raw_config
    identity = context.dataset_identities[0] if context.dataset_identities else None
    date_start, date_end = _date_range(raw)
    dataset = {
        "dataset_id": identity.dataset_id if identity else "unknown",
        "platform": str(
            raw.get("data_type") or (identity.platform if identity else "")
        ),
        "content_type": str(raw.get("content_type", "")),
        "date_start": date_start,
        "date_end": date_end,
        "source_hash": identity.sha256 if identity else "",
    }
    pipeline = {
        "started_at": started_at,
        "completed_at": completed_at,
        "prefect_flow_run_id": context.prefect_flow_run_id,
        "mlflow_run_id": mlflow_run_id,
    }
    return RunManifest(
        run_id=context.pipeline_run_id,
        status=status,
        dataset=dataset,
        code={
            "git_commit": context.git_commit,
            "config_digest": context.config_digest,
        },
        pipeline=pipeline,
        artifacts=tuple(artifacts),
        failure=failure,
    )


def _date_range(config: Mapping[str, Any]) -> tuple[str | None, str | None]:
    try:
        year = int(config["year"])
        month = _month_number(config["month"])
    except (KeyError, TypeError, ValueError):
        return None, None
    final_day = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{final_day:02d}"


def _month_number(value: Any) -> int:
    text = str(value).strip().lower()
    if text.isdigit():
        month = int(text)
    else:
        names = {
            name.lower(): index
            for index, name in enumerate(calendar.month_name)
            if name
        }
        abbreviations = {
            name.lower(): index
            for index, name in enumerate(calendar.month_abbr)
            if name
        }
        month = names.get(text) or abbreviations.get(text)
    if not month or not 1 <= month <= 12:
        raise ValueError(f"invalid month: {value!r}")
    return month


def _publish_artifacts(
    root: Path, artifacts: Sequence[ArtifactReference]
) -> tuple[ArtifactRecord, ...]:
    records: list[ArtifactRecord] = []
    seen_keys: set[str] = set()
    for ref in artifacts:
        key = ref.asset_key or _fallback_key(ref.path)
        if key in seen_keys:
            raise ValueError(f"duplicate artifact key: {key}")
        seen_keys.add(key)
        source = Path(ref.path).resolve(strict=True)
        try:
            source.relative_to(root.resolve())
        except ValueError as exc:
            raise ValueError(f"artifact is outside the run root: {source}") from exc
        actual_size = source.stat().st_size
        if ref.byte_size is not None and actual_size != ref.byte_size:
            raise ValueError(f"source artifact byte size mismatch: {source}")
        if _hash_file(source) != ref.sha256:
            raise ValueError(f"source artifact checksum mismatch: {source}")
        if source.suffix.lower() == ".parquet" and ref.row_count is not None:
            actual_rows, _ = _parquet_shape(source)
            if actual_rows != ref.row_count:
                raise ValueError(f"source artifact row count mismatch: {source}")
        elif source.suffix.lower() == ".csv" and ref.row_count is not None:
            actual_rows, _ = _csv_shape(source)
            if actual_rows != ref.row_count:
                raise ValueError(f"source artifact row count mismatch: {source}")

        category, relative = _canonical_location(root, key, source)
        target = root / relative
        _atomic_copy(source, target)
        if target.suffix.lower() == ".parquet":
            rows = _parquet_shape(target)[0]
        elif target.suffix.lower() == ".csv":
            rows = _csv_shape(target)[0]
        else:
            rows = ref.row_count
        record = ArtifactRecord(
            key=key,
            path=relative.as_posix(),
            category=category,
            media_type=ref.media_type,
            schema_version=_artifact_schema_version(key, target),
            sha256=_hash_file(target),
            rows=rows,
            byte_size=target.stat().st_size,
            stage=_artifact_stage(key),
        )
        _validate_artifact_record(root, record)
        records.append(record)
    return tuple(records)


def _fallback_key(path: str) -> str:
    return Path(path).stem.replace(" ", "_")


def _canonical_location(
    root: Path, key: str, source: Path
) -> tuple[ArtifactCategory, Path]:
    base_key = _base_artifact_key(key)
    if base_key.startswith("topic_") or base_key == "theme_manifest":
        return ArtifactCategory.INTERMEDIATE, _intermediate_path(root, source, base_key)
    if base_key in _NETWORK_KEYS:
        return ArtifactCategory.DATA, Path("data/network") / source.name
    if base_key in _COMMUNITY_PATHS:
        return (
            ArtifactCategory.DATA,
            Path("data/communities") / _COMMUNITY_PATHS[base_key] / source.name,
        )
    if base_key in _COMMUNITY_SUMMARY_PATHS:
        return (
            ArtifactCategory.DATA,
            Path("data/communities/summary")
            / _COMMUNITY_SUMMARY_PATHS[base_key]
            / source.name,
        )
    if base_key in _COMMUNITY_GRAPH_SAMPLE_PATHS:
        return (
            ArtifactCategory.DATA,
            Path("data/communities/graph_samples")
            / _COMMUNITY_GRAPH_SAMPLE_PATHS[base_key]
            / source.name,
        )
    if base_key in _COMMUNITY_NODE_INDEX_PATHS:
        return (
            ArtifactCategory.DATA,
            Path("data/communities/node_index")
            / _COMMUNITY_NODE_INDEX_PATHS[base_key]
            / source.name,
        )
    if base_key in _COMMUNITY_INTERACTION_PATHS:
        return (
            ArtifactCategory.DATA,
            Path("data/communities/interactions")
            / _COMMUNITY_INTERACTION_PATHS[base_key]
            / source.name,
        )
    if base_key in _METRIC_KEYS:
        return ArtifactCategory.DATA, Path("data/metrics") / base_key / source.name
    if base_key in _TOPIC_PATHS:
        return (
            ArtifactCategory.DATA,
            Path("data/topics") / _TOPIC_PATHS[base_key] / source.name,
        )
    normalized_key = str(key).strip()
    if normalized_key.startswith("theme_clusters_"):
        return ArtifactCategory.DATA, Path("data/themes/clusters/monthly") / source.name
    if normalized_key.startswith("theme_cluster_observations_"):
        return (
            ArtifactCategory.DATA,
            Path("data/themes/clusters/evidence") / source.name,
        )
    if normalized_key == "theme_canonical_families":
        return ArtifactCategory.DATA, Path("data/themes/clusters") / source.name
    if normalized_key in {"theme_embeddings_clustering", "theme_embeddings_similarity"}:
        return ArtifactCategory.DATA, Path("data/themes/embeddings") / source.name
    if normalized_key.startswith("themes_"):
        return ArtifactCategory.DATA, Path("data/themes/monthly") / source.name
    if base_key == "community_transitions":
        return ArtifactCategory.DATA, Path("data/themes") / source.name
    if base_key in {
        "community_paths",
        "community_path_membership",
        "community_path_theme_similarity",
    }:
        return ArtifactCategory.DATA, Path("data/evolution") / source.name
    if base_key in {"provider_run_summary", "theme_generation_provenance"}:
        return ArtifactCategory.DATA, Path("data/themes") / source.name
    if base_key.startswith("visualization_"):
        group = source.parent.name if source.parent != root else "general"
        return (
            ArtifactCategory.REPORT,
            Path("reports/figures") / group / source.name,
        )
    if base_key.startswith("report_"):
        return ArtifactCategory.REPORT, Path("reports") / source.name
    return ArtifactCategory.DATA, Path("data/misc") / base_key / source.name


def _intermediate_path(root: Path, source: Path, base_key: str) -> Path:
    relative = source.relative_to(root)
    parts = relative.parts
    if "_intermediate" in parts:
        index = parts.index("_intermediate")
        return Path("_intermediate", *parts[index + 1 :])
    section = "theme_inputs" if base_key == "theme_manifest" else "topic_inputs"
    return Path("_intermediate") / section / source.name


def _artifact_stage(key: str) -> str:
    if (
        key.startswith("themes_")
        or key.startswith("theme_clusters_")
        or key.startswith("theme_cluster_observations_")
        or key == "theme_canonical_families"
        or key in {"theme_embeddings_clustering", "theme_embeddings_similarity"}
        or key.startswith("visualization_")
        or key
        in {
            "community_transitions",
            "community_paths",
            "community_path_membership",
            "community_path_theme_similarity",
            "provider_run_summary",
            "theme_generation_provenance",
        }
    ):
        return "theme"
    if (
        key in _TOPIC_PATHS
        or key == "theme_manifest"
        or key.startswith("translation_provenance_")
    ):
        return "topic"
    return "network_community"


def _artifact_schema_version(key: str, path: Path) -> str:
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return "1"
        if isinstance(payload, Mapping):
            return str(payload.get("schema_version", "1"))
        return "1"
    return "1"


def validate_artifact_record(run_root: str | Path, record: ArtifactRecord) -> Path:
    """Validate one manifest-listed artifact and return its resolved path.

    This narrow public helper lets read-only consumers verify only the requested
    artifact instead of re-hashing every artifact in the run.
    """
    root = Path(run_root).resolve()
    _validate_artifact_record(root, record)
    return (root / record.path).resolve(strict=True)


def _validate_artifact_record(root: Path, record: ArtifactRecord) -> None:
    path = (root / record.path).resolve(strict=True)
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"artifact path escapes the run root: {record.path}") from exc
    if not path.is_file():
        raise ValueError(f"artifact is not a regular file: {record.path}")

    expected_prefix = {
        ArtifactCategory.INTERMEDIATE: "_intermediate",
        ArtifactCategory.DATA: "data",
        ArtifactCategory.REPORT: "reports",
    }[record.category]
    if Path(record.path).parts[0] != expected_prefix:
        raise ValueError(f"artifact category/path mismatch: {record.key}")

    allowed_media_types = _EXPECTED_MEDIA_TYPES.get(path.suffix.lower())
    if allowed_media_types is None:
        raise ValueError(f"artifact extension is not supported: {record.path}")
    if record.media_type not in allowed_media_types:
        raise ValueError(f"artifact media type mismatch: {record.key}")

    if _hash_file(path) != record.sha256:
        raise ValueError(f"artifact checksum mismatch: {record.key}")
    if record.byte_size is not None and path.stat().st_size != record.byte_size:
        raise ValueError(f"artifact byte size mismatch: {record.key}")

    if path.suffix.lower() == ".parquet":
        rows, columns = _parquet_shape(path)
        if record.rows is not None and rows != record.rows:
            raise ValueError(f"artifact row count mismatch: {record.key}")
        required = _required_columns(record.key, run_root=root)
        missing = [column for column in required if column not in columns]
        if missing:
            raise ValueError(
                f"artifact schema mismatch for {record.key}; missing columns: {missing}"
            )
    elif path.suffix.lower() == ".csv":
        rows, columns = _csv_shape(path)
        if record.rows is not None and rows != record.rows:
            raise ValueError(f"artifact row count mismatch: {record.key}")
        required = _required_columns(record.key, run_root=root)
        missing = [column for column in required if column not in columns]
        if missing:
            raise ValueError(
                f"artifact schema mismatch for {record.key}; missing columns: {missing}"
            )
    elif path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError(f"JSON artifact must contain an object: {record.key}")
        base_key = _base_artifact_key(record.key)
        if base_key in {"topic_manifest", "theme_manifest", "provider_run_summary"}:
            actual = str(payload.get("schema_version", ""))
            if actual != record.schema_version:
                raise ValueError(f"artifact schema version mismatch: {record.key}")


def _required_columns(key: str, *, run_root: Path | None = None) -> list[str]:
    base_key = _base_artifact_key(key)

    if base_key in {"topic_absolute_messages", "topic_weighted_messages"}:
        from src.topics.topic_inputs import COMMUNITY_MESSAGE_COLUMNS

        return list(COMMUNITY_MESSAGE_COLUMNS)
    if base_key == "topic_matched":
        from src.topics.topic_inputs import MATCHED_COMMUNITY_COLUMNS

        return list(MATCHED_COMMUNITY_COLUMNS)
    if base_key == "topic_partial_matched":
        from src.topics.topic_inputs import PARTIAL_MATCHED_COMMUNITY_COLUMNS

        return list(PARTIAL_MATCHED_COMMUNITY_COLUMNS)
    normalized_key = str(key).strip()
    alias = _PUBLIC_SCHEMA_ALIASES.get(base_key)
    if normalized_key.startswith("theme_clusters_"):
        alias = "theme_cluster_summary"
    elif normalized_key.startswith("theme_cluster_observations_"):
        alias = "theme_cluster_observation"
    elif normalized_key == "theme_canonical_families":
        alias = "theme_canonical_family"
    elif normalized_key in {
        "theme_embeddings_clustering",
        "theme_embeddings_similarity",
    }:
        alias = "theme_embedding"
    elif alias is None and normalized_key.startswith("themes_"):
        alias = "themed_output"
    if alias is None:
        return []
    from src.reporting.output_contract import get_required_columns_by_artifact

    config: Mapping[str, Any] | None = None
    if alias == "network_data" and run_root is not None:
        config_path = run_root / RESOLVED_CONFIG_FILE
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, Mapping):
            raise ValueError(
                f"resolved run config must contain an object: {config_path}"
            )
        config = payload
    return list(get_required_columns_by_artifact(config).get(alias, []))


def _parquet_shape(path: Path) -> tuple[int, list[str]]:
    """Read row count and column names from a Parquet file without loading all data."""
    import pyarrow.parquet as pq  # local import — not on the hot path

    pf = pq.ParquetFile(path)
    rows = pf.metadata.num_rows
    columns = list(pf.schema_arrow.names)
    return rows, columns


def _csv_shape(path: Path) -> tuple[int, list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            columns = next(reader)
        except StopIteration:
            return 0, []
        rows = sum(1 for _ in reader)
    return rows, columns


def _atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    _atomic_write_text(
        path,
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    )


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
