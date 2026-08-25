from __future__ import annotations

import ast
import hashlib
import json
import logging
import math
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence

import numpy as np
import pandas as pd
import sklearn
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity

from src.themes.theme_inputs import _parse_list

MONTHLY_CLUSTER_CONTRACT_VERSION = "3.0"
CANONICALIZATION_CONTRACT_VERSION = "4.0"
DEFAULT_CLUSTERING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_MIN_CLUSTER_SIZE = 2
DEFAULT_CLUSTERING_METRIC = "euclidean"
MONTHLY_CLUSTERING_INPUT_NORMALIZED = True
MONTHLY_CLUSTER_SELECTION_METHOD = "leaf"
MONTHLY_CLUSTER_ALLOW_SINGLE_CLUSTER = False
HDBSCAN_IMPLEMENTATION = "sklearn.cluster.HDBSCAN"
HDBSCAN_VERSION = sklearn.__version__
CANONICALIZATION_REPRESENTATION = "monthly_semantic_representative_l2_normalized"
CANONICALIZATION_GROUPING_METHOD = "agglomerative"
CANONICALIZATION_IMPLEMENTATION = "sklearn.cluster.AgglomerativeClustering"
CANONICALIZATION_METRIC = "cosine"
CANONICALIZATION_LINKAGE = "complete"
CANONICALIZATION_SIMILARITY_THRESHOLD = 0.65
CANONICALIZATION_DISTANCE_THRESHOLD = 1.0 - CANONICALIZATION_SIMILARITY_THRESHOLD

logger = logging.getLogger(__name__)

_AMBIGUOUS_GENERAL_THEME_SERIALIZATION = "ambiguous_general_theme_serialization"
_MISSING_GENERAL_THEME = "missing_general_theme"


class EmbeddingModel(Protocol):
    def encode(self, sentences: Sequence[str]) -> np.ndarray: ...


class DeterministicThemeEmbeddingModel:
    """Offline-only embedding stub used by tests and explicit mock runs."""

    def encode(self, sentences: Sequence[str]) -> np.ndarray:
        vectors: list[list[float]] = []
        for sentence in sentences:
            normalized = _normalized_label(str(sentence))
            tokens = normalized.split()
            buckets = [0.0] * 16
            for token in tokens:
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                buckets[digest[0] % len(buckets)] += 1.0
            buckets.append(float(len(tokens)))
            vectors.append(buckets)
        return np.asarray(vectors, dtype=np.float32)


def build_clustering_embedder(
    config: Mapping[str, Any] | None = None,
) -> EmbeddingModel:
    """Build the configured clustering embedding provider without model downloads."""
    from src.config.settings import (
        get_clustering_settings,
        get_clustering_tei_client_settings,
    )
    from src.themes.tei_client import TEIClient

    theme = (config or {}).get("theme", {})
    theme = theme if isinstance(theme, Mapping) else {}
    runtime = get_clustering_settings()
    provider = str(theme.get("clustering_provider", runtime.provider)).strip().lower()
    if provider == "mock":
        return DeterministicThemeEmbeddingModel()
    if provider != "tei":
        raise ValueError(f"unsupported theme clustering provider: {provider!r}")

    settings = get_clustering_tei_client_settings()
    configured_model = str(theme.get("clustering_model", settings.model_id)).strip()
    configured_revision = str(
        theme.get("clustering_model_revision", settings.revision)
    ).strip()
    if configured_model != settings.model_id:
        raise ValueError(
            "theme clustering model does not match the TEI clustering profile: "
            f"config={configured_model!r}, tei={settings.model_id!r}"
        )
    if configured_revision != settings.revision:
        raise ValueError(
            "theme clustering model revision does not match the TEI clustering profile: "
            f"config={configured_revision!r}, tei={settings.revision!r}"
        )
    return TEIClient(
        base_url=str(settings.base_url),
        api_key=settings.api_key.get_secret_value() if settings.api_key else None,
        client_batch_size=settings.client_batch_size,
        timeout_seconds=settings.timeout_seconds,
        normalize=False,
    )


@dataclass(frozen=True)
class ThemeObservation:
    period: str
    pair_key: str
    absolute_community: str | None
    weighted_community: str | None
    label: str
    keywords: tuple[str, ...]
    source_index: int

    @property
    def source_key(self) -> str:
        return f"{self.pair_key}|{self.label}"


@dataclass(frozen=True)
class MonthlyCluster:
    period: str
    cluster_id: str
    hdbscan_label: int
    representative_theme: str
    observation_indices: tuple[int, ...]
    mean_membership_probability: float


@dataclass(frozen=True)
class CanonicalFamily:
    canonical_theme_id: str
    canonical_label: str
    monthly_cluster_ids: tuple[str, ...]
    monthly_representatives: tuple[str, ...]
    periods: tuple[str, ...]
    stage_b_cluster_label: int
    hdbscan_label: int | None
    singleton_canonical_theme: bool


def build_clustered_theme_artifacts(
    themed_monthly: Mapping[str, pd.DataFrame],
    *,
    year: str | int,
    embedder: EmbeddingModel,
    clustering_model: str = DEFAULT_CLUSTERING_MODEL,
    min_cluster_size: int = DEFAULT_MIN_CLUSTER_SIZE,
    canonicalization_min_cluster_size: int | None = None,
    metric: str = DEFAULT_CLUSTERING_METRIC,
    clusterer_factory: Callable[..., Any] | None = None,
    source_artifact_hashes: Mapping[str, str] | None = None,
    embedding_provider: str = "tei",
    embedding_model_revision: str = "",
    embedding_contract_version: str = "",
    embedding_dtype: str = "float32",
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], pd.DataFrame]:
    """Cluster raw general themes monthly, then canonicalize representatives.

    The input frames are never mutated. Only ``general_theme_names`` supplies
    clustering labels; missing general labels are retained as diagnostics rather
    than falling back to IF/WIF labels.
    """
    if min_cluster_size < 2:
        raise ValueError("theme clustering min_cluster_size must be at least 2")
    canonical_min = canonicalization_min_cluster_size or min_cluster_size
    if canonical_min < 2:
        raise ValueError("theme canonicalization min_cluster_size must be at least 2")

    periods = _periods(themed_monthly, year)
    observations_by_period: dict[str, list[ThemeObservation]] = {}
    excluded_missing_general: dict[str, int] = {}
    excluded_ambiguous_general: dict[str, int] = {}
    denominator_pairs: dict[str, set[str]] = {}
    monthly_clusters: dict[str, list[MonthlyCluster]] = {}
    monthly_cluster_representations: dict[str, np.ndarray] = {}
    membership_probabilities: dict[str, np.ndarray] = {}
    monthly_labels: dict[str, np.ndarray] = {}

    for month, frame in themed_monthly.items():
        period = periods[month]
        (
            observations,
            excluded_missing,
            excluded_ambiguous,
            themed_pairs,
        ) = _extract_general_theme_observations_with_diagnostics(frame, period=period)
        observations_by_period[period] = observations
        excluded_missing_general[period] = excluded_missing
        excluded_ambiguous_general[period] = excluded_ambiguous
        denominator_pairs[period] = themed_pairs
        if not observations:
            monthly_clusters[period] = []
            membership_probabilities[period] = np.empty((0,), dtype=float)
            monthly_labels[period] = np.empty((0,), dtype=int)
            continue

        embeddings = _validate_embeddings(
            embedder.encode([obs.label for obs in observations]), len(observations)
        )
        clustering_embeddings = _l2_normalize_embeddings(
            embeddings,
            context="monthly Stage-A clustering embeddings",
        )
        labels, probabilities = _fit_hdbscan(
            clustering_embeddings,
            min_cluster_size=min_cluster_size,
            metric=metric,
            clusterer_factory=clusterer_factory,
            cluster_selection_method=MONTHLY_CLUSTER_SELECTION_METHOD,
            allow_single_cluster=MONTHLY_CLUSTER_ALLOW_SINGLE_CLUSTER,
        )
        membership_probabilities[period] = probabilities
        monthly_labels[period] = labels
        monthly_clusters[period] = _monthly_clusters(
            period,
            observations,
            embeddings,
            labels,
            probabilities,
        )
        monthly_cluster_representations.update(
            _normalized_representative_embeddings(
                monthly_clusters[period],
                observations=observations,
                embeddings=embeddings,
            )
        )

    all_monthly_clusters = [
        cluster
        for period in sorted(monthly_clusters)
        for cluster in monthly_clusters[period]
    ]
    families, family_by_cluster = _canonicalize_monthly_clusters(
        all_monthly_clusters,
        normalized_representative_embeddings=monthly_cluster_representations,
    )

    monthly_summary_frames: dict[str, pd.DataFrame] = {}
    monthly_observation_frames: dict[str, pd.DataFrame] = {}
    source_artifact_hashes = source_artifact_hashes or {}

    for period in sorted(observations_by_period):
        observations = observations_by_period[period]
        clusters = monthly_clusters[period]
        labels = monthly_labels[period]
        probabilities = membership_probabilities[period]
        monthly_summary_frames[period] = _monthly_summary_frame(
            period=period,
            observations=observations,
            clusters=clusters,
            families=family_by_cluster,
            denominator_pairs=denominator_pairs[period],
            excluded_missing_general=excluded_missing_general[period],
            excluded_ambiguous_general=excluded_ambiguous_general[period],
            monthly_noise_observation_count=int(np.sum(monthly_labels[period] == -1)),
            clustering_model=clustering_model,
            min_cluster_size=min_cluster_size,
            canonicalization_min_cluster_size=canonical_min,
            metric=metric,
            source_artifact_sha256=source_artifact_hashes.get(period),
            embedding_provider=embedding_provider,
            embedding_model_revision=embedding_model_revision,
            embedding_contract_version=embedding_contract_version,
            embedding_dtype=embedding_dtype,
        )
        monthly_observation_frames[period] = _observation_frame(
            observations=observations,
            labels=labels,
            probabilities=probabilities,
            clusters=clusters,
            family_by_cluster=family_by_cluster,
            clustering_model=clustering_model,
            min_cluster_size=min_cluster_size,
            canonicalization_min_cluster_size=canonical_min,
            metric=metric,
            source_artifact_sha256=source_artifact_hashes.get(period),
            embedding_provider=embedding_provider,
            embedding_model_revision=embedding_model_revision,
            embedding_contract_version=embedding_contract_version,
            embedding_dtype=embedding_dtype,
        )

    families_frame = _families_frame(
        families,
        clustering_model=clustering_model,
        embedding_provider=embedding_provider,
        min_cluster_size=min_cluster_size,
        canonicalization_min_cluster_size=canonical_min,
        metric=metric,
        source_artifact_hashes=source_artifact_hashes,
        embedding_model_revision=embedding_model_revision,
        embedding_contract_version=embedding_contract_version,
        embedding_dtype=embedding_dtype,
    )
    return monthly_summary_frames, monthly_observation_frames, families_frame


def extract_general_theme_observations(
    frame: pd.DataFrame, *, period: str
) -> tuple[list[ThemeObservation], int, set[str]]:
    """Return admitted observations plus the legacy missing-theme diagnostic.

    The public three-value shape is retained for compatibility. The production
    clustering pipeline uses the internal diagnostic-aware variant so ambiguous
    legacy multi-theme serializations can be reported separately.
    """
    observations, excluded_missing, _, themed_pairs = (
        _extract_general_theme_observations_with_diagnostics(frame, period=period)
    )
    return observations, excluded_missing, themed_pairs


def _extract_general_theme_observations_with_diagnostics(
    frame: pd.DataFrame, *, period: str
) -> tuple[list[ThemeObservation], int, int, set[str]]:
    observations: list[ThemeObservation] = []
    excluded_missing_general = 0
    excluded_ambiguous_general = 0
    themed_pairs: set[str] = set()

    for source_index, record in enumerate(frame.to_dict(orient="records")):
        absolute = _community_id(record.get("absolute_community"))
        weighted = _community_id(record.get("weighted_community"))
        pair_key = _pair_key(absolute, weighted)
        if pair_key is None:
            continue

        entries, exclusion_reason = _general_theme_entries(record)
        if exclusion_reason == _AMBIGUOUS_GENERAL_THEME_SERIALIZATION:
            # Preserve the existing reporting denominator: the source pair has a
            # saved general-theme value even though it cannot be safely split
            # into semantic observations. Only the clustering population is
            # reduced.
            themed_pairs.add(pair_key)
            excluded_ambiguous_general += 1
            logger.warning(
                "excluded ambiguous general-theme serialization period=%s pair_key=%s source_index=%s reason=%s",
                period,
                pair_key,
                source_index,
                exclusion_reason,
            )
            continue
        if not entries:
            excluded_missing_general += 1
            continue

        themed_pairs.add(pair_key)
        for label, keywords in entries:
            observations.append(
                ThemeObservation(
                    period=period,
                    pair_key=pair_key,
                    absolute_community=absolute,
                    weighted_community=weighted,
                    label=label,
                    keywords=tuple(keywords),
                    source_index=source_index,
                )
            )
    return (
        observations,
        excluded_missing_general,
        excluded_ambiguous_general,
        themed_pairs,
    )


def _fit_hdbscan(
    embeddings: np.ndarray,
    *,
    min_cluster_size: int,
    metric: str,
    clusterer_factory: Callable[..., Any] | None,
    cluster_selection_method: str = "eom",
    allow_single_cluster: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    # Keep historical helper defaults explicit for read-only benchmark callers.
    # Production Stage A passes the contract-3.0 selection/single-cluster policy.
    count = embeddings.shape[0]
    if count < min_cluster_size:
        return np.full(count, -1, dtype=int), np.zeros(count, dtype=float)
    translated_min_samples = min_cluster_size + 1
    if clusterer_factory is None and count < translated_min_samples:
        # The legacy contrib implementation excluded the query point from
        # min_samples. With fewer than min_cluster_size + 1 observations there
        # cannot be enough neighbours to form a core point under that contract,
        # so return deterministic noise instead of asking sklearn to reject the
        # invalid min_samples > n_samples combination.
        return np.full(count, -1, dtype=int), np.zeros(count, dtype=float)
    hdbscan_kwargs = {
        "min_cluster_size": min_cluster_size,
        # sklearn includes the point itself in min_samples, while the legacy
        # scikit-contrib implementation did not. +1 preserves the previous
        # effective density threshold during the controlled implementation migration.
        "min_samples": translated_min_samples,
        "metric": metric,
        "cluster_selection_method": cluster_selection_method,
        "allow_single_cluster": allow_single_cluster,
        "copy": True,
    }
    if clusterer_factory is None:
        from sklearn.cluster import HDBSCAN

        clusterer = HDBSCAN(**hdbscan_kwargs)
    else:
        clusterer = clusterer_factory(**hdbscan_kwargs)
    clusterer.fit(embeddings)
    labels = np.asarray(clusterer.labels_, dtype=int)
    probabilities = np.asarray(
        getattr(clusterer, "probabilities_", np.where(labels >= 0, 1.0, 0.0)),
        dtype=float,
    )
    if labels.shape != (count,) or probabilities.shape != (count,):
        raise RuntimeError("HDBSCAN returned malformed labels or probabilities")
    return labels, probabilities


def _monthly_clusters(
    period: str,
    observations: Sequence[ThemeObservation],
    embeddings: np.ndarray,
    labels: np.ndarray,
    probabilities: np.ndarray,
) -> list[MonthlyCluster]:
    clusters: list[MonthlyCluster] = []
    for hdbscan_label in sorted({int(value) for value in labels if int(value) >= 0}):
        indices = tuple(int(index) for index in np.flatnonzero(labels == hdbscan_label))
        representative = _semantic_medoid_label(
            [observations[index].label for index in indices],
            embeddings[list(indices)],
            source_keys=[observations[index].source_key for index in indices],
        )
        source_identities = sorted(observations[index].source_key for index in indices)
        cluster_id = _stable_id(
            "mc",
            {
                "contract": MONTHLY_CLUSTER_CONTRACT_VERSION,
                "period": period,
                "sources": source_identities,
            },
        )
        clusters.append(
            MonthlyCluster(
                period=period,
                cluster_id=cluster_id,
                hdbscan_label=hdbscan_label,
                representative_theme=representative,
                observation_indices=indices,
                mean_membership_probability=float(
                    np.mean(probabilities[list(indices)])
                ),
            )
        )
    return clusters


def _normalized_representative_embeddings(
    clusters: Sequence[MonthlyCluster],
    *,
    observations: Sequence[ThemeObservation],
    embeddings: np.ndarray,
) -> dict[str, np.ndarray]:
    """Resolve each monthly semantic medoid to its existing normalized vector.

    Stage B must reuse a vector already produced for monthly clustering. It does
    not re-embed representative labels and does not average heterogeneous
    constituent vectors.
    """
    result: dict[str, np.ndarray] = {}
    for cluster in clusters:
        representative_indices = [
            index
            for index in cluster.observation_indices
            if observations[index].label == cluster.representative_theme
        ]
        if not representative_indices:
            raise ValueError(
                "monthly cluster "
                f"{cluster.cluster_id!r} representative "
                f"{cluster.representative_theme!r} is missing from its constituent "
                "observations"
            )

        representative_vectors = np.asarray(
            embeddings[representative_indices], dtype=np.float64
        )
        vector = representative_vectors[0]
        if not np.allclose(representative_vectors, vector, rtol=1e-7, atol=1e-7):
            raise ValueError(
                "monthly cluster "
                f"{cluster.cluster_id!r} representative "
                f"{cluster.representative_theme!r} maps to inconsistent recorded "
                "embeddings"
            )

        norm = float(np.linalg.norm(vector))
        if not math.isfinite(norm) or norm <= 0.0:
            raise ValueError(
                "cannot L2-normalize zero/non-finite representative embedding for "
                f"monthly cluster {cluster.cluster_id!r}"
            )
        result[cluster.cluster_id] = vector / norm
    return result


def _validate_canonical_representation_matrix(
    embeddings: np.ndarray, *, expected_rows: int
) -> None:
    if embeddings.ndim != 2 or embeddings.shape[0] != expected_rows:
        raise ValueError(
            "Stage-B representation matrix has invalid shape "
            f"{embeddings.shape}; expected ({expected_rows}, dimensions)"
        )
    if embeddings.shape[1] == 0 or not np.isfinite(embeddings).all():
        raise ValueError("Stage-B representation matrix must be finite and non-empty")
    norms = np.linalg.norm(embeddings, axis=1)
    if not np.allclose(norms, 1.0, rtol=1e-7, atol=1e-7):
        raise ValueError(
            "Stage-B monthly representative embeddings must be L2-normalized"
        )


def _canonicalize_monthly_clusters(
    clusters: Sequence[MonthlyCluster],
    *,
    normalized_representative_embeddings: Mapping[str, np.ndarray],
) -> tuple[list[CanonicalFamily], dict[str, CanonicalFamily]]:
    if not clusters:
        return [], {}

    ordered_clusters = sorted(clusters, key=lambda item: (item.period, item.cluster_id))
    missing = [
        cluster.cluster_id
        for cluster in ordered_clusters
        if cluster.cluster_id not in normalized_representative_embeddings
    ]
    if missing:
        raise ValueError(
            "missing normalized representative embedding(s) for monthly cluster(s): "
            + ", ".join(missing[:10])
        )

    embeddings = np.vstack(
        [
            np.asarray(
                normalized_representative_embeddings[cluster.cluster_id],
                dtype=np.float64,
            )
            for cluster in ordered_clusters
        ]
    )
    _validate_canonical_representation_matrix(
        embeddings, expected_rows=len(ordered_clusters)
    )

    if len(ordered_clusters) == 1:
        stage_b_labels = np.asarray([0], dtype=int)
    else:
        clusterer = AgglomerativeClustering(
            n_clusters=None,
            metric=CANONICALIZATION_METRIC,
            linkage=CANONICALIZATION_LINKAGE,
            distance_threshold=CANONICALIZATION_DISTANCE_THRESHOLD,
            compute_full_tree=True,
        )
        stage_b_labels = np.asarray(clusterer.fit_predict(embeddings), dtype=int)
        if stage_b_labels.shape != (len(ordered_clusters),):
            raise RuntimeError(
                "Stage-B agglomerative clustering returned malformed labels"
            )

    grouped: dict[int, list[int]] = {}
    for index, stage_b_label in enumerate(stage_b_labels):
        grouped.setdefault(int(stage_b_label), []).append(index)

    families: list[CanonicalFamily] = []
    by_cluster: dict[str, CanonicalFamily] = {}
    for stage_b_label, indices in sorted(grouped.items()):
        member_clusters = [ordered_clusters[index] for index in indices]
        canonical_label = _semantic_medoid_label(
            [cluster.representative_theme for cluster in member_clusters],
            embeddings[indices],
            source_keys=[cluster.cluster_id for cluster in member_clusters],
        )
        canonical_id = _stable_id(
            "ct",
            {
                "contract": CANONICALIZATION_CONTRACT_VERSION,
                "monthly_clusters": sorted(
                    cluster.cluster_id for cluster in member_clusters
                ),
            },
        )
        family = CanonicalFamily(
            canonical_theme_id=canonical_id,
            canonical_label=canonical_label,
            monthly_cluster_ids=tuple(
                sorted(cluster.cluster_id for cluster in member_clusters)
            ),
            monthly_representatives=tuple(
                sorted({cluster.representative_theme for cluster in member_clusters})
            ),
            periods=tuple(sorted({cluster.period for cluster in member_clusters})),
            stage_b_cluster_label=stage_b_label,
            hdbscan_label=None,
            singleton_canonical_theme=len(member_clusters) == 1,
        )
        families.append(family)
        for cluster in member_clusters:
            by_cluster[cluster.cluster_id] = family
    families.sort(
        key=lambda item: (item.canonical_label.casefold(), item.canonical_theme_id)
    )
    return families, by_cluster


def _canonicalization_provenance() -> dict[str, Any]:
    return {
        "canonicalization_representation": CANONICALIZATION_REPRESENTATION,
        "canonicalization_grouping_method": CANONICALIZATION_GROUPING_METHOD,
        "canonicalization_implementation": CANONICALIZATION_IMPLEMENTATION,
        "canonicalization_metric": CANONICALIZATION_METRIC,
        "canonicalization_linkage": CANONICALIZATION_LINKAGE,
        "canonicalization_similarity_threshold": (
            CANONICALIZATION_SIMILARITY_THRESHOLD
        ),
        "canonicalization_distance_threshold": CANONICALIZATION_DISTANCE_THRESHOLD,
    }


def _monthly_clustering_provenance(
    *, min_cluster_size: int, metric: str
) -> dict[str, Any]:
    return {
        "clustering_input_normalized": MONTHLY_CLUSTERING_INPUT_NORMALIZED,
        "hdbscan_min_samples": min_cluster_size + 1,
        "hdbscan_cluster_selection_method": MONTHLY_CLUSTER_SELECTION_METHOD,
        "hdbscan_allow_single_cluster": MONTHLY_CLUSTER_ALLOW_SINGLE_CLUSTER,
        "clustering_metric": metric,
    }


def _monthly_summary_frame(
    *,
    period: str,
    observations: Sequence[ThemeObservation],
    clusters: Sequence[MonthlyCluster],
    families: Mapping[str, CanonicalFamily],
    denominator_pairs: set[str],
    excluded_missing_general: int,
    excluded_ambiguous_general: int,
    monthly_noise_observation_count: int,
    clustering_model: str,
    min_cluster_size: int,
    canonicalization_min_cluster_size: int,
    metric: str,
    source_artifact_sha256: str | None,
    embedding_provider: str,
    embedding_model_revision: str,
    embedding_contract_version: str,
    embedding_dtype: str,
) -> pd.DataFrame:
    grouped: dict[str, dict[str, Any]] = {}
    for cluster in clusters:
        family = families[cluster.cluster_id]
        item = grouped.setdefault(
            family.canonical_theme_id,
            {
                "family": family,
                "clusters": [],
                "observations": [],
            },
        )
        item["clusters"].append(cluster)
        item["observations"].extend(
            observations[index] for index in cluster.observation_indices
        )

    rows: list[dict[str, Any]] = []
    denominator = len(denominator_pairs)
    for canonical_id, item in grouped.items():
        family: CanonicalFamily = item["family"]
        member_clusters: list[MonthlyCluster] = item["clusters"]
        member_observations: list[ThemeObservation] = item["observations"]
        pairs = sorted({obs.pair_key for obs in member_observations})
        pair_details = _pair_details(member_observations)
        keywords = _rank_keywords(member_observations)
        source_labels = sorted(
            {obs.label for obs in member_observations}, key=str.casefold
        )
        representatives = sorted(
            {cluster.representative_theme for cluster in member_clusters},
            key=str.casefold,
        )
        cluster_ids = sorted(cluster.cluster_id for cluster in member_clusters)
        probability_values = [
            cluster.mean_membership_probability for cluster in member_clusters
        ]
        rows.append(
            {
                "period": period,
                "canonical_theme_id": canonical_id,
                "canonical_theme_label": family.canonical_label,
                "monthly_cluster_ids": json.dumps(cluster_ids, ensure_ascii=False),
                "monthly_representative_themes": json.dumps(
                    representatives, ensure_ascii=False
                ),
                "source_general_theme_labels": json.dumps(
                    source_labels, ensure_ascii=False
                ),
                "community_count": len(pairs),
                "total_themed_community_pairs": denominator,
                "percentage": (
                    round((len(pairs) * 100.0) / denominator, 6) if denominator else 0.0
                ),
                "prominent_keywords": json.dumps(keywords, ensure_ascii=False),
                "community_pairs": json.dumps(pair_details, ensure_ascii=False),
                "mean_membership_probability": (
                    round(float(np.mean(probability_values)), 8)
                    if probability_values
                    else 0.0
                ),
                "source_observation_count": len(observations),
                "cluster_observation_count": len(member_observations),
                "monthly_cluster_count": len(member_clusters),
                "excluded_records_missing_general_theme": excluded_missing_general,
                "excluded_records_ambiguous_general_theme_serialization": (
                    excluded_ambiguous_general
                ),
                "monthly_noise_observation_count": monthly_noise_observation_count,
                "embedding_provider": embedding_provider,
                "embedding_model": clustering_model,
                "embedding_model_revision": embedding_model_revision,
                "embedding_contract_version": embedding_contract_version,
                "embedding_dtype": embedding_dtype,
                "embedding_normalized": False,
                "hdbscan_implementation": HDBSCAN_IMPLEMENTATION,
                "hdbscan_version": HDBSCAN_VERSION,
                "clustering_min_cluster_size": min_cluster_size,
                "canonicalization_min_cluster_size": canonicalization_min_cluster_size,
                **_monthly_clustering_provenance(
                    min_cluster_size=min_cluster_size, metric=metric
                ),
                **_canonicalization_provenance(),
                "monthly_cluster_contract_version": MONTHLY_CLUSTER_CONTRACT_VERSION,
                "canonicalization_contract_version": CANONICALIZATION_CONTRACT_VERSION,
                "source_artifact_sha256": source_artifact_sha256 or "",
            }
        )
    if not rows:
        rows.append(
            {
                "period": period,
                "canonical_theme_id": "",
                "canonical_theme_label": "",
                "monthly_cluster_ids": "[]",
                "monthly_representative_themes": "[]",
                "source_general_theme_labels": "[]",
                "community_count": 0,
                "total_themed_community_pairs": denominator,
                "percentage": 0.0,
                "prominent_keywords": "[]",
                "community_pairs": "[]",
                "mean_membership_probability": 0.0,
                "source_observation_count": len(observations),
                "cluster_observation_count": 0,
                "monthly_cluster_count": 0,
                "excluded_records_missing_general_theme": excluded_missing_general,
                "excluded_records_ambiguous_general_theme_serialization": (
                    excluded_ambiguous_general
                ),
                "monthly_noise_observation_count": monthly_noise_observation_count,
                "embedding_provider": embedding_provider,
                "embedding_model": clustering_model,
                "embedding_model_revision": embedding_model_revision,
                "embedding_contract_version": embedding_contract_version,
                "embedding_dtype": embedding_dtype,
                "embedding_normalized": False,
                "hdbscan_implementation": HDBSCAN_IMPLEMENTATION,
                "hdbscan_version": HDBSCAN_VERSION,
                "clustering_min_cluster_size": min_cluster_size,
                "canonicalization_min_cluster_size": canonicalization_min_cluster_size,
                **_monthly_clustering_provenance(
                    min_cluster_size=min_cluster_size, metric=metric
                ),
                **_canonicalization_provenance(),
                "monthly_cluster_contract_version": MONTHLY_CLUSTER_CONTRACT_VERSION,
                "canonicalization_contract_version": CANONICALIZATION_CONTRACT_VERSION,
                "source_artifact_sha256": source_artifact_sha256 or "",
            }
        )
    rows.sort(
        key=lambda row: (
            -int(row["community_count"]),
            str(row["canonical_theme_label"]).casefold(),
            str(row["canonical_theme_id"]),
        )
    )
    return pd.DataFrame(rows, columns=CLUSTER_SUMMARY_COLUMNS)


def _observation_frame(
    *,
    observations: Sequence[ThemeObservation],
    labels: np.ndarray,
    probabilities: np.ndarray,
    clusters: Sequence[MonthlyCluster],
    family_by_cluster: Mapping[str, CanonicalFamily],
    clustering_model: str,
    min_cluster_size: int,
    canonicalization_min_cluster_size: int,
    metric: str,
    source_artifact_sha256: str | None,
    embedding_provider: str,
    embedding_model_revision: str,
    embedding_contract_version: str,
    embedding_dtype: str,
) -> pd.DataFrame:
    cluster_by_observation: dict[int, MonthlyCluster] = {}
    for cluster in clusters:
        for index in cluster.observation_indices:
            cluster_by_observation[index] = cluster
    rows = []
    for index, observation in enumerate(observations):
        cluster = cluster_by_observation.get(index)
        family = family_by_cluster.get(cluster.cluster_id) if cluster else None
        rows.append(
            {
                "period": observation.period,
                "absolute_community": observation.absolute_community,
                "weighted_community": observation.weighted_community,
                "pair_key": observation.pair_key,
                "source_general_theme_label": observation.label,
                "general_keywords": json.dumps(
                    list(observation.keywords), ensure_ascii=False
                ),
                "source_index": observation.source_index,
                "hdbscan_label": int(labels[index]) if len(labels) else -1,
                "membership_probability": (
                    round(float(probabilities[index]), 8) if len(probabilities) else 0.0
                ),
                "is_monthly_noise": cluster is None,
                "monthly_cluster_id": cluster.cluster_id if cluster else None,
                "monthly_representative_theme": (
                    cluster.representative_theme if cluster else None
                ),
                "canonical_theme_id": family.canonical_theme_id if family else None,
                "canonical_theme_label": family.canonical_label if family else None,
                "embedding_provider": embedding_provider,
                "embedding_model": clustering_model,
                "embedding_model_revision": embedding_model_revision,
                "embedding_contract_version": embedding_contract_version,
                "embedding_dtype": embedding_dtype,
                "embedding_normalized": False,
                "hdbscan_implementation": HDBSCAN_IMPLEMENTATION,
                "hdbscan_version": HDBSCAN_VERSION,
                "clustering_min_cluster_size": min_cluster_size,
                "canonicalization_min_cluster_size": canonicalization_min_cluster_size,
                **_monthly_clustering_provenance(
                    min_cluster_size=min_cluster_size, metric=metric
                ),
                **_canonicalization_provenance(),
                "source_artifact_sha256": source_artifact_sha256 or "",
                "monthly_cluster_contract_version": MONTHLY_CLUSTER_CONTRACT_VERSION,
                "canonicalization_contract_version": CANONICALIZATION_CONTRACT_VERSION,
            }
        )
    return pd.DataFrame(rows, columns=CLUSTER_OBSERVATION_COLUMNS)


def _families_frame(
    families: Sequence[CanonicalFamily],
    *,
    clustering_model: str,
    embedding_provider: str,
    min_cluster_size: int,
    canonicalization_min_cluster_size: int,
    metric: str,
    source_artifact_hashes: Mapping[str, str],
    embedding_model_revision: str,
    embedding_contract_version: str,
    embedding_dtype: str,
) -> pd.DataFrame:
    source_hashes = json.dumps(
        [source_artifact_hashes[key] for key in sorted(source_artifact_hashes)],
        ensure_ascii=False,
    )
    rows = [
        {
            "canonical_theme_id": family.canonical_theme_id,
            "canonical_theme_label": family.canonical_label,
            "monthly_cluster_ids": json.dumps(
                list(family.monthly_cluster_ids), ensure_ascii=False
            ),
            "monthly_representatives": json.dumps(
                list(family.monthly_representatives), ensure_ascii=False
            ),
            "periods": json.dumps(list(family.periods), ensure_ascii=False),
            "months_present": len(family.periods),
            "stage_b_cluster_label": family.stage_b_cluster_label,
            "stage_b_hdbscan_label": family.hdbscan_label,
            "singleton_canonical_theme": family.singleton_canonical_theme,
            "embedding_provider": embedding_provider,
            "embedding_model": clustering_model,
            "embedding_model_revision": embedding_model_revision,
            "embedding_contract_version": embedding_contract_version,
            "embedding_dtype": embedding_dtype,
            "embedding_normalized": False,
            "hdbscan_implementation": HDBSCAN_IMPLEMENTATION,
            "hdbscan_version": HDBSCAN_VERSION,
            "clustering_min_cluster_size": min_cluster_size,
            "canonicalization_min_cluster_size": canonicalization_min_cluster_size,
            **_monthly_clustering_provenance(
                min_cluster_size=min_cluster_size, metric=metric
            ),
            **_canonicalization_provenance(),
            "source_artifact_sha256s": source_hashes,
            "monthly_cluster_contract_version": MONTHLY_CLUSTER_CONTRACT_VERSION,
            "canonicalization_contract_version": CANONICALIZATION_CONTRACT_VERSION,
        }
        for family in families
    ]
    return pd.DataFrame(rows, columns=CANONICAL_FAMILY_COLUMNS)


def _semantic_medoid_label(
    labels: Sequence[str], embeddings: np.ndarray, *, source_keys: Sequence[str]
) -> str:
    if not labels:
        raise ValueError("cannot choose representative from an empty cluster")
    if len(labels) == 1:
        return labels[0]
    similarities = cosine_similarity(embeddings)
    means = similarities.mean(axis=1)
    best = max(float(value) for value in means)
    candidates = [
        index
        for index, value in enumerate(means)
        if math.isclose(float(value), best, rel_tol=1e-12, abs_tol=1e-12)
    ]
    winner = min(
        candidates,
        key=lambda index: (_normalized_label(labels[index]), source_keys[index]),
    )
    return labels[winner]


def _rank_keywords(
    observations: Sequence[ThemeObservation], limit: int = 20
) -> list[str]:
    evidence: dict[str, dict[str, Any]] = {}
    source_order = 0
    for observation in observations:
        seen_in_pair: set[str] = set()
        for keyword in observation.keywords:
            display = _display_text(keyword)
            if not display:
                continue
            key = display.casefold()
            if key in seen_in_pair:
                continue
            seen_in_pair.add(key)
            item = evidence.get(key)
            if item is None:
                item = {"display": display, "order": source_order, "pairs": set()}
                evidence[key] = item
                source_order += 1
            item["pairs"].add(observation.pair_key)
    ranked = sorted(
        evidence.values(),
        key=lambda item: (
            -len(item["pairs"]),
            item["order"],
            item["display"].casefold(),
        ),
    )
    return [str(item["display"]) for item in ranked[:limit]]


def _pair_details(observations: Sequence[ThemeObservation]) -> list[dict[str, Any]]:
    by_pair: dict[str, dict[str, Any]] = {}
    for observation in observations:
        item = by_pair.setdefault(
            observation.pair_key,
            {
                "absolute_community": observation.absolute_community,
                "weighted_community": observation.weighted_community,
                "source_labels": [],
                "keywords": [],
            },
        )
        if observation.label not in item["source_labels"]:
            item["source_labels"].append(observation.label)
        seen = {str(value).casefold() for value in item["keywords"]}
        for keyword in observation.keywords:
            if keyword.casefold() not in seen:
                item["keywords"].append(keyword)
                seen.add(keyword.casefold())
    return [by_pair[key] for key in sorted(by_pair)]


def _general_theme_entries(
    record: Mapping[str, Any],
) -> tuple[list[tuple[str, list[str]]], str | None]:
    """Return admitted saved general-theme labels and an exclusion reason.

    ``generate_llm_themes`` historically persists multiple general theme names
    as one dot-joined string while ``general_theme_gpt`` retains the original
    mapping. Mapping keys may decompose that legacy representation only when
    they round-trip exactly. If a value structurally looks like that legacy
    multi-theme encoding but its mapping is absent or inconsistent, the record
    is excluded rather than being promoted to one composite semantic label.
    """
    raw_names = record.get("general_theme_names")
    names = _general_theme_names(raw_names)
    if not names:
        return [], _MISSING_GENERAL_THEME

    mapping = _general_theme_mapping(record.get("general_theme_gpt"))
    raw_scalar_name = _general_theme_scalar_text(raw_names)
    if raw_scalar_name is not None:
        saved_name = _display_text(raw_scalar_name)
        if mapping:
            mapping_names = list(mapping)
            flattened = ".".join(mapping_names)
            if saved_name == _display_text(flattened):
                names = mapping_names
            elif _looks_like_legacy_dot_joined_multi_theme(raw_names):
                return [], _AMBIGUOUS_GENERAL_THEME_SERIALIZATION
        elif _looks_like_legacy_dot_joined_multi_theme(raw_names):
            return [], _AMBIGUOUS_GENERAL_THEME_SERIALIZATION

    fallback_keywords = _keywords(record.get("all_keywords"))
    entries: list[tuple[str, list[str]]] = []
    for name in names:
        mapped_keywords = _keywords(mapping.get(name)) if name in mapping else []
        entries.append((name, mapped_keywords or fallback_keywords))
    return entries, None


def _looks_like_legacy_dot_joined_multi_theme(value: Any) -> bool:
    """Conservatively identify the producer's ambiguous dot-joined shape.

    A blind split on ``.`` would corrupt legitimate labels such as ``U.S.
    Politics``. We therefore require at least two title-like, multi-word
    segments separated by a period followed by optional whitespace and an
    uppercase letter. This matches the known legacy producer failure while
    avoiding common abbreviation punctuation.
    """
    if not isinstance(value, str):
        return False
    text = _display_text(value)
    if not text or "." not in text:
        return False
    segments = [
        segment.strip()
        for segment in re.split(r"\.\s*(?=[A-Z][A-Za-z])", text)
        if segment.strip()
    ]
    if len(segments) < 2:
        return False
    return sum(len(segment.split()) >= 2 for segment in segments) >= 2


def _general_theme_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    normalized = value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        for parser in (json.loads, ast.literal_eval):
            try:
                normalized = parser(text)
                break
            except (ValueError, SyntaxError, json.JSONDecodeError):
                continue
        else:
            return {}
    if not isinstance(normalized, Mapping):
        return {}

    result: dict[str, Any] = {}
    for raw_name, raw_keywords in normalized.items():
        name = _display_text(raw_name)
        if name and name not in result:
            result[name] = raw_keywords
    return result


def _general_theme_names(value: Any) -> list[str]:
    """Parse saved general-theme labels without treating commas as delimiters.

    ``general_theme_names`` is produced from semantic labels, and commas are valid
    label text. Structured list representations remain supported, but an ordinary
    scalar string is one saved label (or one legacy dot-joined serialization that
    is reconciled separately against ``general_theme_gpt``).
    """
    if value is None:
        return []
    try:
        if pd.isna(value):
            return []
    except (TypeError, ValueError):
        pass

    values: Iterable[Any]
    if isinstance(value, list):
        values = value
    elif isinstance(value, tuple):
        values = value
    elif hasattr(value, "tolist") and not isinstance(value, str):
        converted = value.tolist()
        values = converted if isinstance(converted, list) else [converted]
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        parsed: Any = None
        parsed_successfully = False
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(text)
                parsed_successfully = True
                break
            except (ValueError, SyntaxError, json.JSONDecodeError):
                continue
        if parsed_successfully and isinstance(parsed, (list, tuple)):
            values = parsed
        elif parsed_successfully:
            values = [parsed]
        else:
            values = [text]
    else:
        values = [value]

    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        label = _display_text(item)
        if label and label not in seen:
            seen.add(label)
            result.append(label)
    return result


def _general_theme_scalar_text(value: Any) -> str | None:
    """Return scalar saved text, or ``None`` when the value is list-structured."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None

    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(text)
        except (ValueError, SyntaxError, json.JSONDecodeError):
            continue
        if isinstance(parsed, (list, tuple)):
            return None
        return _display_text(parsed) or None
    return _display_text(text)


def _keywords(value: Any) -> list[str]:
    parsed = _parse_list(value)
    values = parsed if isinstance(parsed, list) else [parsed]
    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        display = _display_text(item)
        key = display.casefold()
        if display and key not in seen:
            seen.add(key)
            result.append(display)
    return result


def _community_id(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = _display_text(value)
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text or None


def _pair_key(absolute: str | None, weighted: str | None) -> str | None:
    if absolute is None and weighted is None:
        return None
    return f"if:{absolute or ''}|wif:{weighted or ''}"


def _display_text(value: Any) -> str:
    return " ".join(str(value).strip().split()) if value is not None else ""


def _normalized_label(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def _stable_id(prefix: str, payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(encoded).hexdigest()[:16]}"


def _validate_embeddings(values: Any, expected_rows: int) -> np.ndarray:
    matrix = np.asarray(values, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[0] != expected_rows or matrix.shape[1] == 0:
        raise RuntimeError(
            f"embedding provider returned shape {matrix.shape}; expected ({expected_rows}, dimensions)"
        )
    if not np.isfinite(matrix).all():
        raise RuntimeError("embedding provider returned non-finite values")
    return matrix


def _l2_normalize_embeddings(
    embeddings: np.ndarray,
    *,
    context: str,
) -> np.ndarray:
    """Return an in-memory float64 unit-vector copy for Stage-A clustering.

    The recorded embedding artifact remains the raw float32 provider output. This
    helper changes only the geometry passed to HDBSCAN and deliberately leaves
    semantic-medoid and Stage-B representative calculations on the recorded
    vectors.
    """
    matrix = np.asarray(embeddings, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[1] == 0 or not np.isfinite(matrix).all():
        raise ValueError(f"{context} are not a finite 2D embedding matrix")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if not np.isfinite(norms).all() or np.any(norms <= 0.0):
        raise ValueError(f"{context} contain zero/non-finite vectors")
    return matrix / norms


def _periods(monthly: Mapping[str, pd.DataFrame], year: str | int) -> dict[str, str]:
    result: dict[str, str] = {}
    month_names = {
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
    for month in monthly:
        text = str(month).strip().lower()
        number = int(text) if text.isdigit() else month_names.get(text)
        if number is None or not 1 <= number <= 12:
            raise ValueError(f"unsupported theme month value: {month!r}")
        result[month] = f"{int(year):04d}-{number:02d}"
    return result


CLUSTER_SUMMARY_COLUMNS = [
    "period",
    "canonical_theme_id",
    "canonical_theme_label",
    "monthly_cluster_ids",
    "monthly_representative_themes",
    "source_general_theme_labels",
    "community_count",
    "total_themed_community_pairs",
    "percentage",
    "prominent_keywords",
    "community_pairs",
    "mean_membership_probability",
    "source_observation_count",
    "cluster_observation_count",
    "monthly_cluster_count",
    "excluded_records_missing_general_theme",
    "excluded_records_ambiguous_general_theme_serialization",
    "monthly_noise_observation_count",
    "embedding_provider",
    "embedding_model",
    "embedding_model_revision",
    "embedding_contract_version",
    "embedding_dtype",
    "embedding_normalized",
    "clustering_input_normalized",
    "hdbscan_implementation",
    "hdbscan_version",
    "hdbscan_min_samples",
    "hdbscan_cluster_selection_method",
    "hdbscan_allow_single_cluster",
    "clustering_min_cluster_size",
    "canonicalization_min_cluster_size",
    "clustering_metric",
    "canonicalization_representation",
    "canonicalization_grouping_method",
    "canonicalization_implementation",
    "canonicalization_metric",
    "canonicalization_linkage",
    "canonicalization_similarity_threshold",
    "canonicalization_distance_threshold",
    "monthly_cluster_contract_version",
    "canonicalization_contract_version",
    "source_artifact_sha256",
]

CLUSTER_OBSERVATION_COLUMNS = [
    "period",
    "absolute_community",
    "weighted_community",
    "pair_key",
    "source_general_theme_label",
    "general_keywords",
    "source_index",
    "hdbscan_label",
    "membership_probability",
    "is_monthly_noise",
    "monthly_cluster_id",
    "monthly_representative_theme",
    "canonical_theme_id",
    "canonical_theme_label",
    "embedding_provider",
    "embedding_model",
    "embedding_model_revision",
    "embedding_contract_version",
    "embedding_dtype",
    "embedding_normalized",
    "clustering_input_normalized",
    "hdbscan_implementation",
    "hdbscan_version",
    "hdbscan_min_samples",
    "hdbscan_cluster_selection_method",
    "hdbscan_allow_single_cluster",
    "clustering_min_cluster_size",
    "canonicalization_min_cluster_size",
    "clustering_metric",
    "canonicalization_representation",
    "canonicalization_grouping_method",
    "canonicalization_implementation",
    "canonicalization_metric",
    "canonicalization_linkage",
    "canonicalization_similarity_threshold",
    "canonicalization_distance_threshold",
    "source_artifact_sha256",
    "monthly_cluster_contract_version",
    "canonicalization_contract_version",
]

CANONICAL_FAMILY_COLUMNS = [
    "canonical_theme_id",
    "canonical_theme_label",
    "monthly_cluster_ids",
    "monthly_representatives",
    "periods",
    "months_present",
    "stage_b_cluster_label",
    "stage_b_hdbscan_label",
    "singleton_canonical_theme",
    "embedding_provider",
    "embedding_model",
    "embedding_model_revision",
    "embedding_contract_version",
    "embedding_dtype",
    "embedding_normalized",
    "clustering_input_normalized",
    "hdbscan_implementation",
    "hdbscan_version",
    "hdbscan_min_samples",
    "hdbscan_cluster_selection_method",
    "hdbscan_allow_single_cluster",
    "clustering_min_cluster_size",
    "canonicalization_min_cluster_size",
    "clustering_metric",
    "canonicalization_representation",
    "canonicalization_grouping_method",
    "canonicalization_implementation",
    "canonicalization_metric",
    "canonicalization_linkage",
    "canonicalization_similarity_threshold",
    "canonicalization_distance_threshold",
    "source_artifact_sha256s",
    "monthly_cluster_contract_version",
    "canonicalization_contract_version",
]
