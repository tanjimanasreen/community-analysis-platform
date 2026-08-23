from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.themes.canonical_benchmark import (
    AGGLOMERATIVE_GROUPING,
    CONSTITUENT_MEAN_EMBEDDING,
    CONSTITUENT_PROBABILITY_WEIGHTED_MEAN_EMBEDDING,
    CONSTITUENT_UNIQUE_MEAN_EMBEDDING,
    CONSTITUENT_UNIT_MEAN_EMBEDDING,
    REPRESENTATIVE_EMBEDDING,
    CanonicalizationVariant,
    align_recorded_embeddings,
    benchmark_canonicalization,
    build_stage_b_representation_embeddings,
    extract_monthly_representatives,
    load_canonicalization_benchmark_data,
)
from src.themes.theme_clustering import (
    MonthlyCluster,
    _canonicalize_monthly_clusters,
    _fit_hdbscan,
)


def _evidence(period: str, cluster_id: str, representative: str, repeats: int = 2):
    return pd.DataFrame(
        [
            {
                "period": period,
                "monthly_cluster_id": cluster_id,
                "monthly_representative_theme": representative,
            }
            for _ in range(repeats)
        ]
    )


def _benchmark_evidence_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "period": "2019-01",
                "monthly_cluster_id": "mc_a",
                "monthly_representative_theme": "Theme A",
                "source_general_theme_label": "Theme A",
                "membership_probability": 1.0,
            }
        ]
    )


def _benchmark_embedding_frame() -> pd.DataFrame:
    return pd.DataFrame([{"text": "Theme A", "embedding": [1.0, 0.0]}])


def test_load_benchmark_data_accepts_run_local_theme_clusters_layout(
    tmp_path, monkeypatch
):
    evidence_dir = tmp_path / "evidence"
    embedding_dir = tmp_path / "embeddings"
    evidence_dir.mkdir()
    embedding_dir.mkdir()
    evidence_path = evidence_dir / "2019-01.parquet"
    embedding_path = embedding_dir / "clustering_general_themes.parquet"
    evidence_path.touch()
    embedding_path.touch()

    evidence = _benchmark_evidence_frame()
    embeddings = _benchmark_embedding_frame()

    def fake_read_parquet(path):
        return evidence.copy() if Path(path) == evidence_path else embeddings.copy()

    monkeypatch.setattr(pd, "read_parquet", fake_read_parquet)

    representatives, loaded_evidence, loaded_embeddings = (
        load_canonicalization_benchmark_data(tmp_path)
    )

    assert representatives["monthly_cluster_id"].tolist() == ["mc_a"]
    pd.testing.assert_frame_equal(loaded_evidence, evidence)
    pd.testing.assert_frame_equal(loaded_embeddings, embeddings)


def test_load_benchmark_data_preserves_published_data_themes_layout(
    tmp_path, monkeypatch
):
    evidence_dir = tmp_path / "clusters" / "evidence"
    embedding_dir = tmp_path / "embeddings"
    evidence_dir.mkdir(parents=True)
    embedding_dir.mkdir()
    evidence_path = evidence_dir / "2019-01.parquet"
    embedding_path = embedding_dir / "clustering_general_themes.parquet"
    evidence_path.touch()
    embedding_path.touch()

    evidence = _benchmark_evidence_frame()
    embeddings = _benchmark_embedding_frame()

    def fake_read_parquet(path):
        return evidence.copy() if Path(path) == evidence_path else embeddings.copy()

    monkeypatch.setattr(pd, "read_parquet", fake_read_parquet)

    representatives, loaded_evidence, loaded_embeddings = (
        load_canonicalization_benchmark_data(tmp_path)
    )

    assert representatives["monthly_cluster_id"].tolist() == ["mc_a"]
    pd.testing.assert_frame_equal(loaded_evidence, evidence)
    pd.testing.assert_frame_equal(loaded_embeddings, embeddings)


def test_load_benchmark_data_missing_layout_lists_checked_evidence_paths(tmp_path):
    try:
        load_canonicalization_benchmark_data(tmp_path)
    except FileNotFoundError as exc:
        message = str(exc)
        assert str(tmp_path / "evidence") in message
        assert str(tmp_path / "clusters" / "evidence") in message
    else:
        raise AssertionError("expected missing benchmark evidence layout to fail")


def test_load_benchmark_data_missing_embedding_lists_checked_paths(tmp_path):
    (tmp_path / "evidence").mkdir()

    try:
        load_canonicalization_benchmark_data(tmp_path)
    except FileNotFoundError as exc:
        message = str(exc)
        assert (
            str(tmp_path / "embeddings" / "clustering_general_themes.parquet")
            in message
        )
        assert (
            str(
                tmp_path
                / "clusters"
                / "embeddings"
                / "clustering_general_themes.parquet"
            )
            in message
        )
    else:
        raise AssertionError("expected missing benchmark embedding layout to fail")


def test_extract_monthly_representatives_deduplicates_observation_rows():
    reps = extract_monthly_representatives(
        [
            _evidence("2019-01", "mc_a", "Theme A", repeats=3),
            _evidence("2019-02", "mc_b", "Theme B", repeats=4),
        ]
    )

    assert reps.to_dict("records") == [
        {
            "period": "2019-01",
            "monthly_cluster_id": "mc_a",
            "monthly_representative_theme": "Theme A",
        },
        {
            "period": "2019-02",
            "monthly_cluster_id": "mc_b",
            "monthly_representative_theme": "Theme B",
        },
    ]


def test_extract_monthly_representatives_rejects_conflicting_cluster_identity():
    frame = pd.DataFrame(
        [
            {
                "period": "2019-01",
                "monthly_cluster_id": "mc_a",
                "monthly_representative_theme": "Theme A",
            },
            {
                "period": "2019-01",
                "monthly_cluster_id": "mc_a",
                "monthly_representative_theme": "Different Theme",
            },
        ]
    )

    try:
        extract_monthly_representatives([frame])
    except ValueError as exc:
        assert "inconsistent" in str(exc)
    else:
        raise AssertionError("expected conflicting monthly cluster identity to fail")


def test_align_recorded_embeddings_uses_exact_representative_text():
    representatives = pd.DataFrame(
        [
            {
                "period": "2019-01",
                "monthly_cluster_id": "mc_a",
                "monthly_representative_theme": "Theme A",
            },
            {
                "period": "2019-02",
                "monthly_cluster_id": "mc_b",
                "monthly_representative_theme": "Theme B",
            },
        ]
    )
    embeddings = pd.DataFrame(
        [
            {"text": "Theme B", "embedding": [0.0, 1.0]},
            {"text": "Theme A", "embedding": [1.0, 0.0]},
        ]
    )

    matrix = align_recorded_embeddings(representatives, embeddings)

    np.testing.assert_allclose(matrix, [[1.0, 0.0], [0.0, 1.0]])
    assert matrix.dtype == np.float32


def test_baseline_variant_reproduces_current_stage_b_hdbscan_partition():
    representatives = pd.DataFrame(
        [
            {
                "period": f"2019-{index + 1:02d}",
                "monthly_cluster_id": f"mc_{index}",
                "monthly_representative_theme": f"Theme {index}",
            }
            for index in range(12)
        ]
    )
    matrix = np.asarray(
        [
            [0.0, 0.0],
            [0.01, 0.0],
            [0.0, 0.01],
            [0.02, 0.01],
            [-0.01, 0.0],
            [0.01, 0.02],
            [10.0, 10.0],
            [10.01, 10.0],
            [10.0, 10.01],
            [10.02, 10.01],
            [9.99, 10.0],
            [10.01, 10.02],
        ],
        dtype=np.float32,
    )
    baseline = CanonicalizationVariant(
        name="baseline",
        normalize_embeddings=False,
        metric="euclidean",
        min_cluster_size=2,
    )

    _, membership = benchmark_canonicalization(
        representatives, matrix, variants=[baseline]
    )
    expected_labels, _ = _fit_hdbscan(
        matrix,
        min_cluster_size=2,
        metric="euclidean",
        clusterer_factory=None,
    )

    actual_groups = {
        frozenset(group.index.tolist())
        for _, group in membership.loc[~membership["singleton_noise"]].groupby(
            "benchmark_family_key"
        )
    }
    expected_groups = {
        frozenset(np.flatnonzero(expected_labels == label).tolist())
        for label in set(expected_labels.tolist())
        if label >= 0
    }
    assert actual_groups == expected_groups


def test_benchmark_reports_family_size_and_cosine_cohesion_without_mutating_input():
    representatives = pd.DataFrame(
        [
            {
                "period": f"2019-{index + 1:02d}",
                "monthly_cluster_id": f"mc_{index}",
                "monthly_representative_theme": f"Theme {index}",
            }
            for index in range(6)
        ]
    )
    matrix = np.asarray(
        [
            [1.0, 0.0],
            [0.99, 0.01],
            [0.98, 0.02],
            [0.0, 1.0],
            [0.01, 0.99],
            [0.02, 0.98],
        ],
        dtype=np.float32,
    )
    original = matrix.copy()
    variant = CanonicalizationVariant(
        name="normalized",
        normalize_embeddings=True,
        metric="euclidean",
        min_cluster_size=2,
    )

    summary, membership = benchmark_canonicalization(
        representatives, matrix, variants=[variant]
    )

    np.testing.assert_array_equal(matrix, original)
    row = summary.iloc[0]
    assert row["monthly_cluster_count"] == 6
    assert row["largest_family_size"] <= 6
    assert 0.0 < row["largest_family_share"] <= 1.0
    assert len(membership) == 6
    assert set(membership["variant"]) == {"normalized"}
    if row["clustered_family_count"]:
        assert -1.0 <= row["weighted_mean_within_family_cosine"] <= 1.0


def test_cosine_benchmark_uses_brute_algorithm_and_returns_all_memberships():
    representatives = pd.DataFrame(
        [
            {
                "period": f"2019-{index + 1:02d}",
                "monthly_cluster_id": f"mc_{index}",
                "monthly_representative_theme": f"Theme {index}",
            }
            for index in range(6)
        ]
    )
    matrix = np.asarray(
        [
            [1.0, 0.0],
            [0.99, 0.01],
            [0.98, 0.02],
            [0.0, 1.0],
            [0.01, 0.99],
            [0.02, 0.98],
        ],
        dtype=np.float32,
    )
    variant = CanonicalizationVariant(
        name="cosine",
        normalize_embeddings=False,
        metric="cosine",
        min_cluster_size=2,
        algorithm="brute",
    )

    summary, membership = benchmark_canonicalization(
        representatives, matrix, variants=[variant]
    )

    assert summary.iloc[0]["metric"] == "cosine"
    assert summary.iloc[0]["algorithm"] == "brute"
    assert len(membership) == 6


def test_constituent_mean_embeddings_preserve_observation_multiplicity():
    from src.themes.canonical_benchmark import build_constituent_mean_embeddings

    representatives = pd.DataFrame(
        [
            {
                "period": "2019-01",
                "monthly_cluster_id": "mc_a",
                "monthly_representative_theme": "Theme A",
            },
            {
                "period": "2019-02",
                "monthly_cluster_id": "mc_b",
                "monthly_representative_theme": "Theme C",
            },
        ]
    )
    evidence = pd.DataFrame(
        [
            {"monthly_cluster_id": "mc_a", "source_general_theme_label": "Theme A"},
            {"monthly_cluster_id": "mc_a", "source_general_theme_label": "Theme A"},
            {"monthly_cluster_id": "mc_a", "source_general_theme_label": "Theme B"},
            {"monthly_cluster_id": "mc_b", "source_general_theme_label": "Theme C"},
            {"monthly_cluster_id": None, "source_general_theme_label": "Noise"},
        ]
    )
    embedding_frame = pd.DataFrame(
        [
            {"text": "Theme A", "embedding": [1.0, 0.0]},
            {"text": "Theme B", "embedding": [0.0, 1.0]},
            {"text": "Theme C", "embedding": [0.0, 2.0]},
            {"text": "Noise", "embedding": [9.0, 9.0]},
        ]
    )

    matrix, diagnostics = build_constituent_mean_embeddings(
        representatives, evidence, embedding_frame
    )

    np.testing.assert_allclose(matrix[0], [2.0 / 3.0, 1.0 / 3.0], rtol=1e-6)
    np.testing.assert_allclose(matrix[1], [0.0, 2.0])
    assert matrix.dtype == np.float32
    assert diagnostics.to_dict("records") == [
        {
            "monthly_cluster_id": "mc_a",
            "constituent_observation_count": 3,
            "constituent_unique_label_count": 2,
        },
        {
            "monthly_cluster_id": "mc_b",
            "constituent_observation_count": 1,
            "constituent_unique_label_count": 1,
        },
    ]


def test_constituent_mean_embeddings_require_recorded_vector_for_every_observation():
    from src.themes.canonical_benchmark import build_constituent_mean_embeddings

    representatives = pd.DataFrame(
        [
            {
                "period": "2019-01",
                "monthly_cluster_id": "mc_a",
                "monthly_representative_theme": "Theme A",
            }
        ]
    )
    evidence = pd.DataFrame(
        [
            {"monthly_cluster_id": "mc_a", "source_general_theme_label": "Theme A"},
            {"monthly_cluster_id": "mc_a", "source_general_theme_label": "Missing"},
        ]
    )
    embedding_frame = pd.DataFrame([{"text": "Theme A", "embedding": [1.0, 0.0]}])

    try:
        build_constituent_mean_embeddings(representatives, evidence, embedding_frame)
    except ValueError as exc:
        assert "constituent" in str(exc)
        assert "Missing" in str(exc)
    else:
        raise AssertionError("expected missing constituent embedding to fail")


def test_plan083_representation_builder_constructs_controlled_variants_and_diagnostics():
    representatives = pd.DataFrame(
        [
            {
                "period": "2019-01",
                "monthly_cluster_id": "mc_a",
                "monthly_representative_theme": "Theme A",
            },
            {
                "period": "2019-02",
                "monthly_cluster_id": "mc_b",
                "monthly_representative_theme": "Theme C",
            },
        ]
    )
    evidence = pd.DataFrame(
        [
            {
                "monthly_cluster_id": "mc_a",
                "source_general_theme_label": "Theme A",
                "membership_probability": 1.0,
            },
            {
                "monthly_cluster_id": "mc_a",
                "source_general_theme_label": "Theme A",
                "membership_probability": 0.5,
            },
            {
                "monthly_cluster_id": "mc_a",
                "source_general_theme_label": "Theme B",
                "membership_probability": 0.5,
            },
            {
                "monthly_cluster_id": "mc_b",
                "source_general_theme_label": "Theme C",
                "membership_probability": 1.0,
            },
        ]
    )
    embedding_frame = pd.DataFrame(
        [
            {"text": "Theme A", "embedding": [2.0, 0.0]},
            {"text": "Theme B", "embedding": [0.0, 1.0]},
            {"text": "Theme C", "embedding": [0.0, 3.0]},
        ]
    )

    matrices, diagnostics = build_stage_b_representation_embeddings(
        representatives,
        evidence,
        embedding_frame,
        representations=[
            CONSTITUENT_MEAN_EMBEDDING,
            CONSTITUENT_UNIT_MEAN_EMBEDDING,
            CONSTITUENT_PROBABILITY_WEIGHTED_MEAN_EMBEDDING,
            CONSTITUENT_UNIQUE_MEAN_EMBEDDING,
        ],
    )

    np.testing.assert_allclose(
        matrices[CONSTITUENT_MEAN_EMBEDDING][0], [4.0 / 3.0, 1.0 / 3.0]
    )
    np.testing.assert_allclose(
        matrices[CONSTITUENT_UNIT_MEAN_EMBEDDING][0], [2.0 / 3.0, 1.0 / 3.0]
    )
    np.testing.assert_allclose(
        matrices[CONSTITUENT_PROBABILITY_WEIGHTED_MEAN_EMBEDDING][0],
        [1.5, 0.25],
    )
    np.testing.assert_allclose(
        matrices[CONSTITUENT_UNIQUE_MEAN_EMBEDDING][0], [1.0, 0.5]
    )
    assert all(matrix.dtype == np.float32 for matrix in matrices.values())
    row = diagnostics.set_index("monthly_cluster_id").loc["mc_a"]
    assert row["constituent_observation_count"] == 3
    assert row["constituent_unique_label_count"] == 2
    assert -1.0 <= row["mean_constituent_to_centroid_cosine"] <= 1.0
    assert -1.0 <= row["minimum_constituent_pairwise_cosine"] <= 1.0
    assert -1.0 <= row["representative_to_centroid_cosine"] <= 1.0
    assert -1.0 <= row["mean_representative_to_constituent_cosine"] <= 1.0


def test_plan083_probability_weighted_representation_rejects_zero_total_probability():
    representatives = pd.DataFrame(
        [
            {
                "period": "2019-01",
                "monthly_cluster_id": "mc_a",
                "monthly_representative_theme": "Theme A",
            }
        ]
    )
    evidence = pd.DataFrame(
        [
            {
                "monthly_cluster_id": "mc_a",
                "source_general_theme_label": "Theme A",
                "membership_probability": 0.0,
            },
            {
                "monthly_cluster_id": "mc_a",
                "source_general_theme_label": "Theme B",
                "membership_probability": 0.0,
            },
        ]
    )
    embedding_frame = pd.DataFrame(
        [
            {"text": "Theme A", "embedding": [1.0, 0.0]},
            {"text": "Theme B", "embedding": [0.0, 1.0]},
        ]
    )

    try:
        build_stage_b_representation_embeddings(
            representatives,
            evidence,
            embedding_frame,
            representations=[CONSTITUENT_PROBABILITY_WEIGHTED_MEAN_EMBEDDING],
        )
    except ValueError as exc:
        assert "zero/invalid total" in str(exc)
    else:
        raise AssertionError("expected zero probability total to fail")


def test_plan083_representation_builder_requires_recorded_representative_vector():
    representatives = pd.DataFrame(
        [
            {
                "period": "2019-01",
                "monthly_cluster_id": "mc_a",
                "monthly_representative_theme": "Missing Representative",
            }
        ]
    )
    evidence = pd.DataFrame(
        [
            {
                "monthly_cluster_id": "mc_a",
                "source_general_theme_label": "Theme A",
                "membership_probability": 1.0,
            }
        ]
    )
    embedding_frame = pd.DataFrame([{"text": "Theme A", "embedding": [1.0, 0.0]}])

    try:
        build_stage_b_representation_embeddings(
            representatives,
            evidence,
            embedding_frame,
            representations=[CONSTITUENT_MEAN_EMBEDDING],
        )
    except ValueError as exc:
        assert "representative" in str(exc)
        assert "Missing Representative" in str(exc)
    else:
        raise AssertionError("expected missing representative embedding to fail")


def test_benchmark_can_compare_representative_and_constituent_mean_representations():
    from src.themes.canonical_benchmark import CONSTITUENT_MEAN_EMBEDDING

    representatives = pd.DataFrame(
        [
            {
                "period": f"2019-{index + 1:02d}",
                "monthly_cluster_id": f"mc_{index}",
                "monthly_representative_theme": f"Theme {index}",
                "constituent_observation_count": index + 2,
                "constituent_unique_label_count": index + 1,
            }
            for index in range(6)
        ]
    )
    representative_matrix = np.asarray(
        [
            [1.0, 0.0],
            [0.99, 0.01],
            [0.98, 0.02],
            [0.0, 1.0],
            [0.01, 0.99],
            [0.02, 0.98],
        ],
        dtype=np.float32,
    )
    centroid_matrix = np.asarray(
        [
            [1.0, 0.0],
            [0.95, 0.05],
            [0.90, 0.10],
            [0.0, 1.0],
            [0.05, 0.95],
            [0.10, 0.90],
        ],
        dtype=np.float32,
    )
    variants = [
        CanonicalizationVariant(
            name="representative",
            normalize_embeddings=False,
            metric="euclidean",
            min_cluster_size=2,
        ),
        CanonicalizationVariant(
            name="centroid",
            normalize_embeddings=True,
            metric="euclidean",
            min_cluster_size=2,
            representation=CONSTITUENT_MEAN_EMBEDDING,
        ),
    ]

    summary, membership = benchmark_canonicalization(
        representatives,
        representative_matrix,
        variants=variants,
        representation_embeddings={CONSTITUENT_MEAN_EMBEDDING: centroid_matrix},
    )

    assert set(summary["representation"]) == {"representative", "constituent_mean"}
    assert set(membership["representation"]) == {
        "representative",
        "constituent_mean",
    }
    assert set(membership["constituent_observation_count"]) == {2, 3, 4, 5, 6, 7}


def test_benchmark_rejects_variant_with_unavailable_representation():
    variant = CanonicalizationVariant(
        name="missing-representation",
        normalize_embeddings=False,
        metric="euclidean",
        min_cluster_size=2,
        representation="not_available",
    )
    representatives = pd.DataFrame(
        [
            {
                "period": f"2019-{index + 1:02d}",
                "monthly_cluster_id": f"mc_{index}",
                "monthly_representative_theme": f"Theme {index}",
            }
            for index in range(3)
        ]
    )
    matrix = np.eye(3, dtype=np.float32)

    try:
        benchmark_canonicalization(representatives, matrix, variants=[variant])
    except ValueError as exc:
        assert "unavailable representation" in str(exc)
    else:
        raise AssertionError("expected unavailable representation to fail")


def test_write_benchmark_includes_plan080_centroid_variants_without_inference(
    tmp_path, monkeypatch
):
    from src.themes.canonical_benchmark import write_canonicalization_benchmark

    representatives = pd.DataFrame(
        [
            {
                "period": f"2019-{index + 1:02d}",
                "monthly_cluster_id": f"mc_{index}",
                "monthly_representative_theme": f"Theme {index}",
            }
            for index in range(6)
        ]
    )
    evidence_rows = []
    embedding_rows = []
    for index in range(6):
        label = f"Theme {index}"
        evidence_rows.append(
            {
                "monthly_cluster_id": f"mc_{index}",
                "source_general_theme_label": label,
                "membership_probability": 1.0,
            }
        )
        embedding_rows.append(
            {
                "text": label,
                "embedding": [
                    1.0 if index < 3 else 0.0,
                    0.0 if index < 3 else 1.0,
                    float(index) / 100.0,
                ],
            }
        )
    evidence = pd.DataFrame(evidence_rows)
    embedding_frame = pd.DataFrame(embedding_rows)

    monkeypatch.setattr(
        "src.themes.canonical_benchmark.load_canonicalization_benchmark_data",
        lambda _themes_dir: (representatives, evidence, embedding_frame),
    )

    summary_path, membership_path = write_canonicalization_benchmark("unused", tmp_path)

    summary = pd.read_csv(summary_path)
    membership = pd.read_csv(membership_path)
    assert {
        "constituent_mean_raw_euclidean_mcs2",
        "constituent_mean_normalized_euclidean_mcs2",
        "representative_normalized_agglomerative_complete_cosine_s65",
        "constituent_unit_mean_normalized_agglomerative_complete_cosine_s65",
        "constituent_probability_weighted_mean_normalized_agglomerative_complete_cosine_s65",
        "constituent_unique_mean_normalized_agglomerative_complete_cosine_s65",
    }.issubset(set(summary["variant"]))
    centroid_rows = membership.loc[membership["representation"] == "constituent_mean"]
    centroid_variant_count = int(
        (summary["representation"] == "constituent_mean").sum()
    )
    assert len(centroid_rows) == len(representatives) * centroid_variant_count
    assert set(centroid_rows["constituent_observation_count"]) == {1}
    assert {
        "mean_constituent_to_centroid_cosine",
        "minimum_constituent_pairwise_cosine",
        "representative_to_centroid_cosine",
        "family_observation_count",
        "family_observation_share",
    }.issubset(membership.columns)
    assert {
        "largest_family_observation_count",
        "largest_family_observation_share",
        "weighted_mean_within_family_representative_cosine",
        "minimum_within_family_representative_cosine",
    }.issubset(summary.columns)


def test_agglomerative_complete_cosine_threshold_preserves_singletons_as_noise():
    from src.themes.canonical_benchmark import (
        AGGLOMERATIVE_GROUPING,
        CONSTITUENT_MEAN_EMBEDDING,
    )

    representatives = pd.DataFrame(
        [
            {
                "period": f"2019-{index + 1:02d}",
                "monthly_cluster_id": f"mc_{index}",
                "monthly_representative_theme": f"Theme {index}",
            }
            for index in range(5)
        ]
    )
    representative_matrix = np.eye(5, dtype=np.float32)
    centroid_matrix = np.asarray(
        [
            [1.0, 0.0, 0.0, 0.0, 0.0],
            [0.98, 0.20, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.98, 0.20, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )
    variant = CanonicalizationVariant(
        name="complete-threshold",
        normalize_embeddings=True,
        metric="cosine",
        min_cluster_size=2,
        representation=CONSTITUENT_MEAN_EMBEDDING,
        grouping_method=AGGLOMERATIVE_GROUPING,
        linkage="complete",
        similarity_threshold=0.95,
    )

    summary, membership = benchmark_canonicalization(
        representatives,
        representative_matrix,
        variants=[variant],
        representation_embeddings={CONSTITUENT_MEAN_EMBEDDING: centroid_matrix},
    )

    row = summary.iloc[0]
    assert row["grouping_method"] == "agglomerative"
    assert row["linkage"] == "complete"
    assert row["similarity_threshold"] == 0.95
    assert np.isclose(row["distance_threshold"], 0.05)
    assert pd.isna(row["min_samples"])
    assert row["clustered_family_count"] == 2
    assert row["noise_monthly_clusters"] == 1
    assert row["minimum_within_family_cosine"] >= 0.95
    assert membership["stage_b_hdbscan_label"].isna().all()
    assert membership.loc[
        membership["singleton_noise"], "monthly_cluster_id"
    ].tolist() == ["mc_4"]


def test_hdbscan_min_samples_override_is_isolated_to_benchmark_variant():
    from src.themes.canonical_benchmark import CONSTITUENT_MEAN_EMBEDDING

    representatives = pd.DataFrame(
        [
            {
                "period": f"2019-{index + 1:02d}",
                "monthly_cluster_id": f"mc_{index}",
                "monthly_representative_theme": f"Theme {index}",
            }
            for index in range(6)
        ]
    )
    matrix = np.asarray(
        [
            [1.0, 0.0],
            [0.99, 0.01],
            [0.98, 0.02],
            [0.0, 1.0],
            [0.01, 0.99],
            [0.02, 0.98],
        ],
        dtype=np.float32,
    )
    variant = CanonicalizationVariant(
        name="centroid-ms1",
        normalize_embeddings=True,
        metric="euclidean",
        min_cluster_size=2,
        min_samples=1,
        representation=CONSTITUENT_MEAN_EMBEDDING,
    )

    summary, membership = benchmark_canonicalization(
        representatives,
        matrix,
        variants=[variant],
        representation_embeddings={CONSTITUENT_MEAN_EMBEDDING: matrix.copy()},
    )

    assert summary.iloc[0]["grouping_method"] == "hdbscan"
    assert summary.iloc[0]["min_samples"] == 1
    assert membership["stage_b_hdbscan_label"].notna().all()


def test_plan081_default_variants_cover_cosine_threshold_grid():
    from src.themes.canonical_benchmark import (
        AGGLOMERATIVE_GROUPING,
        DEFAULT_CANONICALIZATION_BENCHMARK_VARIANTS,
    )

    threshold_variants = [
        variant
        for variant in DEFAULT_CANONICALIZATION_BENCHMARK_VARIANTS
        if variant.grouping_method == AGGLOMERATIVE_GROUPING
        and variant.representation == CONSTITUENT_MEAN_EMBEDDING
    ]

    assert len(threshold_variants) == 10
    assert {variant.linkage for variant in threshold_variants} == {
        "average",
        "complete",
    }
    assert {variant.similarity_threshold for variant in threshold_variants} == {
        0.60,
        0.65,
        0.70,
        0.75,
        0.80,
    }
    assert all(variant.normalize_embeddings for variant in threshold_variants)
    assert all(
        variant.representation == "constituent_mean" for variant in threshold_variants
    )


def test_plan083_default_variants_cover_fixed_complete_linkage_representation_grid():
    from src.themes.canonical_benchmark import (
        DEFAULT_CANONICALIZATION_BENCHMARK_VARIANTS,
        PLAN083_REPRESENTATIONS,
        PLAN083_SIMILARITY_THRESHOLDS,
    )

    plan083_variants = [
        variant
        for variant in DEFAULT_CANONICALIZATION_BENCHMARK_VARIANTS
        if variant.grouping_method == AGGLOMERATIVE_GROUPING
        and variant.linkage == "complete"
        and variant.representation in PLAN083_REPRESENTATIONS
    ]

    assert {
        (variant.representation, variant.similarity_threshold)
        for variant in plan083_variants
    } == {
        (representation, threshold)
        for representation in PLAN083_REPRESENTATIONS
        for threshold in PLAN083_SIMILARITY_THRESHOLDS
    }
    assert all(variant.metric == "cosine" for variant in plan083_variants)
    assert all(variant.normalize_embeddings for variant in plan083_variants)


def test_plan083_representative_space_diagnostics_expose_centroid_false_merge():
    representatives = pd.DataFrame(
        [
            {
                "period": "2019-01",
                "monthly_cluster_id": "mc_a",
                "monthly_representative_theme": "Theme A",
                "constituent_observation_count": 2,
            },
            {
                "period": "2019-02",
                "monthly_cluster_id": "mc_b",
                "monthly_representative_theme": "Theme B",
                "constituent_observation_count": 2,
            },
        ]
    )
    representative_matrix = np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    collapsed_centroid_matrix = np.asarray([[1.0, 1.0], [1.0, 1.0]], dtype=np.float32)
    variants = [
        CanonicalizationVariant(
            name="centroid",
            normalize_embeddings=True,
            metric="cosine",
            min_cluster_size=2,
            representation=CONSTITUENT_MEAN_EMBEDDING,
            grouping_method=AGGLOMERATIVE_GROUPING,
            linkage="complete",
            similarity_threshold=0.65,
        ),
        CanonicalizationVariant(
            name="representative",
            normalize_embeddings=True,
            metric="cosine",
            min_cluster_size=2,
            representation=REPRESENTATIVE_EMBEDDING,
            grouping_method=AGGLOMERATIVE_GROUPING,
            linkage="complete",
            similarity_threshold=0.65,
        ),
    ]

    summary, membership = benchmark_canonicalization(
        representatives,
        representative_matrix,
        variants=variants,
        representation_embeddings={
            CONSTITUENT_MEAN_EMBEDDING: collapsed_centroid_matrix
        },
    )

    centroid_summary = summary.set_index("variant").loc["centroid"]
    representative_summary = summary.set_index("variant").loc["representative"]
    assert centroid_summary["clustered_family_count"] == 1
    assert centroid_summary["minimum_within_family_cosine"] >= 0.65
    assert centroid_summary["minimum_within_family_representative_cosine"] < 0.65
    assert representative_summary["clustered_family_count"] == 0
    assert membership.loc[
        membership["variant"] == "representative", "singleton_noise"
    ].all()


def test_plan083_reports_observation_weighted_family_concentration():
    representatives = pd.DataFrame(
        [
            {
                "period": "2019-01",
                "monthly_cluster_id": "mc_a",
                "monthly_representative_theme": "Theme A",
                "constituent_observation_count": 100,
            },
            {
                "period": "2019-02",
                "monthly_cluster_id": "mc_b",
                "monthly_representative_theme": "Theme B",
                "constituent_observation_count": 100,
            },
            {
                "period": "2019-03",
                "monthly_cluster_id": "mc_c",
                "monthly_representative_theme": "Theme C",
                "constituent_observation_count": 1,
            },
        ]
    )
    matrix = np.asarray([[1.0, 0.0], [0.99, 0.01], [0.0, 1.0]], dtype=np.float32)
    variant = CanonicalizationVariant(
        name="weighted-concentration",
        normalize_embeddings=True,
        metric="cosine",
        min_cluster_size=2,
        representation=REPRESENTATIVE_EMBEDDING,
        grouping_method=AGGLOMERATIVE_GROUPING,
        linkage="complete",
        similarity_threshold=0.65,
    )

    summary, membership = benchmark_canonicalization(
        representatives, matrix, variants=[variant]
    )

    row = summary.iloc[0]
    assert np.isclose(row["largest_family_share"], 2.0 / 3.0)
    assert row["largest_family_observation_count"] == 200
    assert np.isclose(row["largest_family_observation_share"], 200.0 / 201.0)
    clustered = membership.loc[~membership["singleton_noise"]]
    assert set(clustered["family_observation_count"]) == {200}
    assert np.allclose(clustered["family_observation_share"], 200.0 / 201.0)


def test_production_stage_b_partition_matches_approved_plan083_representative_candidate():
    representatives = pd.DataFrame(
        [
            {
                "period": f"2019-{index + 1:02d}",
                "monthly_cluster_id": f"mc_{index}",
                "monthly_representative_theme": f"Theme {index}",
            }
            for index in range(5)
        ]
    )
    matrix = np.asarray(
        [
            [1.0, 0.0],
            [0.95, 0.20],
            [0.10, 0.99],
            [0.00, 1.00],
            [-1.0, 0.0],
        ],
        dtype=np.float64,
    )
    matrix = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)
    variant = CanonicalizationVariant(
        name="approved-production-candidate",
        normalize_embeddings=True,
        metric="cosine",
        min_cluster_size=2,
        representation=REPRESENTATIVE_EMBEDDING,
        grouping_method=AGGLOMERATIVE_GROUPING,
        linkage="complete",
        similarity_threshold=0.65,
    )

    _, membership = benchmark_canonicalization(
        representatives,
        matrix,
        variants=[variant],
    )
    benchmark_families = {
        frozenset(group["monthly_cluster_id"].astype(str))
        for _, group in membership.groupby("benchmark_family_key", sort=False)
    }

    clusters = [
        MonthlyCluster(
            period=str(row.period),
            cluster_id=str(row.monthly_cluster_id),
            hdbscan_label=0,
            representative_theme=str(row.monthly_representative_theme),
            observation_indices=(0, 1),
            mean_membership_probability=1.0,
        )
        for row in representatives.itertuples(index=False)
    ]
    representative_embeddings = {
        cluster.cluster_id: matrix[index] for index, cluster in enumerate(clusters)
    }
    production_families, _ = _canonicalize_monthly_clusters(
        clusters,
        normalized_representative_embeddings=representative_embeddings,
    )
    production_memberships = {
        frozenset(family.monthly_cluster_ids) for family in production_families
    }

    assert production_memberships == benchmark_families
