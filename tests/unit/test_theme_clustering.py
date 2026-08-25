from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.themes.theme_clustering import (
    CANONICALIZATION_DISTANCE_THRESHOLD,
    CANONICALIZATION_GROUPING_METHOD,
    CANONICALIZATION_LINKAGE,
    CANONICALIZATION_METRIC,
    CANONICALIZATION_REPRESENTATION,
    CANONICALIZATION_SIMILARITY_THRESHOLD,
    MONTHLY_CLUSTER_CONTRACT_VERSION,
    MONTHLY_CLUSTER_SELECTION_METHOD,
    MONTHLY_CLUSTERING_INPUT_NORMALIZED,
    MonthlyCluster,
    _canonicalize_monthly_clusters,
    _l2_normalize_embeddings,
    _normalized_representative_embeddings,
    build_clustered_theme_artifacts,
    extract_general_theme_observations,
)


def test_stage_a_production_geometry_contract_is_unit_euclidean_leaf():
    raw = np.asarray([[3.0, 4.0], [0.0, 2.0]], dtype=np.float32)
    raw_before = raw.copy()

    normalized = _l2_normalize_embeddings(raw, context="test embeddings")

    assert MONTHLY_CLUSTER_CONTRACT_VERSION == "3.0"
    assert MONTHLY_CLUSTERING_INPUT_NORMALIZED is True
    assert MONTHLY_CLUSTER_SELECTION_METHOD == "leaf"
    assert normalized.dtype == np.float64
    assert np.allclose(np.linalg.norm(normalized, axis=1), 1.0)
    np.testing.assert_array_equal(raw, raw_before)


def test_stage_a_normalization_rejects_zero_vectors():
    with pytest.raises(ValueError, match="zero/non-finite vectors"):
        _l2_normalize_embeddings(
            np.asarray([[1.0, 0.0], [0.0, 0.0]], dtype=np.float32),
            context="test embeddings",
        )


class MappingEmbedder:
    def __init__(self, mapping: dict[str, list[float]]):
        self.mapping = mapping
        self.calls: list[list[str]] = []

    def encode(self, sentences):
        values = [str(value) for value in sentences]
        self.calls.append(values)
        return np.asarray([self.mapping[value] for value in values], dtype=np.float32)


class QueueClustererFactory:
    def __init__(self, labels_by_call: list[list[int]], probabilities_by_call=None):
        self.labels_by_call = list(labels_by_call)
        self.probabilities_by_call = list(probabilities_by_call or [])
        self.calls = []
        self.fit_inputs = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        labels = self.labels_by_call.pop(0)
        probabilities = (
            self.probabilities_by_call.pop(0)
            if self.probabilities_by_call
            else [1.0 if label >= 0 else 0.0 for label in labels]
        )

        class Clusterer:
            def fit(inner_self, embeddings):
                assert len(embeddings) == len(labels)
                self.fit_inputs.append(np.asarray(embeddings, dtype=float).copy())
                inner_self.labels_ = np.asarray(labels)
                inner_self.probabilities_ = np.asarray(probabilities, dtype=np.float32)
                return inner_self

        return Clusterer()


def _row(
    if_id,
    wif_id,
    general,
    keywords,
    *,
    general_mapping=None,
    absolute="IF fallback should not be used",
):
    return {
        "absolute_community": if_id,
        "weighted_community": wif_id,
        "general_theme_names": general,
        "general_theme_gpt": general_mapping or {},
        "all_keywords": keywords,
        "absolute_theme_names": absolute,
        "weighted_theme_names": "WIF fallback should not be used",
    }


def test_general_theme_observations_never_fall_back_to_if_or_wif_labels():
    frame = pd.DataFrame(
        [
            _row(1, 11, None, ["immigration"], absolute="Absolute Theme"),
            _row(2, 12, "General Theme", ["policy"]),
        ]
    )

    observations, excluded, pairs = extract_general_theme_observations(
        frame, period="2017-01"
    )

    assert excluded == 1
    assert pairs == {"if:2|wif:12"}
    assert [item.label for item in observations] == ["General Theme"]


def test_general_theme_gpt_reconstructs_dot_joined_general_labels_and_keyword_evidence():
    frame = pd.DataFrame(
        [
            _row(
                1,
                11,
                "US Immigration Policy.Social Media Activism",
                ["fallback", "keywords"],
                general_mapping={
                    "US Immigration Policy": ["immigration", "court"],
                    "Social Media Activism": ["protest", "retweet"],
                },
            )
        ]
    )

    observations, excluded, pairs = extract_general_theme_observations(
        frame, period="2017-01"
    )

    assert excluded == 0
    assert pairs == {"if:1|wif:11"}
    assert [item.label for item in observations] == [
        "US Immigration Policy",
        "Social Media Activism",
    ]
    assert observations[0].keywords == ("immigration", "court")
    assert observations[1].keywords == ("protest", "retweet")


def test_general_theme_gpt_reconstructs_comma_bearing_labels_before_generic_list_parsing():
    frame = pd.DataFrame(
        [
            _row(
                1,
                11,
                (
                    "Media content production, metadata, and episodic structure."
                    "Online social network and recruitment dynamics"
                ),
                ["fallback", "keywords"],
                general_mapping={
                    "Media content production, metadata, and episodic structure": [
                        "media",
                        "metadata",
                    ],
                    "Online social network and recruitment dynamics": [
                        "social",
                        "network",
                    ],
                },
            )
        ]
    )

    observations, excluded, pairs = extract_general_theme_observations(
        frame, period="2019-06"
    )

    assert excluded == 0
    assert pairs == {"if:1|wif:11"}
    assert [item.label for item in observations] == [
        "Media content production, metadata, and episodic structure",
        "Online social network and recruitment dynamics",
    ]
    assert observations[0].keywords == ("media", "metadata")
    assert observations[1].keywords == ("social", "network")
    assert "metadata" not in {item.label for item in observations}


def test_single_comma_bearing_general_theme_remains_atomic():
    frame = pd.DataFrame(
        [
            _row(
                1,
                11,
                "Departure, farewell, and temporal markers",
                ["departure", "farewell"],
                general_mapping={
                    "Departure, farewell, and temporal markers": [
                        "departure",
                        "farewell",
                    ]
                },
            )
        ]
    )

    observations, excluded, pairs = extract_general_theme_observations(
        frame, period="2019-06"
    )

    assert excluded == 0
    assert pairs == {"if:1|wif:11"}
    assert [item.label for item in observations] == [
        "Departure, farewell, and temporal markers"
    ]
    assert observations[0].keywords == ("departure", "farewell")


def test_scalar_general_theme_without_mapping_is_not_comma_delimited():
    frame = pd.DataFrame(
        [
            _row(
                1,
                11,
                "Names, identities, and social networks in regional context",
                ["names", "identity"],
                general_mapping=None,
            )
        ]
    )

    observations, excluded, pairs = extract_general_theme_observations(
        frame, period="2019-06"
    )

    assert excluded == 0
    assert pairs == {"if:1|wif:11"}
    assert [item.label for item in observations] == [
        "Names, identities, and social networks in regional context"
    ]


def test_structured_general_theme_list_preserves_commas_inside_items():
    frame = pd.DataFrame(
        [
            _row(
                1,
                11,
                [
                    "Cultural events, tourism, and hospitality contexts",
                    "Online social interaction",
                ],
                ["fallback"],
                general_mapping={
                    "Cultural events, tourism, and hospitality contexts": [
                        "culture",
                        "tourism",
                    ],
                    "Online social interaction": ["social"],
                },
            )
        ]
    )

    observations, excluded, _ = extract_general_theme_observations(
        frame, period="2019-06"
    )

    assert excluded == 0
    assert [item.label for item in observations] == [
        "Cultural events, tourism, and hospitality contexts",
        "Online social interaction",
    ]


def test_serialized_general_theme_lists_preserve_commas_inside_items():
    values = [
        '["Theme A, with comma", "Theme B"]',
        "['Theme A, with comma', 'Theme B']",
    ]

    for value in values:
        frame = pd.DataFrame([_row(1, 11, value, ["fallback"])])
        observations, excluded, _ = extract_general_theme_observations(
            frame, period="2019-06"
        )

        assert excluded == 0
        assert [item.label for item in observations] == [
            "Theme A, with comma",
            "Theme B",
        ]


def test_general_theme_mapping_does_not_supply_labels_when_names_are_missing():
    frame = pd.DataFrame(
        [
            _row(
                1,
                11,
                None,
                ["fallback"],
                general_mapping={"Mapping-only theme": ["mapped"]},
            )
        ]
    )

    observations, excluded, pairs = extract_general_theme_observations(
        frame, period="2017-01"
    )

    assert observations == []
    assert excluded == 1
    assert pairs == set()


def test_two_stage_clustering_aggregates_distinct_matched_pairs_and_keywords():
    monthly = {
        "january": pd.DataFrame(
            [
                _row(1, 11, "US Immigration Policy", ["trump", "immigration", "ban"]),
                _row(
                    2, 12, "Trump Immigration Policy", ["immigration", "court", "trump"]
                ),
                _row(3, 13, "Sports Update", ["game", "team"]),
                _row(4, 14, None, ["ignored"]),
            ]
        ),
        "february": pd.DataFrame(
            [
                _row(5, 15, "US Immigration Policy", ["immigration", "ban", "court"]),
                _row(
                    6,
                    16,
                    "Immigration Legal Challenges",
                    ["court", "immigration", "judge"],
                ),
                _row(7, 17, "Music News", ["music", "artist"]),
            ]
        ),
    }
    embedder = MappingEmbedder(
        {
            "US Immigration Policy": [1.0, 0.0],
            "Trump Immigration Policy": [0.95, 0.05],
            "Sports Update": [0.0, 1.0],
            "Immigration Legal Challenges": [0.9, 0.1],
            "Music News": [0.0, 1.0],
        }
    )
    factory = QueueClustererFactory(
        [[0, 0, -1], [0, 0, -1]],
        [[0.9, 0.8, 0.0], [0.95, 0.85, 0.0]],
    )

    summaries, evidence, families = build_clustered_theme_artifacts(
        monthly,
        year=2017,
        embedder=embedder,
        clustering_model="sentence-transformers/all-MiniLM-L6-v2",
        clusterer_factory=factory,
        embedding_provider="tei",
        source_artifact_hashes={"2017-01": "abc", "2017-02": "def"},
    )

    january = summaries["2017-01"]
    february = summaries["2017-02"]
    assert len(january) == 1
    assert len(february) == 1
    assert (
        january.iloc[0]["canonical_theme_id"] == february.iloc[0]["canonical_theme_id"]
    )
    assert january.iloc[0]["community_count"] == 2
    assert january.iloc[0]["total_themed_community_pairs"] == 3
    assert january.iloc[0]["monthly_noise_observation_count"] == 1
    assert january.iloc[0]["excluded_records_missing_general_theme"] == 1
    assert january.iloc[0]["embedding_provider"] == "tei"
    assert january.iloc[0]["embedding_model_revision"] == ""
    assert january.iloc[0]["embedding_contract_version"] == ""
    assert january.iloc[0]["embedding_dtype"] == "float32"
    assert not bool(january.iloc[0]["embedding_normalized"])
    assert bool(january.iloc[0]["clustering_input_normalized"])
    assert january.iloc[0]["hdbscan_implementation"] == "sklearn.cluster.HDBSCAN"
    assert january.iloc[0]["hdbscan_min_samples"] == 3
    assert january.iloc[0]["hdbscan_cluster_selection_method"] == "leaf"
    assert not bool(january.iloc[0]["hdbscan_allow_single_cluster"])
    assert january.iloc[0]["clustering_min_cluster_size"] == 2
    assert january.iloc[0]["canonicalization_min_cluster_size"] == 2
    assert january.iloc[0]["clustering_metric"] == "euclidean"
    assert january.iloc[0]["canonicalization_representation"] == (
        CANONICALIZATION_REPRESENTATION
    )
    assert january.iloc[0]["canonicalization_grouping_method"] == (
        CANONICALIZATION_GROUPING_METHOD
    )
    assert january.iloc[0]["canonicalization_metric"] == CANONICALIZATION_METRIC
    assert january.iloc[0]["canonicalization_linkage"] == CANONICALIZATION_LINKAGE
    assert january.iloc[0]["canonicalization_similarity_threshold"] == (
        CANONICALIZATION_SIMILARITY_THRESHOLD
    )
    assert january.iloc[0]["canonicalization_distance_threshold"] == (
        CANONICALIZATION_DISTANCE_THRESHOLD
    )
    assert january.iloc[0]["source_artifact_sha256"] == "abc"
    assert json.loads(january.iloc[0]["prominent_keywords"])[:2] == [
        "trump",
        "immigration",
    ]

    january_evidence = evidence["2017-01"]
    assert january_evidence["is_monthly_noise"].tolist() == [False, False, True]
    assert january_evidence.iloc[2]["canonical_theme_id"] is None
    assert january_evidence.iloc[0]["source_artifact_sha256"] == "abc"
    assert bool(january_evidence.iloc[0]["clustering_input_normalized"])
    assert january_evidence.iloc[0]["hdbscan_cluster_selection_method"] == "leaf"
    assert len(families) == 1
    assert families.iloc[0]["months_present"] == 2
    assert bool(families.iloc[0]["clustering_input_normalized"])
    assert families.iloc[0]["hdbscan_cluster_selection_method"] == "leaf"
    assert pd.isna(families.iloc[0]["stage_b_hdbscan_label"])
    assert int(families.iloc[0]["stage_b_cluster_label"]) >= 0
    assert json.loads(families.iloc[0]["source_artifact_sha256s"]) == ["abc", "def"]
    assert embedder.calls == [
        ["US Immigration Policy", "Trump Immigration Policy", "Sports Update"],
        ["US Immigration Policy", "Immigration Legal Challenges", "Music News"],
    ]

    assert factory.calls == [
        {
            "min_cluster_size": 2,
            "min_samples": 3,
            "metric": "euclidean",
            "cluster_selection_method": "leaf",
            "allow_single_cluster": False,
            "copy": True,
        },
        {
            "min_cluster_size": 2,
            "min_samples": 3,
            "metric": "euclidean",
            "cluster_selection_method": "leaf",
            "allow_single_cluster": False,
            "copy": True,
        },
    ]
    assert all(
        np.allclose(np.linalg.norm(matrix, axis=1), 1.0)
        for matrix in factory.fit_inputs
    )


def test_stage_b_noise_becomes_singleton_canonical_themes():
    monthly = {
        "january": pd.DataFrame(
            [
                _row(1, 11, "Theme A", ["a"]),
                _row(2, 12, "Theme A variant", ["a"]),
            ]
        ),
        "february": pd.DataFrame(
            [
                _row(3, 13, "Theme B", ["b"]),
                _row(4, 14, "Theme B variant", ["b"]),
            ]
        ),
    }
    embedder = MappingEmbedder(
        {
            "Theme A": [1.0, 0.0],
            "Theme A variant": [0.9, 0.1],
            "Theme B": [0.0, 1.0],
            "Theme B variant": [0.1, 0.9],
        }
    )
    factory = QueueClustererFactory([[0, 0], [0, 0]])

    summaries, _, families = build_clustered_theme_artifacts(
        monthly,
        year=2017,
        embedder=embedder,
        clusterer_factory=factory,
        embedding_provider="mock",
    )

    assert len(families) == 2
    assert families["singleton_canonical_theme"].tolist() == [True, True]
    assert (
        summaries["2017-01"].iloc[0]["canonical_theme_id"]
        != summaries["2017-02"].iloc[0]["canonical_theme_id"]
    )
    assert set(families["embedding_provider"]) == {"mock"}
    assert families["stage_b_hdbscan_label"].isna().all()


def test_stage_b_reuses_normalized_monthly_representative_embedding_not_centroid():
    from src.themes.theme_clustering import ThemeObservation

    cluster = MonthlyCluster(
        period="2017-01",
        cluster_id="mc_test",
        hdbscan_label=0,
        representative_theme="Theme A",
        observation_indices=(0, 1, 2),
        mean_membership_probability=1.0,
    )
    observations = [
        ThemeObservation("2017-01", "p0", "1", "11", "Theme A", (), 0),
        ThemeObservation("2017-01", "p1", "2", "12", "Theme A", (), 1),
        ThemeObservation("2017-01", "p2", "3", "13", "Theme B", (), 2),
    ]
    embeddings = np.asarray(
        [
            [2.0, 0.0],
            [2.0, 0.0],
            [0.0, 4.0],
        ],
        dtype=np.float32,
    )

    representative = _normalized_representative_embeddings(
        [cluster], observations=observations, embeddings=embeddings
    )[cluster.cluster_id]

    np.testing.assert_allclose(representative, [1.0, 0.0])
    np.testing.assert_allclose(np.linalg.norm(representative), 1.0)
    centroid = embeddings.mean(axis=0)
    centroid = centroid / np.linalg.norm(centroid)
    assert not np.allclose(representative, centroid)


def test_stage_b_representative_embedding_fails_if_medoid_is_not_in_constituents():
    from src.themes.theme_clustering import ThemeObservation

    cluster = MonthlyCluster(
        period="2017-01",
        cluster_id="mc_test",
        hdbscan_label=0,
        representative_theme="Missing Theme",
        observation_indices=(0, 1),
        mean_membership_probability=1.0,
    )
    observations = [
        ThemeObservation("2017-01", "p0", "1", "11", "Theme A", (), 0),
        ThemeObservation("2017-01", "p1", "2", "12", "Theme B", (), 1),
    ]

    with np.testing.assert_raises_regex(
        ValueError, "representative 'Missing Theme'.*missing from its constituent"
    ):
        _normalized_representative_embeddings(
            [cluster],
            observations=observations,
            embeddings=np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
        )


def test_stage_b_representative_embedding_rejects_inconsistent_duplicate_vectors():
    from src.themes.theme_clustering import ThemeObservation

    cluster = MonthlyCluster(
        period="2017-01",
        cluster_id="mc_test",
        hdbscan_label=0,
        representative_theme="Theme A",
        observation_indices=(0, 1),
        mean_membership_probability=1.0,
    )
    observations = [
        ThemeObservation("2017-01", "p0", "1", "11", "Theme A", (), 0),
        ThemeObservation("2017-01", "p1", "2", "12", "Theme A", (), 1),
    ]

    with np.testing.assert_raises_regex(
        ValueError, "representative 'Theme A'.*inconsistent recorded embeddings"
    ):
        _normalized_representative_embeddings(
            [cluster],
            observations=observations,
            embeddings=np.asarray([[1.0, 0.0], [0.9, 0.1]], dtype=np.float32),
        )


def test_complete_linkage_threshold_prevents_bridge_chain_merging():
    clusters = [
        MonthlyCluster(
            period=f"2017-0{index + 1}",
            cluster_id=f"mc_{index}",
            hdbscan_label=0,
            representative_theme=label,
            observation_indices=(0, 1),
            mean_membership_probability=1.0,
        )
        for index, label in enumerate(("Theme A", "Theme B", "Theme C"))
    ]
    # A↔B and B↔C are each above 0.65 cosine similarity, but A↔C is not.
    angles = np.deg2rad([0.0, 40.0, 80.0])
    centroids = {
        cluster.cluster_id: np.asarray([np.cos(angle), np.sin(angle)])
        for cluster, angle in zip(clusters, angles)
    }

    families, _ = _canonicalize_monthly_clusters(
        clusters,
        normalized_representative_embeddings=centroids,
    )

    assert sorted(len(family.monthly_cluster_ids) for family in families) == [1, 2]
    multi_member = next(
        family for family in families if not family.singleton_canonical_theme
    )
    assert set(multi_member.monthly_cluster_ids) in (
        {"mc_0", "mc_1"},
        {"mc_1", "mc_2"},
    )
    assert all(family.hdbscan_label is None for family in families)


def test_stage_b_canonical_ids_are_stable_when_input_cluster_order_changes():
    clusters = [
        MonthlyCluster(
            period=f"2017-0{index + 1}",
            cluster_id=f"mc_{index}",
            hdbscan_label=0,
            representative_theme=label,
            observation_indices=(0, 1),
            mean_membership_probability=1.0,
        )
        for index, label in enumerate(("Theme A", "Theme B", "Theme C"))
    ]
    centroids = {
        "mc_0": np.asarray([1.0, 0.0]),
        "mc_1": np.asarray([0.99, 0.1410673598]),
        "mc_2": np.asarray([0.0, 1.0]),
    }
    centroids = {key: value / np.linalg.norm(value) for key, value in centroids.items()}

    first, _ = _canonicalize_monthly_clusters(
        clusters,
        normalized_representative_embeddings=centroids,
    )
    second, _ = _canonicalize_monthly_clusters(
        list(reversed(clusters)),
        normalized_representative_embeddings=centroids,
    )

    first_membership = {
        family.canonical_theme_id: family.monthly_cluster_ids for family in first
    }
    second_membership = {
        family.canonical_theme_id: family.monthly_cluster_ids for family in second
    }
    assert first_membership == second_membership


def test_all_noise_month_keeps_denominator_and_noise_diagnostics():
    monthly = {
        "january": pd.DataFrame(
            [
                _row(1, 11, "One-off A", ["a"]),
                _row(2, 12, "One-off B", ["b"]),
            ]
        )
    }
    embedder = MappingEmbedder({"One-off A": [1.0, 0.0], "One-off B": [0.0, 1.0]})
    factory = QueueClustererFactory([[-1, -1]])

    summaries, evidence, families = build_clustered_theme_artifacts(
        monthly,
        year=2017,
        embedder=embedder,
        clusterer_factory=factory,
    )

    row = summaries["2017-01"].iloc[0]
    assert row["canonical_theme_id"] == ""
    assert row["total_themed_community_pairs"] == 2
    assert row["source_observation_count"] == 2
    assert row["monthly_noise_observation_count"] == 2
    assert evidence["2017-01"]["is_monthly_noise"].all()
    assert families.empty


def test_clustering_embedder_uses_independent_tei_profile(monkeypatch):
    from src.themes.theme_clustering import build_clustering_embedder

    monkeypatch.setenv("TEI_CLUSTERING_BASE_URL", "http://127.0.0.1:9181")
    monkeypatch.setenv("TEI_BASE_URL", "http://127.0.0.1:9180")

    client = build_clustering_embedder({"theme": {"clustering_provider": "tei"}})
    try:
        assert client.base_url == "http://127.0.0.1:9181"
        assert client.normalize is False
    finally:
        client.close()


def test_sklearn_hdbscan_small_sample_edge_returns_noise_before_fit():
    from src.themes.theme_clustering import _fit_hdbscan

    labels, probabilities = _fit_hdbscan(
        np.asarray([[0.0, 0.0], [0.1, 0.1]], dtype=np.float32),
        min_cluster_size=2,
        metric="euclidean",
        clusterer_factory=None,
    )

    assert labels.tolist() == [-1, -1]
    assert probabilities.tolist() == [0.0, 0.0]


def test_default_hdbscan_contract_uses_sklearn_and_stable_partition():
    from src.themes.theme_clustering import _fit_hdbscan

    embeddings = np.asarray(
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
    labels, probabilities = _fit_hdbscan(
        embeddings,
        min_cluster_size=2,
        metric="euclidean",
        clusterer_factory=None,
    )

    clusters = {
        frozenset(np.flatnonzero(labels == label).tolist())
        for label in set(labels.tolist())
        if label >= 0
    }
    assert clusters == {frozenset(range(6)), frozenset(range(6, 12))}
    assert probabilities.shape == (12,)
    assert np.all((probabilities >= 0.0) & (probabilities <= 1.0))


def test_duplicate_observations_preserve_density_but_pair_count_is_deduplicated():
    monthly = {
        "january": pd.DataFrame(
            [
                _row(1, 11, ["Theme A", "Theme A variant"], ["shared", "first"]),
                _row(2, 12, "Theme A", ["shared", "second"]),
            ]
        )
    }
    embedder = MappingEmbedder(
        {
            "Theme A": [1.0, 0.0],
            "Theme A variant": [0.9, 0.1],
        }
    )
    factory = QueueClustererFactory([[0, 0, 0]])

    summaries, evidence, _ = build_clustered_theme_artifacts(
        monthly,
        year=2017,
        embedder=embedder,
        clusterer_factory=factory,
    )

    assert embedder.calls[0] == ["Theme A", "Theme A variant", "Theme A"]
    assert len(evidence["2017-01"]) == 3
    row = summaries["2017-01"].iloc[0]
    assert row["source_observation_count"] == 3
    assert row["cluster_observation_count"] == 3
    assert row["community_count"] == 2
    assert row["total_themed_community_pairs"] == 2
    assert json.loads(row["prominent_keywords"])[0] == "shared"


def test_semantic_medoid_ties_use_deterministic_label_order():
    monthly = {
        "january": pd.DataFrame(
            [
                _row(1, 11, "Zulu Theme", ["zulu"]),
                _row(2, 12, "Alpha Theme", ["alpha"]),
            ]
        )
    }
    embedder = MappingEmbedder(
        {
            "Zulu Theme": [1.0, 0.0],
            "Alpha Theme": [0.0, 1.0],
        }
    )
    factory = QueueClustererFactory([[0, 0]])

    summaries, _, _ = build_clustered_theme_artifacts(
        monthly,
        year=2017,
        embedder=embedder,
        clusterer_factory=factory,
    )

    row = summaries["2017-01"].iloc[0]
    assert row["canonical_theme_label"] == "Alpha Theme"
    assert json.loads(row["monthly_representative_themes"]) == ["Alpha Theme"]


def test_tuple_keyword_evidence_is_normalized_into_individual_keywords():
    frame = pd.DataFrame(
        [
            _row(
                1,
                11,
                "Immigration policy",
                ("nobannowall", "muslimban", "ban", "travel"),
            )
        ]
    )

    observations, excluded, pairs = extract_general_theme_observations(
        frame, period="2017-03"
    )

    assert excluded == 0
    assert pairs == {"if:1|wif:11"}
    assert len(observations) == 1
    assert observations[0].keywords == (
        "nobannowall",
        "muslimban",
        "ban",
        "travel",
    )


def test_ambiguous_dot_joined_general_theme_is_excluded_and_diagnosed():
    malformed = (
        "Public Outcry and Resistance."
        "Islamophobia and Muslim Ban."
        "Political Figures and Movements."
        "Refugees and Immigration Ban Opposition"
    )
    monthly = {
        "march": pd.DataFrame(
            [
                _row(
                    4,
                    44,
                    malformed,
                    ("nobannowall", "muslimban", "ban", "travel", "trump"),
                    general_mapping=None,
                )
            ]
        )
    }

    summaries, evidence, families = build_clustered_theme_artifacts(
        monthly,
        year=2017,
        embedder=MappingEmbedder({}),
        embedding_provider="mock",
    )

    summary = summaries["2017-03"].iloc[0]
    assert summary["total_themed_community_pairs"] == 1
    assert summary["source_observation_count"] == 0
    assert summary["excluded_records_missing_general_theme"] == 0
    assert summary["excluded_records_ambiguous_general_theme_serialization"] == 1
    assert summary["canonical_theme_label"] == ""
    assert (
        summary["monthly_cluster_contract_version"]
        == MONTHLY_CLUSTER_CONTRACT_VERSION
    )
    assert summary["canonicalization_contract_version"] == "4.0"
    assert evidence["2017-03"].empty
    assert families.empty


def test_mismatched_mapping_does_not_promote_composite_theme_into_clustering():
    malformed = "Immigration Policy and Travel Ban.Public Resistance and Protest"
    monthly = {
        "march": pd.DataFrame(
            [
                _row(
                    4,
                    44,
                    malformed,
                    ("ban", "travel", "protest"),
                    general_mapping={
                        "Immigration Policy and Travel Ban": ["ban", "travel"],
                        "Different Resistance Label": ["protest"],
                    },
                )
            ]
        )
    }

    summaries, _, _ = build_clustered_theme_artifacts(
        monthly,
        year=2017,
        embedder=MappingEmbedder({}),
        embedding_provider="mock",
    )

    summary = summaries["2017-03"].iloc[0]
    assert summary["excluded_records_ambiguous_general_theme_serialization"] == 1
    assert summary["source_observation_count"] == 0


def test_legitimate_abbreviation_period_is_not_treated_as_legacy_multi_theme_serialization():
    frame = pd.DataFrame(
        [_row(1, 11, "U.S. Immigration Policy", ("immigration", "policy"))]
    )

    observations, excluded, pairs = extract_general_theme_observations(
        frame, period="2017-03"
    )

    assert excluded == 0
    assert pairs == {"if:1|wif:11"}
    assert [item.label for item in observations] == ["U.S. Immigration Policy"]
    assert observations[0].keywords == ("immigration", "policy")


def test_canonical_label_is_always_one_of_the_admitted_source_observations():
    malformed = "Theme Group Alpha.Composite Theme Group Beta"
    monthly = {
        "march": pd.DataFrame(
            [
                _row(1, 11, "Valid Theme Alpha", ("alpha",)),
                _row(2, 12, "Valid Theme Beta", ("beta",)),
                _row(3, 13, malformed, ("bad",), general_mapping=None),
            ]
        )
    }
    embedder = MappingEmbedder(
        {
            "Valid Theme Alpha": [1.0, 0.0],
            "Valid Theme Beta": [0.95, 0.05],
        }
    )
    factory = QueueClustererFactory([[0, 0]])

    summaries, evidence, _ = build_clustered_theme_artifacts(
        monthly,
        year=2017,
        embedder=embedder,
        clusterer_factory=factory,
        embedding_provider="mock",
    )

    summary = summaries["2017-03"].iloc[0]
    admitted = set(evidence["2017-03"]["source_general_theme_label"])
    assert summary["canonical_theme_label"] in admitted
    assert malformed not in admitted
    assert summary["excluded_records_ambiguous_general_theme_serialization"] == 1


def test_ambiguous_dot_joined_general_theme_with_spacing_is_excluded():
    monthly = {
        "march": pd.DataFrame(
            [
                _row(
                    5,
                    55,
                    "Immigration Policy and Travel Ban. Public Resistance and Protest",
                    ("ban", "travel", "protest"),
                    general_mapping=None,
                )
            ]
        )
    }

    summaries, _, _ = build_clustered_theme_artifacts(
        monthly,
        year=2017,
        embedder=MappingEmbedder({}),
        embedding_provider="mock",
    )

    summary = summaries["2017-03"].iloc[0]
    assert summary["excluded_records_ambiguous_general_theme_serialization"] == 1
    assert summary["source_observation_count"] == 0
