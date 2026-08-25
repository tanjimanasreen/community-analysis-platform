from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.themes.monthly_cluster_benchmark import (
    BENCHMARK_SOURCE_MONTHLY_CLUSTER_CONTRACT_VERSION,
    COSINE,
    DEFAULT_MONTHLY_CLUSTERING_VARIANTS,
    DIAGNOSTIC_ALLOW_SINGLE_VARIANT,
    PRODUCTION_BASELINE_VARIANT,
    RAW_EUCLIDEAN,
    UNIT_EUCLIDEAN,
    MonthlyClusteringVariant,
    _identical_embedding_assignment_metrics,
    _fit_variant,
    _geometry_matrix,
    _recorded_embedding_fingerprints,
    benchmark_monthly_clustering,
    load_monthly_clustering_benchmark_data,
    write_monthly_clustering_benchmark,
)
from src.themes.theme_clustering import (
    DEFAULT_MIN_CLUSTER_SIZE,
    MONTHLY_CLUSTER_ALLOW_SINGLE_CLUSTER,
    MONTHLY_CLUSTER_SELECTION_METHOD,
    ThemeObservation,
    _fit_hdbscan,
    _l2_normalize_embeddings,
    _monthly_clusters,
)


def _frames(
    matrix: np.ndarray,
    *,
    period: str = "2019-01",
    labels: list[str] | None = None,
    production_labels: np.ndarray | None = None,
    production_probabilities: np.ndarray | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    values = np.asarray(matrix, dtype=np.float32)
    texts = labels or [f"Theme {index}" for index in range(len(values))]
    if production_labels is None or production_probabilities is None:
        production_labels, production_probabilities = _fit_hdbscan(
            values,
            min_cluster_size=DEFAULT_MIN_CLUSTER_SIZE,
            metric="euclidean",
            clusterer_factory=None,
            cluster_selection_method="eom",
            allow_single_cluster=False,
        )

    observations = [
        ThemeObservation(
            period=period,
            pair_key=f"{index}|{index + 100}",
            absolute_community=str(index),
            weighted_community=str(index + 100),
            label=text,
            keywords=(),
            source_index=index,
        )
        for index, text in enumerate(texts)
    ]
    monthly_clusters = _monthly_clusters(
        period,
        observations,
        values,
        production_labels,
        production_probabilities,
    )
    cluster_by_observation = {
        index: cluster
        for cluster in monthly_clusters
        for index in cluster.observation_indices
    }

    evidence = pd.DataFrame(
        [
            {
                "period": period,
                "absolute_community": str(index),
                "weighted_community": str(index + 100),
                "pair_key": f"{index}|{index + 100}",
                "source_index": index,
                "source_general_theme_label": text,
                "hdbscan_label": int(production_labels[index]),
                "membership_probability": round(
                    float(production_probabilities[index]), 8
                ),
                "is_monthly_noise": index not in cluster_by_observation,
                "monthly_cluster_id": (
                    cluster_by_observation[index].cluster_id
                    if index in cluster_by_observation
                    else None
                ),
                "monthly_representative_theme": (
                    cluster_by_observation[index].representative_theme
                    if index in cluster_by_observation
                    else None
                ),
                "monthly_cluster_contract_version": (
                    BENCHMARK_SOURCE_MONTHLY_CLUSTER_CONTRACT_VERSION
                ),
            }
            for index, text in enumerate(texts)
        ]
    )
    embedding_frame = pd.DataFrame(
        [
            {"text": text, "embedding": vector.tolist()}
            for text, vector in zip(texts, values)
        ]
    )
    return evidence, embedding_frame


def _variant(name: str) -> MonthlyClusteringVariant:
    return next(
        variant
        for variant in DEFAULT_MONTHLY_CLUSTERING_VARIANTS
        if variant.name == name
    )


def test_default_grid_is_controlled_and_keeps_diagnostic_out_of_main_candidates():
    main = [
        variant
        for variant in DEFAULT_MONTHLY_CLUSTERING_VARIANTS
        if not variant.diagnostic_only
    ]
    diagnostic = [
        variant
        for variant in DEFAULT_MONTHLY_CLUSTERING_VARIANTS
        if variant.diagnostic_only
    ]

    assert len(main) == 12
    assert len(diagnostic) == 1
    assert diagnostic[0].name == DIAGNOSTIC_ALLOW_SINGLE_VARIANT
    assert diagnostic[0].allow_single_cluster is True
    assert {variant.geometry for variant in main} == {
        RAW_EUCLIDEAN,
        UNIT_EUCLIDEAN,
        COSINE,
    }
    assert {variant.cluster_selection_method for variant in main} == {"eom", "leaf"}
    assert {variant.min_samples for variant in main} == {2, 3}
    baseline = _variant(PRODUCTION_BASELINE_VARIANT)
    assert baseline.geometry == RAW_EUCLIDEAN
    assert baseline.cluster_selection_method == "eom"
    assert baseline.min_samples == 3
    assert baseline.allow_single_cluster is False


def test_default_grid_executes_all_variants_without_mutating_production_defaults():
    matrix = np.array(
        [
            [1.00, 0.00],
            [0.99, 0.01],
            [0.98, 0.02],
            [0.97, 0.03],
            [0.00, 1.00],
            [0.01, 0.99],
            [0.02, 0.98],
            [0.03, 0.97],
        ]
    )
    evidence, embeddings = _frames(matrix)

    summary, periods, _, membership = benchmark_monthly_clustering(
        evidence,
        embeddings,
    )

    assert len(summary) == 13
    assert len(periods) == 13
    assert len(membership) == 13 * len(evidence)
    assert set(summary["variant"]) == {
        variant.name for variant in DEFAULT_MONTHLY_CLUSTERING_VARIANTS
    }
    baseline = summary.set_index("variant").loc[PRODUCTION_BASELINE_VARIANT]
    assert baseline["geometry"] == RAW_EUCLIDEAN
    assert baseline["cluster_selection_method"] == "eom"
    assert baseline["min_samples"] == 3
    assert bool(baseline["allow_single_cluster"]) is False


def test_loader_accepts_run_local_theme_clusters_layout(tmp_path, monkeypatch):
    evidence_dir = tmp_path / "evidence"
    embedding_dir = tmp_path / "embeddings"
    evidence_dir.mkdir()
    embedding_dir.mkdir()
    evidence_path = evidence_dir / "2019-01.parquet"
    embedding_path = embedding_dir / "clustering_general_themes.parquet"
    evidence_path.touch()
    embedding_path.touch()

    evidence, embeddings = _frames(
        np.array([[0.0, 0.0], [10.0, 0.0], [0.0, 10.0], [10.0, 10.0]])
    )

    def fake_read_parquet(path):
        return evidence.copy() if Path(path) == evidence_path else embeddings.copy()

    monkeypatch.setattr(pd, "read_parquet", fake_read_parquet)

    loaded_evidence, loaded_embeddings = load_monthly_clustering_benchmark_data(
        tmp_path
    )

    pd.testing.assert_frame_equal(loaded_evidence, evidence)
    pd.testing.assert_frame_equal(loaded_embeddings, embeddings)


def test_loader_preserves_published_data_themes_layout(tmp_path, monkeypatch):
    evidence_dir = tmp_path / "clusters" / "evidence"
    embedding_dir = tmp_path / "embeddings"
    evidence_dir.mkdir(parents=True)
    embedding_dir.mkdir()
    evidence_path = evidence_dir / "2019-01.parquet"
    embedding_path = embedding_dir / "clustering_general_themes.parquet"
    evidence_path.touch()
    embedding_path.touch()

    evidence, embeddings = _frames(
        np.array([[0.0, 0.0], [10.0, 0.0], [0.0, 10.0], [10.0, 10.0]])
    )

    def fake_read_parquet(path):
        return evidence.copy() if Path(path) == evidence_path else embeddings.copy()

    monkeypatch.setattr(pd, "read_parquet", fake_read_parquet)

    loaded_evidence, loaded_embeddings = load_monthly_clustering_benchmark_data(
        tmp_path
    )

    pd.testing.assert_frame_equal(loaded_evidence, evidence)
    pd.testing.assert_frame_equal(loaded_embeddings, embeddings)


def test_production_baseline_reconstructs_exact_noise_partition_and_probabilities():
    matrix = np.array(
        [
            [0.00, 0.00],
            [0.02, 0.00],
            [0.00, 0.02],
            [1.00, 1.00],
            [1.02, 1.00],
            [1.00, 1.02],
        ]
    )
    evidence, embeddings = _frames(matrix)

    summary, periods, clusters, membership = benchmark_monthly_clustering(
        evidence,
        embeddings,
        variants=(_variant(PRODUCTION_BASELINE_VARIANT),),
    )

    assert summary.loc[0, "cluster_count"] == 2
    assert summary.loc[0, "noise_count"] == 0
    assert summary.loc[0, "source_monthly_cluster_contract_version"] == "2.2"
    assert summary.loc[0, "stage_b_canonicalization_contract_version"] == "4.0"
    assert summary.loc[0, "stage_b_similarity_threshold"] == 0.65
    assert periods.loc[0, "cluster_count"] == 2
    assert clusters["observation_count"].tolist() == [3, 3]
    assert len(membership) == len(evidence)
    assert membership["is_noise"].sum() == 0


def test_production_baseline_mismatch_aborts_before_candidate_comparison():
    matrix = np.array(
        [
            [0.00, 0.00],
            [0.02, 0.00],
            [0.00, 0.02],
            [1.00, 1.00],
            [1.02, 1.00],
            [1.00, 1.02],
        ]
    )
    evidence, embeddings = _frames(matrix)
    evidence.loc[0, "hdbscan_label"] = -1

    try:
        benchmark_monthly_clustering(
            evidence,
            embeddings,
            variants=(_variant(PRODUCTION_BASELINE_VARIANT),),
        )
    except ValueError as exc:
        message = str(exc)
        assert "baseline fidelity failed" in message
        assert "noise membership differs" in message
    else:
        raise AssertionError("expected baseline fidelity failure")


def test_production_baseline_cluster_artifact_mismatch_aborts():
    matrix = np.array(
        [
            [0.00, 0.00],
            [0.02, 0.00],
            [0.00, 0.02],
            [1.00, 1.00],
            [1.02, 1.00],
            [1.00, 1.02],
        ]
    )
    evidence, embeddings = _frames(matrix)
    clustered_index = evidence.index[evidence["hdbscan_label"] >= 0][0]
    evidence.loc[clustered_index, "monthly_cluster_id"] = "mc_wrong"

    try:
        benchmark_monthly_clustering(
            evidence,
            embeddings,
            variants=(_variant(PRODUCTION_BASELINE_VARIANT),),
        )
    except ValueError as exc:
        message = str(exc)
        assert "baseline fidelity failed" in message
        assert "monthly_cluster_id differs" in message
    else:
        raise AssertionError("expected persisted cluster-artifact fidelity failure")


def test_all_noise_fixture_is_reported_without_forcing_a_cluster():
    matrix = np.array(
        [[0.0, 0.0], [10.0, 0.0], [0.0, 10.0], [10.0, 10.0]], dtype=float
    )
    evidence, embeddings = _frames(matrix)

    summary, periods, clusters, membership = benchmark_monthly_clustering(
        evidence,
        embeddings,
        variants=(_variant(PRODUCTION_BASELINE_VARIANT),),
    )

    assert summary.loc[0, "cluster_count"] == 0
    assert summary.loc[0, "noise_rate"] == 1.0
    assert periods.loc[0, "cluster_count"] == 0
    assert clusters.empty
    assert membership["is_noise"].all()


def test_allow_single_cluster_variant_is_reported_as_diagnostic_only():
    matrix = np.array(
        [[0.0, 0.0], [10.0, 0.0], [0.0, 10.0], [10.0, 10.0]], dtype=float
    )
    evidence, embeddings = _frames(matrix)

    summary, periods, _, _ = benchmark_monthly_clustering(
        evidence,
        embeddings,
        variants=(_variant(DIAGNOSTIC_ALLOW_SINGLE_VARIANT),),
    )

    assert bool(summary.loc[0, "diagnostic_only"]) is True
    assert bool(summary.loc[0, "allow_single_cluster"]) is True
    assert summary.loc[0, "cluster_count"] == 1
    assert summary.loc[0, "noise_count"] == 0
    assert bool(periods.loc[0, "diagnostic_only"]) is True


def test_leaf_fixture_exposes_finer_structure_than_eom_parent_cluster():
    rng = np.random.default_rng(0)
    sigma = 0.04
    matrix = np.vstack(
        [
            rng.normal([0.00, 0.00], sigma, (10, 2)),
            rng.normal([0.12, 0.00], sigma, (10, 2)),
            rng.normal([0.24, 0.00], sigma, (10, 2)),
            rng.normal([2.00, 2.00], sigma, (8, 2)),
        ]
    )
    evidence, embeddings = _frames(matrix)
    variants = (
        _variant("raw_euclidean_eom_ms3"),
        _variant("raw_euclidean_leaf_ms3"),
    )

    summary, periods, _, _ = benchmark_monthly_clustering(
        evidence, embeddings, variants=variants
    )
    by_variant = periods.set_index("variant")

    assert by_variant.loc["raw_euclidean_eom_ms3", "largest_cluster_size"] >= 25
    assert (
        by_variant.loc["raw_euclidean_leaf_ms3", "largest_cluster_size"]
        < by_variant.loc["raw_euclidean_eom_ms3", "largest_cluster_size"]
    )
    assert (
        by_variant.loc["raw_euclidean_leaf_ms3", "cluster_count"]
        > by_variant.loc["raw_euclidean_eom_ms3", "cluster_count"]
    )
    assert set(summary["variant"]) == {
        "raw_euclidean_eom_ms3",
        "raw_euclidean_leaf_ms3",
    }


def test_normalized_and_cosine_geometry_distinguish_direction_from_vector_norm():
    matrix = np.array(
        [
            [1.0, 0.0],
            [10.0, 0.0],
            [11.0, 0.0],
            [0.0, 1.0],
            [0.0, 10.0],
            [0.0, 11.0],
        ]
    )
    evidence, embeddings = _frames(matrix)
    variants = (
        _variant("raw_euclidean_eom_ms2"),
        _variant("unit_euclidean_eom_ms2"),
        _variant("cosine_eom_ms2"),
    )

    _, _, _, membership = benchmark_monthly_clustering(
        evidence,
        embeddings,
        variants=variants,
        validate_baseline=True,
    )

    partitions = {}
    for variant in [value.name for value in variants]:
        labels = membership.loc[
            membership["variant"] == variant, "benchmark_cluster_label"
        ].to_numpy(dtype=int)
        partitions[variant] = labels[:, None] == labels

    assert not np.array_equal(
        partitions["raw_euclidean_eom_ms2"],
        partitions["unit_euclidean_eom_ms2"],
    )
    assert np.array_equal(
        partitions["unit_euclidean_eom_ms2"], partitions["cosine_eom_ms2"]
    )


def test_unit_euclidean_leaf_ms3_matches_promoted_production_stage_a_contract():
    raw = np.asarray(
        [
            [1.00, 0.10],
            [1.05, 0.11],
            [0.95, 0.09],
            [0.10, 1.00],
            [0.11, 1.05],
            [0.09, 0.95],
        ],
        dtype=np.float32,
    )
    candidate = _variant("unit_euclidean_leaf_ms3")

    benchmark_matrix = _geometry_matrix(raw, candidate.geometry)
    benchmark_labels, benchmark_probabilities = _fit_variant(
        benchmark_matrix, candidate
    )

    production_matrix = _l2_normalize_embeddings(
        raw,
        context="production parity embeddings",
    )
    production_labels, production_probabilities = _fit_hdbscan(
        production_matrix,
        min_cluster_size=DEFAULT_MIN_CLUSTER_SIZE,
        metric="euclidean",
        clusterer_factory=None,
        cluster_selection_method=MONTHLY_CLUSTER_SELECTION_METHOD,
        allow_single_cluster=MONTHLY_CLUSTER_ALLOW_SINGLE_CLUSTER,
    )

    np.testing.assert_array_equal(production_labels, benchmark_labels)
    np.testing.assert_allclose(
        production_probabilities,
        benchmark_probabilities,
        rtol=0.0,
        atol=0.0,
    )


def test_occurrence_multiplicity_is_preserved_when_recorded_vectors_are_deduplicated():
    matrix = np.array(
        [
            [1.0, 0.0],
            [1.0, 0.0],
            [0.99, 0.01],
            [0.0, 1.0],
            [0.0, 1.0],
            [0.01, 0.99],
        ]
    )
    labels = ["Theme A", "Theme A", "Theme B", "Theme C", "Theme C", "Theme D"]
    evidence, _ = _frames(matrix, labels=labels)
    embeddings = pd.DataFrame(
        [
            {"text": "Theme A", "embedding": [1.0, 0.0]},
            {"text": "Theme B", "embedding": [0.99, 0.01]},
            {"text": "Theme C", "embedding": [0.0, 1.0]},
            {"text": "Theme D", "embedding": [0.01, 0.99]},
        ]
    )

    summary, _, _, membership = benchmark_monthly_clustering(
        evidence,
        embeddings,
        variants=(_variant(PRODUCTION_BASELINE_VARIANT),),
    )

    assert summary.loc[0, "observation_count"] == 6
    assert len(membership) == 6
    assert membership["source_general_theme_label"].value_counts()["Theme A"] == 2
    assert membership["source_general_theme_label"].value_counts()["Theme C"] == 2


def test_identical_recorded_embeddings_split_across_clusters_fail_consistency_gate():
    matrix = np.array(
        [
            [1.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
            [0.0, 1.0],
        ],
        dtype=np.float32,
    )
    fingerprints = _recorded_embedding_fingerprints(matrix)
    metrics = _identical_embedding_assignment_metrics(
        fingerprints,
        np.array([0, 1, 2, 2], dtype=int),
    )

    assert metrics["identical_embedding_group_count"] == 2
    assert metrics["identical_embedding_observation_count"] == 4
    assert metrics["identical_embedding_non_noise_split_group_count"] == 1
    assert metrics["identical_embedding_non_noise_split_observation_count"] == 2
    assert metrics["identical_embedding_max_non_noise_cluster_count"] == 2
    assert metrics["identical_embedding_non_noise_consistency_pass"] is False


def test_noise_boundary_tie_is_reported_without_failing_non_noise_consistency_gate():
    matrix = np.array(
        [
            [1.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
            [0.0, 1.0],
        ],
        dtype=np.float32,
    )
    fingerprints = _recorded_embedding_fingerprints(matrix)
    metrics = _identical_embedding_assignment_metrics(
        fingerprints,
        np.array([-1, 0, 2, 2], dtype=int),
    )

    assert metrics["identical_embedding_non_noise_split_group_count"] == 0
    assert metrics["identical_embedding_noise_boundary_split_group_count"] == 1
    assert metrics["identical_embedding_noise_boundary_split_observation_count"] == 2
    assert metrics["identical_embedding_max_non_noise_cluster_count"] == 1
    assert metrics["identical_embedding_non_noise_consistency_pass"] is True


def test_membership_and_summary_expose_identical_embedding_consistency_diagnostics():
    matrix = np.array(
        [
            [1.0, 0.0],
            [1.0, 0.0],
            [0.99, 0.01],
            [0.0, 1.0],
            [0.0, 1.0],
            [0.01, 0.99],
        ]
    )
    labels = ["Theme A", "Theme A", "Theme B", "Theme C", "Theme C", "Theme D"]
    evidence, _ = _frames(matrix, labels=labels)
    embeddings = pd.DataFrame(
        [
            {"text": "Theme A", "embedding": [1.0, 0.0]},
            {"text": "Theme B", "embedding": [0.99, 0.01]},
            {"text": "Theme C", "embedding": [0.0, 1.0]},
            {"text": "Theme D", "embedding": [0.01, 0.99]},
        ]
    )

    summary, periods, _, membership = benchmark_monthly_clustering(
        evidence,
        embeddings,
        variants=(_variant(PRODUCTION_BASELINE_VARIANT),),
    )

    assert summary.loc[0, "identical_embedding_group_count"] == 2
    assert summary.loc[0, "identical_embedding_non_noise_split_group_count"] == 0
    assert bool(summary.loc[0, "identical_embedding_non_noise_consistency_pass"])
    assert periods.loc[0, "identical_embedding_group_count"] == 2
    assert periods.loc[0, "identical_embedding_non_noise_split_group_count"] == 0
    assert bool(periods.loc[0, "identical_embedding_non_noise_consistency_pass"])
    assert membership["recorded_embedding_sha256"].str.len().eq(64).all()
    assert membership.loc[
        membership["source_general_theme_label"] == "Theme A",
        "recorded_embedding_group_size",
    ].eq(2).all()
    assert membership.loc[
        membership["source_general_theme_label"] == "Theme C",
        "recorded_embedding_group_size",
    ].eq(2).all()


def test_cluster_outputs_include_independent_cosine_cohesion_and_stage_b_impact():
    first = np.array(
        [
            [1.0, 0.0],
            [0.99, 0.01],
            [0.98, 0.02],
            [0.0, 1.0],
            [0.01, 0.99],
            [0.02, 0.98],
        ]
    )
    second = np.array(
        [
            [0.995, 0.005],
            [0.985, 0.015],
            [0.975, 0.025],
            [-1.0, 0.0],
            [-0.99, 0.01],
            [-0.98, 0.02],
        ]
    )
    evidence_a, embeddings_a = _frames(first, period="2019-01")
    month2_labels = [f"Month2 Theme {index}" for index in range(len(second))]
    evidence_b, embeddings_b = _frames(
        second,
        period="2019-02",
        labels=month2_labels,
    )
    evidence = pd.concat([evidence_a, evidence_b], ignore_index=True)
    embeddings = pd.concat([embeddings_a, embeddings_b], ignore_index=True)

    summary, periods, clusters, _ = benchmark_monthly_clustering(
        evidence,
        embeddings,
        variants=(_variant(PRODUCTION_BASELINE_VARIANT),),
    )

    assert clusters["mean_pairwise_cosine"].notna().all()
    assert clusters["minimum_pairwise_cosine"].notna().all()
    assert "max_intercluster_representative_cosine" in periods.columns
    assert periods["max_intercluster_representative_cosine"].notna().all()
    assert (
        summary.loc[0, "stage_b_monthly_cluster_count"]
        == summary.loc[0, "cluster_count"]
    )
    assert (
        1
        <= summary.loc[0, "stage_b_canonical_family_count"]
        <= summary.loc[0, "cluster_count"]
    )
    assert 0.0 <= summary.loc[0, "stage_b_largest_family_cluster_share"] <= 1.0


def test_writer_emits_four_csvs_without_provider_or_embedding_calls(
    tmp_path, monkeypatch
):
    matrix = np.array(
        [
            [0.00, 0.00],
            [0.02, 0.00],
            [0.00, 0.02],
            [1.00, 1.00],
            [1.02, 1.00],
            [1.00, 1.02],
        ]
    )
    evidence, embeddings = _frames(matrix)
    monkeypatch.setattr(
        "src.themes.monthly_cluster_benchmark.load_monthly_clustering_benchmark_data",
        lambda _themes_dir: (evidence, embeddings),
    )

    paths = write_monthly_clustering_benchmark(
        "unused",
        tmp_path,
        variants=(_variant(PRODUCTION_BASELINE_VARIANT),),
    )

    assert [path.name for path in paths] == [
        "monthly_clustering_benchmark_summary.csv",
        "monthly_clustering_benchmark_periods.csv",
        "monthly_clustering_benchmark_clusters.csv",
        "monthly_clustering_benchmark_membership.csv",
    ]
    assert all(path.is_file() for path in paths)


def test_current_contract_guard_rejects_pre_plan085_evidence():
    matrix = np.array(
        [[0.0, 0.0], [10.0, 0.0], [0.0, 10.0], [10.0, 10.0]], dtype=float
    )
    evidence, embeddings = _frames(matrix)
    evidence["monthly_cluster_contract_version"] = "2.1"

    try:
        benchmark_monthly_clustering(
            evidence,
            embeddings,
            variants=(_variant(PRODUCTION_BASELINE_VARIANT),),
        )
    except ValueError as exc:
        assert "requires benchmark source Stage-A contract 2.2" in str(exc)
    else:
        raise AssertionError("expected pre-Plan-085 contract rejection")


def test_cli_registers_and_dispatches_monthly_cluster_benchmark(monkeypatch):
    import sys

    import src.cli as cli

    called = {}

    def fake_run(themes_dir, out_dir):
        called["args"] = (themes_dir, out_dir)

    monkeypatch.setattr(cli, "_run_monthly_theme_cluster_benchmark_command", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cli.py",
            "monthly-theme-cluster-benchmark",
            "--themes-dir",
            "/tmp/themes",
            "--out-dir",
            "/tmp/out",
        ],
    )

    cli.main()

    assert called["args"] == ("/tmp/themes", "/tmp/out")
