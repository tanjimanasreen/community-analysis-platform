from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, HDBSCAN
from sklearn.metrics.pairwise import cosine_similarity

from src.themes.theme_clustering import _fit_hdbscan

REPRESENTATIVE_EMBEDDING = "representative"
CONSTITUENT_MEAN_EMBEDDING = "constituent_mean"
CONSTITUENT_UNIT_MEAN_EMBEDDING = "constituent_unit_mean"
CONSTITUENT_PROBABILITY_WEIGHTED_MEAN_EMBEDDING = (
    "constituent_probability_weighted_mean"
)
CONSTITUENT_UNIQUE_MEAN_EMBEDDING = "constituent_unique_mean"
HDBSCAN_GROUPING = "hdbscan"
AGGLOMERATIVE_GROUPING = "agglomerative"

PLAN083_REPRESENTATIONS = (
    REPRESENTATIVE_EMBEDDING,
    CONSTITUENT_MEAN_EMBEDDING,
    CONSTITUENT_UNIT_MEAN_EMBEDDING,
    CONSTITUENT_PROBABILITY_WEIGHTED_MEAN_EMBEDDING,
    CONSTITUENT_UNIQUE_MEAN_EMBEDDING,
)
PLAN083_SIMILARITY_THRESHOLDS = (0.60, 0.65, 0.70, 0.75, 0.80)


@dataclass(frozen=True)
class CanonicalizationVariant:
    name: str
    normalize_embeddings: bool
    metric: str
    min_cluster_size: int
    algorithm: str = "auto"
    representation: str = REPRESENTATIVE_EMBEDDING
    grouping_method: str = HDBSCAN_GROUPING
    min_samples: int | None = None
    linkage: str | None = None
    similarity_threshold: float | None = None


REPRESENTATIVE_CANONICALIZATION_BENCHMARK_VARIANTS: tuple[
    CanonicalizationVariant, ...
] = (
    CanonicalizationVariant(
        name="baseline_raw_euclidean_mcs2",
        normalize_embeddings=False,
        metric="euclidean",
        min_cluster_size=2,
    ),
    CanonicalizationVariant(
        name="normalized_euclidean_mcs2",
        normalize_embeddings=True,
        metric="euclidean",
        min_cluster_size=2,
    ),
    CanonicalizationVariant(
        name="normalized_euclidean_mcs3",
        normalize_embeddings=True,
        metric="euclidean",
        min_cluster_size=3,
    ),
    CanonicalizationVariant(
        name="normalized_euclidean_mcs4",
        normalize_embeddings=True,
        metric="euclidean",
        min_cluster_size=4,
    ),
    CanonicalizationVariant(
        name="cosine_brute_mcs2",
        normalize_embeddings=False,
        metric="cosine",
        min_cluster_size=2,
        algorithm="brute",
    ),
    CanonicalizationVariant(
        name="cosine_brute_mcs3",
        normalize_embeddings=False,
        metric="cosine",
        min_cluster_size=3,
        algorithm="brute",
    ),
)

DEFAULT_CANONICALIZATION_BENCHMARK_VARIANTS: tuple[CanonicalizationVariant, ...] = (
    *REPRESENTATIVE_CANONICALIZATION_BENCHMARK_VARIANTS,
    CanonicalizationVariant(
        name="constituent_mean_raw_euclidean_mcs2",
        normalize_embeddings=False,
        metric="euclidean",
        min_cluster_size=2,
        representation=CONSTITUENT_MEAN_EMBEDDING,
    ),
    CanonicalizationVariant(
        name="constituent_mean_normalized_euclidean_mcs2",
        normalize_embeddings=True,
        metric="euclidean",
        min_cluster_size=2,
        representation=CONSTITUENT_MEAN_EMBEDDING,
    ),
    CanonicalizationVariant(
        name="constituent_mean_normalized_euclidean_mcs2_ms1",
        normalize_embeddings=True,
        metric="euclidean",
        min_cluster_size=2,
        min_samples=1,
        representation=CONSTITUENT_MEAN_EMBEDDING,
    ),
    CanonicalizationVariant(
        name="constituent_mean_normalized_euclidean_mcs2_ms2",
        normalize_embeddings=True,
        metric="euclidean",
        min_cluster_size=2,
        min_samples=2,
        representation=CONSTITUENT_MEAN_EMBEDDING,
    ),
    *(
        CanonicalizationVariant(
            name=(
                "constituent_mean_normalized_agglomerative_"
                f"{linkage}_cosine_s{int(threshold * 100):02d}"
            ),
            normalize_embeddings=True,
            metric="cosine",
            min_cluster_size=2,
            representation=CONSTITUENT_MEAN_EMBEDDING,
            grouping_method=AGGLOMERATIVE_GROUPING,
            linkage=linkage,
            similarity_threshold=threshold,
        )
        for linkage in ("average", "complete")
        for threshold in (0.60, 0.65, 0.70, 0.75, 0.80)
    ),
    *(
        CanonicalizationVariant(
            name=(
                f"{representation}_normalized_agglomerative_complete_"
                f"cosine_s{int(threshold * 100):02d}"
            ),
            normalize_embeddings=True,
            metric="cosine",
            min_cluster_size=2,
            representation=representation,
            grouping_method=AGGLOMERATIVE_GROUPING,
            linkage="complete",
            similarity_threshold=threshold,
        )
        for representation in (
            REPRESENTATIVE_EMBEDDING,
            CONSTITUENT_UNIT_MEAN_EMBEDDING,
            CONSTITUENT_PROBABILITY_WEIGHTED_MEAN_EMBEDDING,
            CONSTITUENT_UNIQUE_MEAN_EMBEDDING,
        )
        for threshold in PLAN083_SIMILARITY_THRESHOLDS
    ),
)


REPRESENTATIVE_COLUMNS = [
    "period",
    "monthly_cluster_id",
    "monthly_representative_theme",
]


def load_canonicalization_benchmark_data(
    themes_dir: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load persisted Stage-A evidence and recorded clustering embeddings only.

    This function never performs embedding inference or theme generation. It is a
    read-only benchmark boundary for Stage-B canonicalization.
    """
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
    evidence_frames = [pd.read_parquet(path) for path in evidence_paths]
    embedding_frame = pd.read_parquet(embedding_path)
    evidence_frame = pd.concat(evidence_frames, ignore_index=True)
    return (
        extract_monthly_representatives(evidence_frames),
        evidence_frame,
        embedding_frame,
    )


def load_canonicalization_benchmark_inputs(
    themes_dir: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Backward-compatible representative/vector loader from Plan 079."""
    representatives, _, embedding_frame = load_canonicalization_benchmark_data(
        themes_dir
    )
    return representatives, embedding_frame


def extract_monthly_representatives(
    evidence_frames: Iterable[pd.DataFrame],
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for frame in evidence_frames:
        missing = [
            column for column in REPRESENTATIVE_COLUMNS if column not in frame.columns
        ]
        if missing:
            raise ValueError(
                "cluster evidence is missing benchmark columns: " + ", ".join(missing)
            )
        admitted = frame.loc[
            frame["monthly_cluster_id"].notna(), REPRESENTATIVE_COLUMNS
        ].copy()
        if not admitted.empty:
            rows.append(admitted)

    if not rows:
        return pd.DataFrame(columns=REPRESENTATIVE_COLUMNS)

    combined = pd.concat(rows, ignore_index=True)
    combined["period"] = combined["period"].astype(str)
    combined["monthly_cluster_id"] = combined["monthly_cluster_id"].astype(str)
    combined["monthly_representative_theme"] = combined[
        "monthly_representative_theme"
    ].astype(str)

    conflicts = (
        combined.groupby("monthly_cluster_id", sort=False)[
            ["period", "monthly_representative_theme"]
        ]
        .nunique(dropna=False)
        .max(axis=1)
    )
    bad_ids = sorted(conflicts[conflicts > 1].index.tolist())
    if bad_ids:
        raise ValueError(
            "monthly cluster IDs map to inconsistent period/representative values: "
            + ", ".join(bad_ids[:10])
        )

    return (
        combined.drop_duplicates(subset=["monthly_cluster_id"])
        .sort_values(["period", "monthly_cluster_id"], kind="stable")
        .reset_index(drop=True)
    )


def align_recorded_embeddings(
    representatives: pd.DataFrame,
    embedding_frame: pd.DataFrame,
) -> np.ndarray:
    by_text = _recorded_embedding_lookup(embedding_frame)

    vectors: list[np.ndarray] = []
    missing_texts: list[str] = []
    for text in representatives["monthly_representative_theme"].astype(str):
        vector = by_text.get(text)
        if vector is None:
            missing_texts.append(text)
        else:
            vectors.append(vector)
    if missing_texts:
        preview = "; ".join(repr(value) for value in missing_texts[:5])
        raise ValueError(
            f"{len(missing_texts)} monthly representative(s) are missing from the "
            f"recorded clustering embedding artifact: {preview}"
        )
    if not vectors:
        return np.empty((0, 0), dtype=np.float32)
    dimensions = {int(vector.size) for vector in vectors}
    if len(dimensions) != 1:
        raise ValueError(
            "recorded embeddings have inconsistent dimensions: " f"{sorted(dimensions)}"
        )
    return np.vstack(vectors).astype(np.float32, copy=False)


def build_constituent_mean_embeddings(
    representatives: pd.DataFrame,
    evidence_frame: pd.DataFrame,
    embedding_frame: pd.DataFrame,
) -> tuple[np.ndarray, pd.DataFrame]:
    """Represent each monthly cluster by its occurrence-weighted mean vector.

    Every persisted non-noise evidence row contributes once, matching the Stage-A
    observation population. Recorded embedding inference may be deduplicated by
    exact text, but repeated theme observations remain repeated in this mean.
    """
    required = {"monthly_cluster_id", "source_general_theme_label"}
    missing = sorted(required.difference(evidence_frame.columns))
    if missing:
        raise ValueError("cluster evidence is missing columns: " + ", ".join(missing))

    admitted = evidence_frame.loc[
        evidence_frame["monthly_cluster_id"].notna(),
        [
            "monthly_cluster_id",
            "source_general_theme_label",
        ],
    ].copy()
    admitted["monthly_cluster_id"] = admitted["monthly_cluster_id"].astype(str)
    admitted["source_general_theme_label"] = admitted[
        "source_general_theme_label"
    ].astype(str)

    by_text = _recorded_embedding_lookup(embedding_frame)
    vectors: list[np.ndarray] = []
    diagnostics: list[dict[str, object]] = []
    expected_dimensions: int | None = None

    for cluster_id in representatives["monthly_cluster_id"].astype(str):
        cluster_rows = admitted.loc[admitted["monthly_cluster_id"] == cluster_id]
        if cluster_rows.empty:
            raise ValueError(
                f"monthly cluster {cluster_id!r} has no persisted constituent evidence"
            )

        constituent_vectors: list[np.ndarray] = []
        missing_texts: list[str] = []
        labels = cluster_rows["source_general_theme_label"].astype(str).tolist()
        for text in labels:
            vector = by_text.get(text)
            if vector is None:
                missing_texts.append(text)
            else:
                constituent_vectors.append(vector)
        if missing_texts:
            preview = "; ".join(repr(value) for value in missing_texts[:5])
            raise ValueError(
                f"monthly cluster {cluster_id!r} has {len(missing_texts)} constituent "
                f"theme observation(s) missing from the recorded clustering embedding "
                f"artifact: {preview}"
            )

        dimensions = {int(vector.size) for vector in constituent_vectors}
        if len(dimensions) != 1:
            raise ValueError(
                f"monthly cluster {cluster_id!r} has inconsistent embedding dimensions: "
                f"{sorted(dimensions)}"
            )
        dimension = next(iter(dimensions))
        if expected_dimensions is None:
            expected_dimensions = dimension
        elif dimension != expected_dimensions:
            raise ValueError(
                "constituent mean embeddings have inconsistent dimensions across "
                f"monthly clusters: {expected_dimensions} != {dimension}"
            )

        matrix = np.vstack(constituent_vectors).astype(np.float64, copy=False)
        centroid = matrix.mean(axis=0)
        if not np.isfinite(centroid).all():
            raise ValueError(
                f"monthly cluster {cluster_id!r} produced a non-finite mean embedding"
            )
        vectors.append(centroid.astype(np.float32))
        diagnostics.append(
            {
                "monthly_cluster_id": cluster_id,
                "constituent_observation_count": len(labels),
                "constituent_unique_label_count": len(set(labels)),
            }
        )

    if not vectors:
        return (
            np.empty((0, 0), dtype=np.float32),
            pd.DataFrame(
                columns=[
                    "monthly_cluster_id",
                    "constituent_observation_count",
                    "constituent_unique_label_count",
                ]
            ),
        )
    return np.vstack(vectors).astype(np.float32, copy=False), pd.DataFrame(diagnostics)


def build_stage_b_representation_embeddings(
    representatives: pd.DataFrame,
    evidence_frame: pd.DataFrame,
    embedding_frame: pd.DataFrame,
    *,
    representations: Sequence[str],
) -> tuple[dict[str, np.ndarray], pd.DataFrame]:
    """Build Plan-083 Stage-B representations from persisted evidence only.

    The returned matrices stay row-aligned with ``representatives``. No embedding
    inference is allowed at this boundary; every constituent and representative
    vector must exist in the recorded clustering embedding artifact.
    """
    requested = tuple(dict.fromkeys(str(value) for value in representations))
    unsupported = sorted(set(requested).difference(PLAN083_REPRESENTATIONS))
    if unsupported:
        raise ValueError(
            "unsupported Stage-B benchmark representation(s): " + ", ".join(unsupported)
        )

    required = {"monthly_cluster_id", "source_general_theme_label"}
    if CONSTITUENT_PROBABILITY_WEIGHTED_MEAN_EMBEDDING in requested:
        required.add("membership_probability")
    missing = sorted(required.difference(evidence_frame.columns))
    if missing:
        raise ValueError("cluster evidence is missing columns: " + ", ".join(missing))

    admitted_columns = ["monthly_cluster_id", "source_general_theme_label"]
    if "membership_probability" in evidence_frame.columns:
        admitted_columns.append("membership_probability")
    admitted = evidence_frame.loc[
        evidence_frame["monthly_cluster_id"].notna(), admitted_columns
    ].copy()
    admitted["monthly_cluster_id"] = admitted["monthly_cluster_id"].astype(str)
    admitted["source_general_theme_label"] = admitted[
        "source_general_theme_label"
    ].astype(str)

    by_text = _recorded_embedding_lookup(embedding_frame)
    matrices_by_representation: dict[str, list[np.ndarray]] = {
        representation: []
        for representation in requested
        if representation != REPRESENTATIVE_EMBEDDING
    }
    diagnostics: list[dict[str, object]] = []
    expected_dimensions: int | None = None

    for row in representatives.itertuples(index=False):
        cluster_id = str(row.monthly_cluster_id)
        representative_text = str(row.monthly_representative_theme)
        cluster_rows = admitted.loc[admitted["monthly_cluster_id"] == cluster_id]
        if cluster_rows.empty:
            raise ValueError(
                f"monthly cluster {cluster_id!r} has no persisted constituent evidence"
            )

        labels = cluster_rows["source_general_theme_label"].astype(str).tolist()
        constituent_vectors: list[np.ndarray] = []
        missing_texts: list[str] = []
        for text in labels:
            vector = by_text.get(text)
            if vector is None:
                missing_texts.append(text)
            else:
                constituent_vectors.append(vector)
        if missing_texts:
            preview = "; ".join(repr(value) for value in missing_texts[:5])
            raise ValueError(
                f"monthly cluster {cluster_id!r} has {len(missing_texts)} constituent "
                "theme observation(s) missing from the recorded clustering embedding "
                f"artifact: {preview}"
            )

        representative_vector = by_text.get(representative_text)
        if representative_vector is None:
            raise ValueError(
                f"monthly cluster {cluster_id!r} representative {representative_text!r} "
                "is missing from the recorded clustering embedding artifact"
            )

        dimensions = {int(vector.size) for vector in constituent_vectors}
        dimensions.add(int(representative_vector.size))
        if len(dimensions) != 1:
            raise ValueError(
                f"monthly cluster {cluster_id!r} has inconsistent embedding dimensions: "
                f"{sorted(dimensions)}"
            )
        dimension = next(iter(dimensions))
        if expected_dimensions is None:
            expected_dimensions = dimension
        elif dimension != expected_dimensions:
            raise ValueError(
                "Stage-B benchmark representations have inconsistent dimensions across "
                f"monthly clusters: {expected_dimensions} != {dimension}"
            )

        constituent_matrix = np.vstack(constituent_vectors).astype(
            np.float64, copy=False
        )
        representative_vector64 = np.asarray(representative_vector, dtype=np.float64)
        centroid = constituent_matrix.mean(axis=0)
        _require_finite_nonzero_vector(
            centroid, context=f"monthly cluster {cluster_id!r}"
        )

        if CONSTITUENT_MEAN_EMBEDDING in matrices_by_representation:
            matrices_by_representation[CONSTITUENT_MEAN_EMBEDDING].append(centroid)

        if CONSTITUENT_UNIT_MEAN_EMBEDDING in matrices_by_representation:
            unit_matrix = _normalize_rows(
                constituent_matrix,
                context=f"monthly cluster {cluster_id!r} constituent embeddings",
            )
            unit_mean = unit_matrix.mean(axis=0)
            _require_finite_nonzero_vector(
                unit_mean, context=f"monthly cluster {cluster_id!r} unit-vector mean"
            )
            matrices_by_representation[CONSTITUENT_UNIT_MEAN_EMBEDDING].append(
                unit_mean
            )

        if (
            CONSTITUENT_PROBABILITY_WEIGHTED_MEAN_EMBEDDING
            in matrices_by_representation
        ):
            probabilities = pd.to_numeric(
                cluster_rows["membership_probability"], errors="coerce"
            ).to_numpy(dtype=np.float64)
            if (
                probabilities.shape != (len(constituent_matrix),)
                or not np.isfinite(probabilities).all()
                or np.any(probabilities < 0.0)
            ):
                raise ValueError(
                    f"monthly cluster {cluster_id!r} has invalid membership_probability "
                    "values for the probability-weighted representation"
                )
            total_probability = float(np.sum(probabilities))
            if not np.isfinite(total_probability) or total_probability <= 0.0:
                raise ValueError(
                    f"monthly cluster {cluster_id!r} has zero/invalid total "
                    "membership_probability for the probability-weighted representation"
                )
            weighted_mean = np.average(
                constituent_matrix, axis=0, weights=probabilities
            )
            _require_finite_nonzero_vector(
                weighted_mean,
                context=f"monthly cluster {cluster_id!r} probability-weighted mean",
            )
            matrices_by_representation[
                CONSTITUENT_PROBABILITY_WEIGHTED_MEAN_EMBEDDING
            ].append(weighted_mean)

        if CONSTITUENT_UNIQUE_MEAN_EMBEDDING in matrices_by_representation:
            unique_labels = sorted(set(labels))
            unique_matrix = np.vstack(
                [by_text[label] for label in unique_labels]
            ).astype(np.float64, copy=False)
            unique_mean = unique_matrix.mean(axis=0)
            _require_finite_nonzero_vector(
                unique_mean, context=f"monthly cluster {cluster_id!r} unique-label mean"
            )
            matrices_by_representation[CONSTITUENT_UNIQUE_MEAN_EMBEDDING].append(
                unique_mean
            )

        diagnostics.append(
            {
                "monthly_cluster_id": cluster_id,
                "constituent_observation_count": len(labels),
                "constituent_unique_label_count": len(set(labels)),
                **_monthly_cluster_cohesion_diagnostics(
                    constituent_matrix,
                    centroid=centroid,
                    representative_vector=representative_vector64,
                ),
            }
        )

    result: dict[str, np.ndarray] = {}
    for representation, vectors in matrices_by_representation.items():
        if not vectors:
            result[representation] = np.empty((0, 0), dtype=np.float32)
        else:
            result[representation] = np.vstack(vectors).astype(np.float32, copy=False)
    return result, pd.DataFrame(diagnostics)


def _monthly_cluster_cohesion_diagnostics(
    constituent_matrix: np.ndarray,
    *,
    centroid: np.ndarray,
    representative_vector: np.ndarray,
) -> dict[str, float]:
    centroid_scores = cosine_similarity(
        constituent_matrix, np.asarray(centroid, dtype=np.float64).reshape(1, -1)
    ).ravel()
    representative_scores = cosine_similarity(
        constituent_matrix,
        np.asarray(representative_vector, dtype=np.float64).reshape(1, -1),
    ).ravel()
    mean_pairwise, minimum_pairwise = _pairwise_cosine_metrics(constituent_matrix)
    representative_to_centroid = float(
        cosine_similarity(
            np.asarray(representative_vector, dtype=np.float64).reshape(1, -1),
            np.asarray(centroid, dtype=np.float64).reshape(1, -1),
        )[0, 0]
    )
    return {
        "mean_constituent_to_centroid_cosine": float(np.mean(centroid_scores)),
        "minimum_constituent_to_centroid_cosine": float(np.min(centroid_scores)),
        "mean_constituent_pairwise_cosine": mean_pairwise,
        "minimum_constituent_pairwise_cosine": minimum_pairwise,
        "representative_to_centroid_cosine": representative_to_centroid,
        "mean_representative_to_constituent_cosine": float(
            np.mean(representative_scores)
        ),
        "minimum_representative_to_constituent_cosine": float(
            np.min(representative_scores)
        ),
    }


def _normalize_rows(matrix: np.ndarray, *, context: str) -> np.ndarray:
    values = np.asarray(matrix, dtype=np.float64)
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    if not np.isfinite(norms).all() or np.any(norms <= 0.0):
        raise ValueError(f"cannot L2-normalize zero/non-finite {context}")
    return values / norms


def _require_finite_nonzero_vector(vector: np.ndarray, *, context: str) -> None:
    values = np.asarray(vector, dtype=np.float64)
    norm = float(np.linalg.norm(values))
    if not np.isfinite(values).all() or not np.isfinite(norm) or norm <= 0.0:
        raise ValueError(f"{context} produced a zero/non-finite embedding vector")


def _recorded_embedding_lookup(
    embedding_frame: pd.DataFrame,
) -> dict[str, np.ndarray]:
    required = {"text", "embedding"}
    missing = sorted(required.difference(embedding_frame.columns))
    if missing:
        raise ValueError("embedding artifact is missing columns: " + ", ".join(missing))

    by_text: dict[str, np.ndarray] = {}
    for row in embedding_frame[["text", "embedding"]].itertuples(index=False):
        text = str(row.text)
        vector = np.asarray(row.embedding, dtype=np.float32)
        if vector.ndim != 1 or vector.size == 0 or not np.isfinite(vector).all():
            raise ValueError(f"invalid recorded embedding for text: {text!r}")
        existing = by_text.get(text)
        if existing is not None and not np.array_equal(existing, vector):
            raise ValueError(
                f"multiple different recorded embeddings found for text: {text!r}"
            )
        by_text[text] = vector
    return by_text


def benchmark_canonicalization(
    representatives: pd.DataFrame,
    embeddings: np.ndarray,
    *,
    variants: Sequence[CanonicalizationVariant] = (
        REPRESENTATIVE_CANONICALIZATION_BENCHMARK_VARIANTS
    ),
    representation_embeddings: Mapping[str, np.ndarray] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if len(representatives) != len(embeddings):
        raise ValueError(
            "representative/embedding row mismatch: "
            f"{len(representatives)} != {len(embeddings)}"
        )
    if representatives.empty:
        raise ValueError(
            "canonicalization benchmark requires at least one monthly cluster"
        )
    if embeddings.ndim != 2 or embeddings.shape[1] == 0:
        raise ValueError(
            "canonicalization benchmark requires a non-empty embedding matrix"
        )
    if not np.isfinite(embeddings).all():
        raise ValueError(
            "canonicalization benchmark embeddings contain non-finite values"
        )

    matrices: dict[str, np.ndarray] = {REPRESENTATIVE_EMBEDDING: embeddings}
    if representation_embeddings:
        matrices.update(representation_embeddings)
    for name, matrix in matrices.items():
        _validate_representation_matrix(
            name,
            matrix,
            expected_rows=len(representatives),
            expected_dimensions=embeddings.shape[1],
        )

    representative_matrix = np.asarray(embeddings, dtype=np.float64).copy()
    observation_counts = _constituent_observation_counts(representatives)

    summary_rows: list[dict[str, object]] = []
    membership_rows: list[dict[str, object]] = []
    for variant in variants:
        if variant.min_cluster_size < 2:
            raise ValueError(
                f"variant {variant.name!r} min_cluster_size must be at least 2"
            )
        source_matrix = matrices.get(variant.representation)
        if source_matrix is None:
            raise ValueError(
                f"variant {variant.name!r} requires unavailable representation "
                f"{variant.representation!r}"
            )
        matrix = _prepare_matrix(source_matrix, normalize=variant.normalize_embeddings)
        labels = _fit_benchmark_variant(matrix, variant)
        family_keys = _family_keys(labels)
        metrics = _variant_metrics(
            matrix,
            family_keys,
            representative_matrix=representative_matrix,
            observation_counts=observation_counts,
        )
        summary_rows.append(
            {
                "variant": variant.name,
                "representation": variant.representation,
                "grouping_method": variant.grouping_method,
                "normalize_embeddings": variant.normalize_embeddings,
                "metric": variant.metric,
                "algorithm": variant.algorithm,
                "linkage": variant.linkage,
                "similarity_threshold": variant.similarity_threshold,
                "distance_threshold": _distance_threshold(variant),
                "min_cluster_size": variant.min_cluster_size,
                "min_samples": _effective_min_samples(variant),
                "monthly_cluster_count": len(representatives),
                **metrics,
            }
        )
        sizes = _family_sizes(family_keys)
        family_observation_counts = _family_observation_counts(
            family_keys, observation_counts
        )
        total_observations = (
            int(np.sum(observation_counts)) if observation_counts is not None else None
        )
        for index, row in representatives.reset_index(drop=True).iterrows():
            key = family_keys[index]
            membership_rows.append(
                {
                    "variant": variant.name,
                    "representation": variant.representation,
                    "grouping_method": variant.grouping_method,
                    "period": str(row["period"]),
                    "monthly_cluster_id": str(row["monthly_cluster_id"]),
                    "monthly_representative_theme": str(
                        row["monthly_representative_theme"]
                    ),
                    "stage_b_cluster_label": int(labels[index]),
                    "stage_b_hdbscan_label": (
                        int(labels[index])
                        if variant.grouping_method == HDBSCAN_GROUPING
                        else None
                    ),
                    "benchmark_family_key": key,
                    "singleton_noise": key.startswith("singleton:"),
                    "family_size": sizes[key],
                    "constituent_observation_count": (
                        int(row["constituent_observation_count"])
                        if "constituent_observation_count" in row.index
                        else None
                    ),
                    "constituent_unique_label_count": (
                        int(row["constituent_unique_label_count"])
                        if "constituent_unique_label_count" in row.index
                        else None
                    ),
                    "mean_constituent_to_centroid_cosine": _optional_float(
                        row, "mean_constituent_to_centroid_cosine"
                    ),
                    "minimum_constituent_to_centroid_cosine": _optional_float(
                        row, "minimum_constituent_to_centroid_cosine"
                    ),
                    "mean_constituent_pairwise_cosine": _optional_float(
                        row, "mean_constituent_pairwise_cosine"
                    ),
                    "minimum_constituent_pairwise_cosine": _optional_float(
                        row, "minimum_constituent_pairwise_cosine"
                    ),
                    "representative_to_centroid_cosine": _optional_float(
                        row, "representative_to_centroid_cosine"
                    ),
                    "mean_representative_to_constituent_cosine": _optional_float(
                        row, "mean_representative_to_constituent_cosine"
                    ),
                    "minimum_representative_to_constituent_cosine": _optional_float(
                        row, "minimum_representative_to_constituent_cosine"
                    ),
                    "family_observation_count": (
                        family_observation_counts.get(key)
                        if family_observation_counts is not None
                        else None
                    ),
                    "family_observation_share": (
                        family_observation_counts[key] / total_observations
                        if family_observation_counts is not None and total_observations
                        else None
                    ),
                }
            )

    summary = pd.DataFrame(summary_rows).sort_values("variant", kind="stable")
    membership = pd.DataFrame(membership_rows).sort_values(
        ["variant", "benchmark_family_key", "period", "monthly_cluster_id"],
        kind="stable",
    )
    return summary.reset_index(drop=True), membership.reset_index(drop=True)


def write_canonicalization_benchmark(
    themes_dir: str | Path,
    output_dir: str | Path,
    *,
    variants: Sequence[CanonicalizationVariant] = (
        DEFAULT_CANONICALIZATION_BENCHMARK_VARIANTS
    ),
) -> tuple[Path, Path]:
    representatives, evidence_frame, embedding_frame = (
        load_canonicalization_benchmark_data(themes_dir)
    )
    embeddings = align_recorded_embeddings(representatives, embedding_frame)

    representation_embeddings: dict[str, np.ndarray] = {}
    requested_representations = tuple(
        dict.fromkeys(
            variant.representation
            for variant in variants
            if variant.representation != REPRESENTATIVE_EMBEDDING
        )
    )
    if requested_representations:
        representation_embeddings, diagnostics = (
            build_stage_b_representation_embeddings(
                representatives,
                evidence_frame,
                embedding_frame,
                representations=requested_representations,
            )
        )
        representatives = representatives.merge(
            diagnostics, on="monthly_cluster_id", how="left", validate="one_to_one"
        )

    summary, membership = benchmark_canonicalization(
        representatives,
        embeddings,
        variants=variants,
        representation_embeddings=representation_embeddings,
    )
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    summary_path = target / "canonicalization_benchmark_summary.csv"
    membership_path = target / "canonicalization_benchmark_membership.csv"
    summary.to_csv(summary_path, index=False)
    membership.to_csv(membership_path, index=False)
    return summary_path, membership_path


def _validate_representation_matrix(
    name: str,
    matrix: np.ndarray,
    *,
    expected_rows: int,
    expected_dimensions: int,
) -> None:
    values = np.asarray(matrix)
    if (
        values.ndim != 2
        or values.shape[0] != expected_rows
        or values.shape[1] != expected_dimensions
    ):
        raise ValueError(
            f"canonicalization representation {name!r} has invalid shape "
            f"{values.shape}; expected ({expected_rows}, {expected_dimensions})"
        )
    if not np.isfinite(values).all():
        raise ValueError(
            f"canonicalization representation {name!r} contains non-finite values"
        )


def _prepare_matrix(embeddings: np.ndarray, *, normalize: bool) -> np.ndarray:
    matrix = np.asarray(embeddings, dtype=np.float64)
    if not normalize:
        return matrix.copy()
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms == 0.0):
        raise ValueError("cannot L2-normalize a zero-length embedding vector")
    return matrix / norms


def _fit_benchmark_variant(
    matrix: np.ndarray,
    variant: CanonicalizationVariant,
) -> np.ndarray:
    count = matrix.shape[0]
    if variant.grouping_method == HDBSCAN_GROUPING:
        effective_min_samples = _effective_min_samples(variant)
        assert effective_min_samples is not None
        if count < variant.min_cluster_size or count < effective_min_samples:
            return np.full(count, -1, dtype=int)

        if (
            variant.metric == "euclidean"
            and variant.algorithm == "auto"
            and variant.min_samples is None
        ):
            labels, _ = _fit_hdbscan(
                matrix,
                min_cluster_size=variant.min_cluster_size,
                metric="euclidean",
                clusterer_factory=None,
            )
            return labels

        clusterer = HDBSCAN(
            min_cluster_size=variant.min_cluster_size,
            min_samples=effective_min_samples,
            metric=variant.metric,
            algorithm=variant.algorithm,
            cluster_selection_method="eom",
            allow_single_cluster=False,
            copy=True,
        )
        clusterer.fit(matrix)
        labels = np.asarray(clusterer.labels_, dtype=int)
        if labels.shape != (count,):
            raise RuntimeError("benchmark HDBSCAN returned malformed labels")
        return labels

    if variant.grouping_method == AGGLOMERATIVE_GROUPING:
        if variant.metric != "cosine":
            raise ValueError(
                f"agglomerative variant {variant.name!r} must use cosine metric"
            )
        if variant.linkage not in {"average", "complete"}:
            raise ValueError(
                f"agglomerative variant {variant.name!r} must use average or "
                "complete linkage"
            )
        threshold = _distance_threshold(variant)
        assert threshold is not None
        clusterer = AgglomerativeClustering(
            n_clusters=None,
            metric="cosine",
            linkage=variant.linkage,
            distance_threshold=threshold,
            compute_full_tree=True,
            compute_distances=True,
        )
        labels = np.asarray(clusterer.fit_predict(matrix), dtype=int)
        if labels.shape != (count,):
            raise RuntimeError(
                "benchmark agglomerative clustering returned malformed labels"
            )
        return _mark_singleton_clusters_as_noise(labels)

    raise ValueError(
        f"variant {variant.name!r} has unsupported grouping method "
        f"{variant.grouping_method!r}"
    )


def _effective_min_samples(variant: CanonicalizationVariant) -> int | None:
    if variant.grouping_method != HDBSCAN_GROUPING:
        return None
    value = variant.min_samples
    if value is None:
        value = variant.min_cluster_size + 1
    if value < 1:
        raise ValueError(f"variant {variant.name!r} min_samples must be at least 1")
    return int(value)


def _distance_threshold(variant: CanonicalizationVariant) -> float | None:
    if variant.grouping_method != AGGLOMERATIVE_GROUPING:
        return None
    threshold = variant.similarity_threshold
    if threshold is None or not 0.0 <= threshold <= 1.0:
        raise ValueError(
            f"agglomerative variant {variant.name!r} similarity_threshold must be "
            "in [0, 1]"
        )
    return 1.0 - float(threshold)


def _mark_singleton_clusters_as_noise(labels: np.ndarray) -> np.ndarray:
    result = np.asarray(labels, dtype=int).copy()
    values, counts = np.unique(result, return_counts=True)
    singleton_labels = {
        int(value) for value, count in zip(values, counts) if count == 1
    }
    if singleton_labels:
        result[np.isin(result, list(singleton_labels))] = -1
    return result


def _family_keys(labels: np.ndarray) -> list[str]:
    return [
        f"cluster:{int(label)}" if int(label) >= 0 else f"singleton:{index}"
        for index, label in enumerate(labels)
    ]


def _family_sizes(keys: Sequence[str]) -> Mapping[str, int]:
    sizes: dict[str, int] = {}
    for key in keys:
        sizes[key] = sizes.get(key, 0) + 1
    return sizes


def _constituent_observation_counts(
    representatives: pd.DataFrame,
) -> np.ndarray | None:
    if "constituent_observation_count" not in representatives.columns:
        return None
    values = pd.to_numeric(
        representatives["constituent_observation_count"], errors="coerce"
    ).to_numpy(dtype=np.float64)
    if (
        values.shape != (len(representatives),)
        or not np.isfinite(values).all()
        or np.any(values <= 0.0)
    ):
        raise ValueError(
            "constituent_observation_count must contain one positive finite value "
            "per monthly cluster"
        )
    return values.astype(np.int64)


def _family_observation_counts(
    family_keys: Sequence[str], observation_counts: np.ndarray | None
) -> dict[str, int] | None:
    if observation_counts is None:
        return None
    if len(family_keys) != len(observation_counts):
        raise ValueError("family/observation-count row mismatch")
    result: dict[str, int] = {}
    for key, count in zip(family_keys, observation_counts):
        result[key] = result.get(key, 0) + int(count)
    return result


def _optional_float(row: pd.Series, column: str) -> float | None:
    if column not in row.index or pd.isna(row[column]):
        return None
    return float(row[column])


def _variant_metrics(
    matrix: np.ndarray,
    family_keys: Sequence[str],
    *,
    representative_matrix: np.ndarray,
    observation_counts: np.ndarray | None,
) -> dict[str, object]:
    sizes = _family_sizes(family_keys)
    clustered_keys = sorted(key for key in sizes if key.startswith("cluster:"))
    singleton_keys = sorted(key for key in sizes if key.startswith("singleton:"))
    largest_family_size = max(sizes.values()) if sizes else 0

    family_cosines: list[tuple[int, float, float]] = []
    representative_family_cosines: list[tuple[int, float, float]] = []
    for key in clustered_keys:
        indices = [index for index, value in enumerate(family_keys) if value == key]
        mean_cosine, min_cosine = _pairwise_cosine_metrics(matrix[indices])
        family_cosines.append((len(indices), mean_cosine, min_cosine))
        representative_mean, representative_min = _pairwise_cosine_metrics(
            representative_matrix[indices]
        )
        representative_family_cosines.append(
            (len(indices), representative_mean, representative_min)
        )

    clustered_points = sum(sizes[key] for key in clustered_keys)
    if clustered_points:
        weighted_mean = sum(size * mean for size, mean, _ in family_cosines) / sum(
            size for size, _, _ in family_cosines
        )
        minimum_family_cosine = min(value for _, _, value in family_cosines)
        weighted_representative_mean = sum(
            size * mean for size, mean, _ in representative_family_cosines
        ) / sum(size for size, _, _ in representative_family_cosines)
        minimum_representative_cosine = min(
            value for _, _, value in representative_family_cosines
        )
    else:
        weighted_mean = float("nan")
        minimum_family_cosine = float("nan")
        weighted_representative_mean = float("nan")
        minimum_representative_cosine = float("nan")

    family_observation_counts = _family_observation_counts(
        family_keys, observation_counts
    )
    if family_observation_counts:
        total_observations = int(sum(family_observation_counts.values()))
        largest_family_observation_count = max(family_observation_counts.values())
        largest_family_observation_share = (
            largest_family_observation_count / total_observations
            if total_observations
            else float("nan")
        )
    else:
        largest_family_observation_count = float("nan")
        largest_family_observation_share = float("nan")

    return {
        "canonical_family_count": len(sizes),
        "clustered_family_count": len(clustered_keys),
        "singleton_noise_count": len(singleton_keys),
        "clustered_monthly_clusters": clustered_points,
        "noise_monthly_clusters": len(singleton_keys),
        "largest_family_size": largest_family_size,
        "largest_family_share": largest_family_size / len(family_keys),
        "largest_family_observation_count": largest_family_observation_count,
        "largest_family_observation_share": largest_family_observation_share,
        "weighted_mean_within_family_cosine": weighted_mean,
        "minimum_within_family_cosine": minimum_family_cosine,
        "weighted_mean_within_family_representative_cosine": (
            weighted_representative_mean
        ),
        "minimum_within_family_representative_cosine": (minimum_representative_cosine),
    }


def _pairwise_cosine_metrics(matrix: np.ndarray) -> tuple[float, float]:
    if len(matrix) <= 1:
        return 1.0, 1.0
    similarities = cosine_similarity(matrix)
    upper = similarities[np.triu_indices(len(matrix), k=1)]
    return float(np.mean(upper)), float(np.min(upper))
