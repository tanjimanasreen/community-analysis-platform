from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.cluster import HDBSCAN
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances

from src.themes.theme_clustering import (
    CANONICALIZATION_CONTRACT_VERSION,
    CANONICALIZATION_LINKAGE,
    CANONICALIZATION_METRIC,
    CANONICALIZATION_REPRESENTATION,
    CANONICALIZATION_SIMILARITY_THRESHOLD,
    DEFAULT_CLUSTERING_METRIC,
    DEFAULT_MIN_CLUSTER_SIZE,
    MonthlyCluster,
    ThemeObservation,
    _canonicalize_monthly_clusters,
    _fit_hdbscan,
    _l2_normalize_embeddings,
    _monthly_clusters,
)

RAW_EUCLIDEAN = "raw_euclidean"
UNIT_EUCLIDEAN = "unit_euclidean"
COSINE = "cosine"

PRODUCTION_BASELINE_VARIANT = "raw_euclidean_eom_ms3"
DIAGNOSTIC_ALLOW_SINGLE_VARIANT = "raw_euclidean_eom_ms3_allow_single"
BENCHMARK_SOURCE_MONTHLY_CLUSTER_CONTRACT_VERSION = "2.2"


@dataclass(frozen=True)
class MonthlyClusteringVariant:
    name: str
    geometry: str
    cluster_selection_method: str
    min_samples: int
    allow_single_cluster: bool = False
    diagnostic_only: bool = False


DEFAULT_MONTHLY_CLUSTERING_VARIANTS: tuple[MonthlyClusteringVariant, ...] = tuple(
    MonthlyClusteringVariant(
        name=f"{geometry}_{selection}_ms{min_samples}",
        geometry=geometry,
        cluster_selection_method=selection,
        min_samples=min_samples,
    )
    for geometry in (RAW_EUCLIDEAN, UNIT_EUCLIDEAN, COSINE)
    for selection in ("eom", "leaf")
    for min_samples in (3, 2)
) + (
    MonthlyClusteringVariant(
        name=DIAGNOSTIC_ALLOW_SINGLE_VARIANT,
        geometry=RAW_EUCLIDEAN,
        cluster_selection_method="eom",
        min_samples=3,
        allow_single_cluster=True,
        diagnostic_only=True,
    ),
)


CLUSTER_OUTPUT_COLUMNS = [
    "variant",
    "period",
    "benchmark_cluster_label",
    "benchmark_representative_theme",
    "observation_count",
    "unique_theme_count",
    "community_pair_count",
    "mean_pairwise_cosine",
    "minimum_pairwise_cosine",
    "mean_representative_to_member_cosine",
    "minimum_representative_to_member_cosine",
    "mean_membership_probability",
    "member_theme_labels",
]

REQUIRED_EVIDENCE_COLUMNS = {
    "period",
    "pair_key",
    "source_general_theme_label",
    "hdbscan_label",
    "membership_probability",
    "is_monthly_noise",
    "monthly_cluster_id",
    "monthly_representative_theme",
}


@dataclass(frozen=True)
class _VariantPeriodResult:
    period: str
    labels: np.ndarray
    probabilities: np.ndarray
    clusters: tuple[MonthlyCluster, ...]
    representative_vectors: Mapping[str, np.ndarray]
    cluster_rows: tuple[dict[str, object], ...]
    membership_rows: tuple[dict[str, object], ...]
    period_metrics: Mapping[str, object]


def load_monthly_clustering_benchmark_data(
    themes_dir: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load persisted Stage-A evidence and clustering vectors without inference."""
    root = Path(themes_dir)
    evidence_candidates = (
        root / "evidence",
        root / "clusters" / "evidence",
    )
    evidence_dir = next(
        (candidate for candidate in evidence_candidates if candidate.is_dir()),
        None,
    )
    if evidence_dir is None:
        checked = ", ".join(str(candidate) for candidate in evidence_candidates)
        raise FileNotFoundError(
            f"theme cluster evidence directory not found; checked: {checked}"
        )

    embedding_candidates = (
        root / "embeddings" / "clustering_general_themes.parquet",
        root / "clusters" / "embeddings" / "clustering_general_themes.parquet",
    )
    embedding_path = next(
        (candidate for candidate in embedding_candidates if candidate.is_file()),
        None,
    )
    if embedding_path is None:
        checked = ", ".join(str(candidate) for candidate in embedding_candidates)
        raise FileNotFoundError(
            f"clustering embedding artifact not found; checked: {checked}"
        )

    evidence_paths = sorted(evidence_dir.glob("*.parquet"))
    if not evidence_paths:
        raise FileNotFoundError(
            f"no monthly cluster evidence artifacts found: {evidence_dir}"
        )

    frames = [pd.read_parquet(path) for path in evidence_paths]
    non_empty = [frame for frame in frames if not frame.empty]
    if not non_empty:
        raise ValueError("monthly clustering benchmark requires theme observations")
    evidence = pd.concat(non_empty, ignore_index=True)
    embeddings = pd.read_parquet(embedding_path)
    return evidence, embeddings


def benchmark_monthly_clustering(
    evidence_frame: pd.DataFrame,
    embedding_frame: pd.DataFrame,
    *,
    variants: Sequence[MonthlyClusteringVariant] = DEFAULT_MONTHLY_CLUSTERING_VARIANTS,
    validate_baseline: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Benchmark monthly HDBSCAN variants against persisted clean Stage-A evidence.

    The function is read-only. It expands exact recorded vectors back to every
    persisted theme occurrence, validates production-baseline fidelity, runs the
    controlled benchmark grid, and audits candidate clusters with cosine cohesion.
    """
    evidence = _validate_evidence(evidence_frame)
    embedding_lookup = _recorded_embedding_lookup(embedding_frame)
    variants = tuple(variants)
    _validate_variants(variants)

    period_inputs: dict[str, tuple[pd.DataFrame, np.ndarray]] = {}
    geometry_diagnostics: dict[str, Mapping[str, object]] = {}
    for period, frame in evidence.groupby("period", sort=True):
        period_frame = frame.reset_index(drop=True)
        raw_matrix = _align_observation_embeddings(period_frame, embedding_lookup)
        period_inputs[str(period)] = (period_frame, raw_matrix)
        geometry_diagnostics[str(period)] = _embedding_geometry_diagnostics(
            period_frame, raw_matrix
        )

    if validate_baseline:
        _assert_production_baseline_fidelity(period_inputs)

    summary_rows: list[dict[str, object]] = []
    period_rows: list[dict[str, object]] = []
    cluster_rows: list[dict[str, object]] = []
    membership_rows: list[dict[str, object]] = []

    for variant in variants:
        results: list[_VariantPeriodResult] = []
        for period in sorted(period_inputs):
            period_frame, raw_matrix = period_inputs[period]
            result = _benchmark_period(
                period,
                period_frame,
                raw_matrix,
                variant=variant,
                geometry_diagnostics=geometry_diagnostics[period],
            )
            results.append(result)
            period_rows.append(
                {
                    "variant": variant.name,
                    "geometry": variant.geometry,
                    "cluster_selection_method": variant.cluster_selection_method,
                    "min_cluster_size": DEFAULT_MIN_CLUSTER_SIZE,
                    "min_samples": variant.min_samples,
                    "allow_single_cluster": variant.allow_single_cluster,
                    "diagnostic_only": variant.diagnostic_only,
                    "source_monthly_cluster_contract_version": (
                        BENCHMARK_SOURCE_MONTHLY_CLUSTER_CONTRACT_VERSION
                    ),
                    **result.period_metrics,
                }
            )
            cluster_rows.extend(result.cluster_rows)
            membership_rows.extend(result.membership_rows)

        stage_b = _stage_b_impact(results)
        summary_rows.append(
            {
                "variant": variant.name,
                "geometry": variant.geometry,
                "cluster_selection_method": variant.cluster_selection_method,
                "min_cluster_size": DEFAULT_MIN_CLUSTER_SIZE,
                "min_samples": variant.min_samples,
                "allow_single_cluster": variant.allow_single_cluster,
                "diagnostic_only": variant.diagnostic_only,
                "source_monthly_cluster_contract_version": (
                    BENCHMARK_SOURCE_MONTHLY_CLUSTER_CONTRACT_VERSION
                ),
                "stage_b_canonicalization_contract_version": (
                    CANONICALIZATION_CONTRACT_VERSION
                ),
                "stage_b_representation": CANONICALIZATION_REPRESENTATION,
                "stage_b_metric": CANONICALIZATION_METRIC,
                "stage_b_linkage": CANONICALIZATION_LINKAGE,
                "stage_b_similarity_threshold": (
                    CANONICALIZATION_SIMILARITY_THRESHOLD
                ),
                **_aggregate_variant_metrics(results),
                **stage_b,
            }
        )

    summary = pd.DataFrame(summary_rows).sort_values("variant", kind="stable")
    periods = pd.DataFrame(period_rows).sort_values(
        ["variant", "period"], kind="stable"
    )
    clusters = pd.DataFrame(cluster_rows, columns=CLUSTER_OUTPUT_COLUMNS).sort_values(
        ["variant", "period", "benchmark_cluster_label"], kind="stable"
    )
    membership = pd.DataFrame(membership_rows).sort_values(
        ["variant", "period", "benchmark_observation_index"], kind="stable"
    )
    return (
        summary.reset_index(drop=True),
        periods.reset_index(drop=True),
        clusters.reset_index(drop=True),
        membership.reset_index(drop=True),
    )


def write_monthly_clustering_benchmark(
    themes_dir: str | Path,
    output_dir: str | Path,
    *,
    variants: Sequence[MonthlyClusteringVariant] = DEFAULT_MONTHLY_CLUSTERING_VARIANTS,
) -> tuple[Path, Path, Path, Path]:
    evidence, embeddings = load_monthly_clustering_benchmark_data(themes_dir)
    summary, periods, clusters, membership = benchmark_monthly_clustering(
        evidence, embeddings, variants=variants
    )

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    summary_path = target / "monthly_clustering_benchmark_summary.csv"
    periods_path = target / "monthly_clustering_benchmark_periods.csv"
    clusters_path = target / "monthly_clustering_benchmark_clusters.csv"
    membership_path = target / "monthly_clustering_benchmark_membership.csv"
    summary.to_csv(summary_path, index=False)
    periods.to_csv(periods_path, index=False)
    clusters.to_csv(clusters_path, index=False)
    membership.to_csv(membership_path, index=False)
    return summary_path, periods_path, clusters_path, membership_path


def _validate_evidence(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(REQUIRED_EVIDENCE_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(
            "cluster evidence is missing benchmark columns: " + ", ".join(missing)
        )
    if frame.empty:
        raise ValueError("monthly clustering benchmark requires theme observations")

    evidence = frame.copy().reset_index(drop=True)
    if evidence["period"].isna().any():
        raise ValueError("cluster evidence period contains missing values")
    if evidence["pair_key"].isna().any():
        raise ValueError("cluster evidence pair_key contains missing values")
    if evidence["source_general_theme_label"].isna().any():
        raise ValueError(
            "cluster evidence source_general_theme_label contains missing values"
        )

    evidence["period"] = evidence["period"].astype(str)
    evidence["pair_key"] = evidence["pair_key"].astype(str)
    evidence["source_general_theme_label"] = evidence[
        "source_general_theme_label"
    ].astype(str)
    if (evidence["period"].str.strip() == "").any():
        raise ValueError("cluster evidence period contains blank values")
    if (evidence["pair_key"].str.strip() == "").any():
        raise ValueError("cluster evidence pair_key contains blank values")
    if (evidence["source_general_theme_label"].str.strip() == "").any():
        raise ValueError(
            "cluster evidence source_general_theme_label contains blank values"
        )
    labels = pd.to_numeric(evidence["hdbscan_label"], errors="raise")
    if labels.isna().any():
        raise ValueError("persisted hdbscan_label contains missing values")
    evidence["hdbscan_label"] = labels.astype(int)

    probabilities = pd.to_numeric(
        evidence["membership_probability"], errors="raise"
    ).to_numpy(dtype=float)
    if not np.isfinite(probabilities).all():
        raise ValueError("persisted membership_probability contains non-finite values")
    if np.any(probabilities < 0.0) or np.any(probabilities > 1.0):
        raise ValueError("persisted membership_probability must be in [0, 1]")
    evidence["membership_probability"] = probabilities

    noise_flags = evidence["is_monthly_noise"]
    if noise_flags.isna().any():
        raise ValueError("persisted is_monthly_noise contains missing values")
    if not all(isinstance(value, (bool, np.bool_)) for value in noise_flags):
        raise ValueError("persisted is_monthly_noise must contain boolean values")
    evidence["is_monthly_noise"] = noise_flags.astype(bool)

    if "monthly_cluster_contract_version" in evidence.columns:
        values = {
            str(value)
            for value in evidence["monthly_cluster_contract_version"].dropna().unique()
        }
        if values and values != {BENCHMARK_SOURCE_MONTHLY_CLUSTER_CONTRACT_VERSION}:
            raise ValueError(
                "monthly clustering benchmark requires benchmark source Stage-A "
                "contract "
                f"{BENCHMARK_SOURCE_MONTHLY_CLUSTER_CONTRACT_VERSION}; "
                f"found {sorted(values)}"
            )
    _validate_optional_single_value(
        evidence,
        "clustering_min_cluster_size",
        DEFAULT_MIN_CLUSTER_SIZE,
    )
    _validate_optional_single_value(
        evidence,
        "clustering_metric",
        DEFAULT_CLUSTERING_METRIC,
    )
    _validate_optional_single_value(evidence, "embedding_normalized", False)
    return evidence


def _validate_optional_single_value(
    frame: pd.DataFrame, column: str, expected: object
) -> None:
    if column not in frame.columns:
        return
    values = frame[column].dropna().unique().tolist()
    if not values:
        return
    if isinstance(expected, str):
        matches = {str(value).casefold() for value in values} == {expected.casefold()}
    else:
        matches = all(value == expected for value in values)
    if not matches:
        raise ValueError(
            f"cluster evidence {column} must be {expected!r}; found {values!r}"
        )


def _validate_variants(variants: Sequence[MonthlyClusteringVariant]) -> None:
    if not variants:
        raise ValueError("monthly clustering benchmark requires at least one variant")
    names: set[str] = set()
    for variant in variants:
        if not variant.name or variant.name in names:
            raise ValueError(
                f"duplicate/empty benchmark variant name: {variant.name!r}"
            )
        names.add(variant.name)
        if variant.geometry not in {RAW_EUCLIDEAN, UNIT_EUCLIDEAN, COSINE}:
            raise ValueError(
                f"variant {variant.name!r} has unsupported geometry "
                f"{variant.geometry!r}"
            )
        if variant.cluster_selection_method not in {"eom", "leaf"}:
            raise ValueError(
                f"variant {variant.name!r} has unsupported cluster selection method"
            )
        if variant.min_samples < 1:
            raise ValueError(f"variant {variant.name!r} min_samples must be at least 1")


def _recorded_embedding_lookup(
    embedding_frame: pd.DataFrame,
) -> dict[str, np.ndarray]:
    required = {"text", "embedding"}
    missing = sorted(required.difference(embedding_frame.columns))
    if missing:
        raise ValueError("embedding artifact is missing columns: " + ", ".join(missing))

    result: dict[str, np.ndarray] = {}
    dimensions: int | None = None
    for row in embedding_frame[["text", "embedding"]].itertuples(index=False):
        text = str(row.text)
        vector = np.asarray(row.embedding, dtype=np.float32)
        if vector.ndim != 1 or vector.size == 0 or not np.isfinite(vector).all():
            raise ValueError(f"invalid recorded embedding for text: {text!r}")
        if dimensions is None:
            dimensions = int(vector.size)
        elif vector.size != dimensions:
            raise ValueError(
                "recorded clustering embeddings have inconsistent dimensions"
            )
        existing = result.get(text)
        if existing is not None and not np.array_equal(existing, vector):
            raise ValueError(
                f"multiple different recorded embeddings found for text: {text!r}"
            )
        result[text] = vector
    if not result:
        raise ValueError("clustering embedding artifact is empty")
    return result


def _align_observation_embeddings(
    evidence: pd.DataFrame,
    embedding_lookup: Mapping[str, np.ndarray],
) -> np.ndarray:
    vectors: list[np.ndarray] = []
    missing: list[str] = []
    for text in evidence["source_general_theme_label"].astype(str):
        vector = embedding_lookup.get(text)
        if vector is None:
            missing.append(text)
        else:
            vectors.append(np.asarray(vector, dtype=np.float32))
    if missing:
        preview = "; ".join(repr(value) for value in missing[:5])
        raise ValueError(
            f"{len(missing)} theme observation(s) are missing from the recorded "
            f"clustering embedding artifact: {preview}"
        )
    return np.vstack(vectors).astype(np.float32, copy=False)


def _assert_production_baseline_fidelity(
    period_inputs: Mapping[str, tuple[pd.DataFrame, np.ndarray]],
) -> None:
    failures: list[str] = []
    for period, (evidence, raw_matrix) in period_inputs.items():
        labels, probabilities = _fit_hdbscan(
            raw_matrix,
            min_cluster_size=DEFAULT_MIN_CLUSTER_SIZE,
            metric=DEFAULT_CLUSTERING_METRIC,
            clusterer_factory=None,
        )
        expected = evidence["hdbscan_label"].to_numpy(dtype=int)
        reason = _partition_mismatch_reason(expected, labels)
        if reason:
            failures.append(f"{period}: {reason}")
            continue

        expected_noise = evidence["is_monthly_noise"].to_numpy(dtype=bool)
        if not np.array_equal(expected_noise, labels < 0):
            count = int(np.sum(expected_noise != (labels < 0)))
            failures.append(
                f"{period}: persisted is_monthly_noise differs for {count} "
                "observation(s)"
            )
            continue

        persisted_probabilities = evidence["membership_probability"].to_numpy(
            dtype=float
        )
        max_probability_delta = float(
            np.max(np.abs(persisted_probabilities - probabilities))
        )
        if max_probability_delta > 5e-7:
            failures.append(
                f"{period}: membership probability max abs diff "
                f"{max_probability_delta:.3g} exceeds 5e-7"
            )
            continue

        observations = _theme_observations(period, evidence)
        reconstructed_clusters = _monthly_clusters(
            period,
            observations,
            raw_matrix,
            labels,
            probabilities,
        )
        cluster_by_observation: dict[int, MonthlyCluster] = {}
        for cluster in reconstructed_clusters:
            for observation_index in cluster.observation_indices:
                cluster_by_observation[int(observation_index)] = cluster

        artifact_reason = _baseline_artifact_mismatch_reason(
            evidence, cluster_by_observation
        )
        if artifact_reason:
            failures.append(f"{period}: {artifact_reason}")

    if failures:
        details = "; ".join(failures[:10])
        raise ValueError(
            "production Stage-A baseline fidelity failed; benchmark aborted: " + details
        )


def _baseline_artifact_mismatch_reason(
    evidence: pd.DataFrame, cluster_by_observation: Mapping[int, MonthlyCluster]
) -> str | None:
    for index, row in evidence.reset_index(drop=True).iterrows():
        cluster = cluster_by_observation.get(index)
        persisted_cluster_id = row["monthly_cluster_id"]
        persisted_representative = row["monthly_representative_theme"]
        if cluster is None:
            if pd.notna(persisted_cluster_id) or pd.notna(persisted_representative):
                return f"noise observation {index} has persisted cluster assignment"
            continue
        if pd.isna(persisted_cluster_id):
            return f"clustered observation {index} is missing monthly_cluster_id"
        if str(persisted_cluster_id) != cluster.cluster_id:
            return f"monthly_cluster_id differs for observation {index}"
        if pd.isna(persisted_representative):
            return f"clustered observation {index} is missing monthly representative"
        if str(persisted_representative) != cluster.representative_theme:
            return f"monthly representative differs for observation {index}"
    return None


def _partition_mismatch_reason(expected: np.ndarray, actual: np.ndarray) -> str | None:
    expected = np.asarray(expected, dtype=int)
    actual = np.asarray(actual, dtype=int)
    if expected.shape != actual.shape:
        return f"label shape mismatch {expected.shape} != {actual.shape}"
    if not np.array_equal(expected < 0, actual < 0):
        count = int(np.sum((expected < 0) != (actual < 0)))
        return f"noise membership differs for {count} observation(s)"

    admitted = np.flatnonzero(expected >= 0)
    if admitted.size:
        expected_same = expected[admitted, None] == expected[admitted]
        actual_same = actual[admitted, None] == actual[admitted]
        if not np.array_equal(expected_same, actual_same):
            return "non-noise cluster partition differs"
    return None


def _benchmark_period(
    period: str,
    evidence: pd.DataFrame,
    raw_matrix: np.ndarray,
    *,
    variant: MonthlyClusteringVariant,
    geometry_diagnostics: Mapping[str, object],
) -> _VariantPeriodResult:
    matrix = _geometry_matrix(raw_matrix, variant.geometry)
    labels, probabilities = _fit_variant(matrix, variant)
    clusters, representative_vectors, cluster_rows = _cluster_diagnostics(
        period,
        evidence,
        raw_matrix,
        labels,
        probabilities,
        variant_name=variant.name,
    )
    representative_by_label = {
        cluster.hdbscan_label: cluster.representative_theme for cluster in clusters
    }
    embedding_fingerprints = _recorded_embedding_fingerprints(raw_matrix)
    embedding_group_sizes = _embedding_group_sizes(embedding_fingerprints)
    identical_embedding_metrics = _identical_embedding_assignment_metrics(
        embedding_fingerprints, labels
    )

    membership_rows: list[dict[str, object]] = []
    for index, row in evidence.reset_index(drop=True).iterrows():
        label = int(labels[index])
        membership_rows.append(
            {
                "variant": variant.name,
                "period": period,
                "benchmark_observation_index": index,
                "pair_key": _optional_text(row, "pair_key"),
                "source_index": _optional_integer(row, "source_index"),
                "source_general_theme_label": str(row["source_general_theme_label"]),
                "recorded_embedding_sha256": embedding_fingerprints[index],
                "recorded_embedding_group_size": embedding_group_sizes[
                    embedding_fingerprints[index]
                ],
                "benchmark_cluster_label": label,
                "is_noise": label < 0,
                "membership_probability": float(probabilities[index]),
                "benchmark_representative_theme": (
                    representative_by_label.get(label) if label >= 0 else None
                ),
            }
        )

    metrics = {
        "period": period,
        **_period_cluster_metrics(
            labels,
            probabilities,
            cluster_rows,
            representative_vectors=representative_vectors,
        ),
        **identical_embedding_metrics,
        **geometry_diagnostics,
    }
    return _VariantPeriodResult(
        period=period,
        labels=labels,
        probabilities=probabilities,
        clusters=tuple(clusters),
        representative_vectors=representative_vectors,
        cluster_rows=tuple(cluster_rows),
        membership_rows=tuple(membership_rows),
        period_metrics=metrics,
    )


def _geometry_matrix(raw_matrix: np.ndarray, geometry: str) -> np.ndarray:
    matrix = np.asarray(raw_matrix, dtype=np.float64)
    if not np.isfinite(matrix).all() or matrix.ndim != 2 or matrix.shape[1] == 0:
        raise ValueError("monthly clustering benchmark embedding matrix is invalid")
    if geometry == RAW_EUCLIDEAN or geometry == COSINE:
        if geometry == COSINE:
            _require_nonzero_rows(matrix, context="cosine benchmark embeddings")
        return matrix.copy()
    if geometry == UNIT_EUCLIDEAN:
        return _l2_normalize_embeddings(
            matrix,
            context="unit-normalized benchmark embeddings",
        )
    raise ValueError(f"unsupported geometry: {geometry!r}")


def _fit_variant(
    matrix: np.ndarray, variant: MonthlyClusteringVariant
) -> tuple[np.ndarray, np.ndarray]:
    count = matrix.shape[0]
    if count < DEFAULT_MIN_CLUSTER_SIZE or count < variant.min_samples:
        return np.full(count, -1, dtype=int), np.zeros(count, dtype=float)

    if (
        variant.name == PRODUCTION_BASELINE_VARIANT
        and variant.geometry == RAW_EUCLIDEAN
        and variant.cluster_selection_method == "eom"
        and variant.min_samples == DEFAULT_MIN_CLUSTER_SIZE + 1
        and not variant.allow_single_cluster
    ):
        return _fit_hdbscan(
            matrix,
            min_cluster_size=DEFAULT_MIN_CLUSTER_SIZE,
            metric=DEFAULT_CLUSTERING_METRIC,
            clusterer_factory=None,
            cluster_selection_method="eom",
            allow_single_cluster=False,
        )

    metric = "cosine" if variant.geometry == COSINE else "euclidean"
    algorithm = "brute" if metric == "cosine" else "auto"
    clusterer = HDBSCAN(
        min_cluster_size=DEFAULT_MIN_CLUSTER_SIZE,
        min_samples=variant.min_samples,
        metric=metric,
        algorithm=algorithm,
        cluster_selection_method=variant.cluster_selection_method,
        allow_single_cluster=variant.allow_single_cluster,
        copy=True,
    )
    clusterer.fit(matrix)
    labels = np.asarray(clusterer.labels_, dtype=int)
    probabilities = np.asarray(clusterer.probabilities_, dtype=float)
    if labels.shape != (count,) or probabilities.shape != (count,):
        raise RuntimeError("benchmark HDBSCAN returned malformed labels/probabilities")
    return labels, probabilities


def _theme_observations(
    period: str, evidence: pd.DataFrame
) -> list[ThemeObservation]:
    observations: list[ThemeObservation] = []
    for index, (_, row) in enumerate(evidence.iterrows()):
        source_index = _optional_integer(row, "source_index")
        observations.append(
            ThemeObservation(
                period=period,
                pair_key=str(row["pair_key"]),
                absolute_community=_optional_text(row, "absolute_community"),
                weighted_community=_optional_text(row, "weighted_community"),
                label=str(row["source_general_theme_label"]),
                keywords=(),
                source_index=source_index if source_index is not None else index,
            )
        )
    return observations


def _cluster_diagnostics(
    period: str,
    evidence: pd.DataFrame,
    raw_matrix: np.ndarray,
    labels: np.ndarray,
    probabilities: np.ndarray,
    *,
    variant_name: str,
) -> tuple[list[MonthlyCluster], dict[str, np.ndarray], list[dict[str, object]]]:
    observations = _theme_observations(period, evidence)
    clusters = _monthly_clusters(
        period,
        observations,
        raw_matrix,
        labels,
        probabilities,
    )

    representative_vectors: dict[str, np.ndarray] = {}
    rows: list[dict[str, object]] = []
    for cluster in clusters:
        indices = np.asarray(cluster.observation_indices, dtype=int)
        labels_in_cluster = [observations[index].label for index in indices]
        representative_index = next(
            int(index)
            for index in indices
            if observations[int(index)].label == cluster.representative_theme
        )
        representative_vectors[cluster.cluster_id] = np.asarray(
            raw_matrix[representative_index], dtype=np.float64
        )

        cluster_matrix = raw_matrix[indices]
        mean_pairwise, min_pairwise = _pairwise_cosine_metrics(cluster_matrix)
        representative_vector = raw_matrix[representative_index]
        representative_similarities = cosine_similarity(
            np.asarray(representative_vector, dtype=np.float64).reshape(1, -1),
            cluster_matrix,
        )[0]
        community_pairs = {
            observations[index].pair_key for index in indices
        }
        unique_labels = sorted(set(labels_in_cluster), key=str.casefold)
        rows.append(
            {
                "variant": variant_name,
                "period": period,
                "benchmark_cluster_label": cluster.hdbscan_label,
                "benchmark_representative_theme": cluster.representative_theme,
                "observation_count": len(indices),
                "unique_theme_count": len(unique_labels),
                "community_pair_count": len(community_pairs),
                "mean_pairwise_cosine": mean_pairwise,
                "minimum_pairwise_cosine": min_pairwise,
                "mean_representative_to_member_cosine": float(
                    np.mean(representative_similarities)
                ),
                "minimum_representative_to_member_cosine": float(
                    np.min(representative_similarities)
                ),
                "mean_membership_probability": float(
                    np.mean(probabilities[indices])
                ),
                "member_theme_labels": json.dumps(unique_labels, ensure_ascii=False),
            }
        )
    return clusters, representative_vectors, rows


def _recorded_embedding_fingerprints(raw_matrix: np.ndarray) -> list[str]:
    matrix = np.asarray(raw_matrix, dtype=np.float32)
    if matrix.ndim != 2:
        raise ValueError("recorded embedding matrix must be two-dimensional")
    return [
        hashlib.sha256(
            np.ascontiguousarray(vector, dtype=np.float32).tobytes(order="C")
        ).hexdigest()
        for vector in matrix
    ]


def _embedding_group_sizes(fingerprints: Sequence[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for fingerprint in fingerprints:
        counts[fingerprint] = counts.get(fingerprint, 0) + 1
    return counts


def _identical_embedding_assignment_metrics(
    fingerprints: Sequence[str], labels: np.ndarray
) -> dict[str, object]:
    if len(fingerprints) != len(labels):
        raise ValueError("embedding fingerprints and labels must be row-aligned")

    groups: dict[str, list[int]] = {}
    for index, fingerprint in enumerate(fingerprints):
        groups.setdefault(fingerprint, []).append(index)

    duplicate_groups = [indices for indices in groups.values() if len(indices) > 1]
    non_noise_split_groups: list[list[int]] = []
    noise_boundary_split_groups: list[list[int]] = []
    max_non_noise_clusters = 0
    for indices in duplicate_groups:
        group_labels = np.asarray(labels[indices], dtype=int)
        non_noise = np.unique(group_labels[group_labels >= 0])
        max_non_noise_clusters = max(max_non_noise_clusters, int(non_noise.size))
        if non_noise.size > 1:
            non_noise_split_groups.append(indices)
        if np.any(group_labels < 0) and np.any(group_labels >= 0):
            noise_boundary_split_groups.append(indices)

    return {
        "identical_embedding_group_count": len(duplicate_groups),
        "identical_embedding_observation_count": sum(
            len(indices) for indices in duplicate_groups
        ),
        "identical_embedding_non_noise_split_group_count": len(
            non_noise_split_groups
        ),
        "identical_embedding_non_noise_split_observation_count": sum(
            len(indices) for indices in non_noise_split_groups
        ),
        "identical_embedding_noise_boundary_split_group_count": len(
            noise_boundary_split_groups
        ),
        "identical_embedding_noise_boundary_split_observation_count": sum(
            len(indices) for indices in noise_boundary_split_groups
        ),
        "identical_embedding_max_non_noise_cluster_count": max_non_noise_clusters,
        "identical_embedding_non_noise_consistency_pass": (
            len(non_noise_split_groups) == 0
        ),
    }


def _period_cluster_metrics(
    labels: np.ndarray,
    probabilities: np.ndarray,
    cluster_rows: Sequence[Mapping[str, object]],
    *,
    representative_vectors: Mapping[str, np.ndarray],
) -> dict[str, object]:
    observation_count = len(labels)
    noise_count = int(np.sum(labels < 0))
    clustered_count = observation_count - noise_count
    cluster_sizes = [int(row["observation_count"]) for row in cluster_rows]
    largest = max(cluster_sizes) if cluster_sizes else 0
    clustered_probabilities = probabilities[labels >= 0]

    return {
        "observation_count": observation_count,
        "cluster_count": len(cluster_sizes),
        "noise_count": noise_count,
        "noise_rate": (
            noise_count / observation_count if observation_count else math.nan
        ),
        "clustered_observation_count": clustered_count,
        "largest_cluster_size": largest,
        "largest_cluster_share_all_observations": (
            largest / observation_count if observation_count else math.nan
        ),
        "largest_cluster_share_clustered_observations": (
            largest / clustered_count if clustered_count else math.nan
        ),
        "median_cluster_size": (
            float(np.median(cluster_sizes)) if cluster_sizes else math.nan
        ),
        "mean_cluster_size": (
            float(np.mean(cluster_sizes)) if cluster_sizes else math.nan
        ),
        "mean_membership_probability": (
            float(np.mean(clustered_probabilities))
            if clustered_probabilities.size
            else math.nan
        ),
        "minimum_membership_probability": (
            float(np.min(clustered_probabilities))
            if clustered_probabilities.size
            else math.nan
        ),
        "size_2_cluster_count": sum(size == 2 for size in cluster_sizes),
        "size_3_cluster_count": sum(size == 3 for size in cluster_sizes),
        "cluster_count_per_observation": (
            len(cluster_sizes) / observation_count if observation_count else math.nan
        ),
        "weighted_mean_cluster_pairwise_cosine": _weighted_cluster_metric(
            cluster_rows, "mean_pairwise_cosine"
        ),
        "worst_cluster_mean_pairwise_cosine": _minimum_cluster_metric(
            cluster_rows, "mean_pairwise_cosine"
        ),
        "worst_cluster_minimum_pairwise_cosine": _minimum_cluster_metric(
            cluster_rows, "minimum_pairwise_cosine"
        ),
        "max_intercluster_representative_cosine": (
            _max_intercluster_representative_cosine(representative_vectors)
        ),
    }


def _aggregate_variant_metrics(
    results: Sequence[_VariantPeriodResult],
) -> dict[str, object]:
    observation_count = sum(len(result.labels) for result in results)
    noise_count = sum(int(np.sum(result.labels < 0)) for result in results)
    clustered_count = observation_count - noise_count
    all_clusters = [row for result in results for row in result.cluster_rows]
    period_metrics = [result.period_metrics for result in results]
    cluster_sizes = [int(row["observation_count"]) for row in all_clusters]
    all_cluster_probabilities = np.concatenate(
        [result.probabilities[result.labels >= 0] for result in results]
    )
    return {
        "period_count": len(results),
        "observation_count": observation_count,
        "cluster_count": len(all_clusters),
        "noise_count": noise_count,
        "noise_rate": (
            noise_count / observation_count if observation_count else math.nan
        ),
        "clustered_observation_count": clustered_count,
        "mean_period_noise_rate": _nanmean(
            [float(row["noise_rate"]) for row in period_metrics]
        ),
        "max_period_noise_rate": _nanmax(
            [float(row["noise_rate"]) for row in period_metrics]
        ),
        "max_period_largest_cluster_share_all_observations": _nanmax(
            [
                float(row["largest_cluster_share_all_observations"])
                for row in period_metrics
            ]
        ),
        "max_period_largest_cluster_share_clustered_observations": _nanmax(
            [
                float(row["largest_cluster_share_clustered_observations"])
                for row in period_metrics
            ]
        ),
        "largest_cluster_size": max(cluster_sizes) if cluster_sizes else 0,
        "median_cluster_size": (
            float(np.median(cluster_sizes)) if cluster_sizes else math.nan
        ),
        "mean_cluster_size": (
            float(np.mean(cluster_sizes)) if cluster_sizes else math.nan
        ),
        "mean_membership_probability": (
            float(np.mean(all_cluster_probabilities))
            if all_cluster_probabilities.size
            else math.nan
        ),
        "minimum_membership_probability": (
            float(np.min(all_cluster_probabilities))
            if all_cluster_probabilities.size
            else math.nan
        ),
        "size_2_cluster_count": sum(size == 2 for size in cluster_sizes),
        "size_3_cluster_count": sum(size == 3 for size in cluster_sizes),
        "cluster_count_per_observation": (
            len(all_clusters) / observation_count if observation_count else math.nan
        ),
        "weighted_mean_cluster_pairwise_cosine": _weighted_cluster_metric(
            all_clusters, "mean_pairwise_cosine"
        ),
        "worst_cluster_mean_pairwise_cosine": _minimum_cluster_metric(
            all_clusters, "mean_pairwise_cosine"
        ),
        "worst_cluster_minimum_pairwise_cosine": _minimum_cluster_metric(
            all_clusters, "minimum_pairwise_cosine"
        ),
        "max_period_intercluster_representative_cosine": _nanmax(
            [
                float(row["max_intercluster_representative_cosine"])
                for row in period_metrics
            ]
        ),
        "identical_embedding_group_count": sum(
            int(row["identical_embedding_group_count"]) for row in period_metrics
        ),
        "identical_embedding_observation_count": sum(
            int(row["identical_embedding_observation_count"])
            for row in period_metrics
        ),
        "identical_embedding_non_noise_split_group_count": sum(
            int(row["identical_embedding_non_noise_split_group_count"])
            for row in period_metrics
        ),
        "identical_embedding_non_noise_split_observation_count": sum(
            int(row["identical_embedding_non_noise_split_observation_count"])
            for row in period_metrics
        ),
        "identical_embedding_noise_boundary_split_group_count": sum(
            int(row["identical_embedding_noise_boundary_split_group_count"])
            for row in period_metrics
        ),
        "identical_embedding_noise_boundary_split_observation_count": sum(
            int(row["identical_embedding_noise_boundary_split_observation_count"])
            for row in period_metrics
        ),
        "identical_embedding_max_non_noise_cluster_count": max(
            (
                int(row["identical_embedding_max_non_noise_cluster_count"])
                for row in period_metrics
            ),
            default=0,
        ),
        "identical_embedding_non_noise_consistency_pass": all(
            bool(row["identical_embedding_non_noise_consistency_pass"])
            for row in period_metrics
        ),
    }


def _stage_b_impact(results: Sequence[_VariantPeriodResult]) -> dict[str, object]:
    monthly_clusters = [cluster for result in results for cluster in result.clusters]
    if not monthly_clusters:
        return {
            "stage_b_monthly_cluster_count": 0,
            "stage_b_canonical_family_count": 0,
            "stage_b_largest_family_cluster_share": math.nan,
            "stage_b_largest_family_observation_share": math.nan,
            "stage_b_minimum_representative_family_cosine": math.nan,
        }

    normalized_vectors: dict[str, np.ndarray] = {}
    observation_counts: dict[str, int] = {}
    for result in results:
        for cluster in result.clusters:
            vector = np.asarray(
                result.representative_vectors[cluster.cluster_id], dtype=np.float64
            )
            norm = float(np.linalg.norm(vector))
            if not math.isfinite(norm) or norm <= 0.0:
                raise ValueError(
                    "cannot L2-normalize benchmark representative "
                    f"{cluster.cluster_id!r}"
                )
            normalized_vectors[cluster.cluster_id] = vector / norm
            observation_counts[cluster.cluster_id] = len(cluster.observation_indices)

    families, by_cluster = _canonicalize_monthly_clusters(
        monthly_clusters,
        normalized_representative_embeddings=normalized_vectors,
    )
    family_cluster_counts: dict[str, int] = {}
    family_observation_counts: dict[str, int] = {}
    for cluster in monthly_clusters:
        family = by_cluster[cluster.cluster_id]
        family_cluster_counts[family.canonical_theme_id] = (
            family_cluster_counts.get(family.canonical_theme_id, 0) + 1
        )
        family_observation_counts[family.canonical_theme_id] = (
            family_observation_counts.get(family.canonical_theme_id, 0)
            + observation_counts[cluster.cluster_id]
        )

    total_observations = sum(observation_counts.values())
    min_family_cosines: list[float] = []
    for family in families:
        if len(family.monthly_cluster_ids) <= 1:
            continue
        matrix = np.vstack(
            [
                normalized_vectors[cluster_id]
                for cluster_id in family.monthly_cluster_ids
            ]
        )
        _, minimum = _pairwise_cosine_metrics(matrix)
        min_family_cosines.append(minimum)

    return {
        "stage_b_monthly_cluster_count": len(monthly_clusters),
        "stage_b_canonical_family_count": len(families),
        "stage_b_largest_family_cluster_share": (
            max(family_cluster_counts.values()) / len(monthly_clusters)
            if family_cluster_counts
            else math.nan
        ),
        "stage_b_largest_family_observation_share": (
            max(family_observation_counts.values()) / total_observations
            if family_observation_counts and total_observations
            else math.nan
        ),
        "stage_b_minimum_representative_family_cosine": (
            min(min_family_cosines) if min_family_cosines else math.nan
        ),
    }


def _embedding_geometry_diagnostics(
    evidence: pd.DataFrame, raw_matrix: np.ndarray
) -> dict[str, object]:
    matrix = np.asarray(raw_matrix, dtype=np.float64)
    norms = np.linalg.norm(matrix, axis=1)
    top1_cosine, top2_cosine = _nearest_neighbor_cosines(matrix)
    top1_euclidean, top2_euclidean = _nearest_neighbor_euclidean(matrix)
    production_clustered = evidence["hdbscan_label"].to_numpy(dtype=int) >= 0
    return {
        "embedding_norm_min": float(np.min(norms)),
        "embedding_norm_mean": float(np.mean(norms)),
        "embedding_norm_median": float(np.median(norms)),
        "embedding_norm_max": float(np.max(norms)),
        "embedding_norm_std": float(np.std(norms)),
        "mean_top1_cosine_similarity": _nanmean(top1_cosine),
        "mean_top2_cosine_similarity": _nanmean(top2_cosine),
        "mean_top1_euclidean_distance": _nanmean(top1_euclidean),
        "mean_top2_euclidean_distance": _nanmean(top2_euclidean),
        "production_clustered_mean_top1_cosine_similarity": _masked_nanmean(
            top1_cosine, production_clustered
        ),
        "production_noise_mean_top1_cosine_similarity": _masked_nanmean(
            top1_cosine, ~production_clustered
        ),
        "production_clustered_mean_top2_cosine_similarity": _masked_nanmean(
            top2_cosine, production_clustered
        ),
        "production_noise_mean_top2_cosine_similarity": _masked_nanmean(
            top2_cosine, ~production_clustered
        ),
        "production_clustered_mean_top1_euclidean_distance": _masked_nanmean(
            top1_euclidean, production_clustered
        ),
        "production_noise_mean_top1_euclidean_distance": _masked_nanmean(
            top1_euclidean, ~production_clustered
        ),
        "production_clustered_mean_top2_euclidean_distance": _masked_nanmean(
            top2_euclidean, production_clustered
        ),
        "production_noise_mean_top2_euclidean_distance": _masked_nanmean(
            top2_euclidean, ~production_clustered
        ),
    }


def _nearest_neighbor_cosines(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    count = len(matrix)
    top1 = np.full(count, np.nan, dtype=float)
    top2 = np.full(count, np.nan, dtype=float)
    if count <= 1:
        return top1, top2
    similarities = cosine_similarity(matrix)
    np.fill_diagonal(similarities, -np.inf)
    ordered = np.sort(similarities, axis=1)[:, ::-1]
    top1[:] = ordered[:, 0]
    if count > 2:
        top2[:] = ordered[:, 1]
    return top1, top2


def _nearest_neighbor_euclidean(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    count = len(matrix)
    top1 = np.full(count, np.nan, dtype=float)
    top2 = np.full(count, np.nan, dtype=float)
    if count <= 1:
        return top1, top2
    distances = euclidean_distances(matrix)
    np.fill_diagonal(distances, np.inf)
    ordered = np.sort(distances, axis=1)
    top1[:] = ordered[:, 0]
    if count > 2:
        top2[:] = ordered[:, 1]
    return top1, top2


def _pairwise_cosine_metrics(matrix: np.ndarray) -> tuple[float, float]:
    if len(matrix) <= 1:
        return 1.0, 1.0
    similarities = cosine_similarity(matrix)
    upper = similarities[np.triu_indices(len(matrix), k=1)]
    return float(np.mean(upper)), float(np.min(upper))


def _weighted_cluster_metric(
    cluster_rows: Sequence[Mapping[str, object]], column: str
) -> float:
    if not cluster_rows:
        return math.nan
    values = np.asarray([float(row[column]) for row in cluster_rows], dtype=float)
    weights = np.asarray(
        [int(row["observation_count"]) for row in cluster_rows], dtype=float
    )
    return float(np.average(values, weights=weights))


def _minimum_cluster_metric(
    cluster_rows: Sequence[Mapping[str, object]], column: str
) -> float:
    if not cluster_rows:
        return math.nan
    return min(float(row[column]) for row in cluster_rows)


def _max_intercluster_representative_cosine(
    representative_vectors: Mapping[str, np.ndarray],
) -> float:
    if len(representative_vectors) < 2:
        return math.nan
    matrix = np.vstack(
        [
            np.asarray(vector, dtype=np.float64)
            for vector in representative_vectors.values()
        ]
    )
    similarities = cosine_similarity(matrix)
    upper = similarities[np.triu_indices(len(matrix), k=1)]
    return float(np.max(upper))


def _require_nonzero_rows(matrix: np.ndarray, *, context: str) -> None:
    norms = np.linalg.norm(matrix, axis=1)
    if not np.isfinite(norms).all() or np.any(norms <= 0.0):
        raise ValueError(f"{context} contain zero/non-finite vectors")


def _optional_text(row: pd.Series, column: str) -> str | None:
    if column not in row.index or pd.isna(row[column]):
        return None
    value = str(row[column])
    return value if value else None


def _optional_integer(row: pd.Series, column: str) -> int | None:
    if column not in row.index or pd.isna(row[column]):
        return None
    return int(row[column])


def _nanmean(values: Sequence[float] | np.ndarray) -> float:
    array = np.asarray(values, dtype=float)
    finite = array[np.isfinite(array)]
    return float(np.mean(finite)) if finite.size else math.nan


def _nanmax(values: Sequence[float] | np.ndarray) -> float:
    array = np.asarray(values, dtype=float)
    finite = array[np.isfinite(array)]
    return float(np.max(finite)) if finite.size else math.nan


def _masked_nanmean(values: np.ndarray, mask: np.ndarray) -> float:
    selected = np.asarray(values, dtype=float)[np.asarray(mask, dtype=bool)]
    return _nanmean(selected)
