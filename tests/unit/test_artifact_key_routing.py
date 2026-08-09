from pathlib import Path

from src.artifacts.models import ArtifactCategory
from src.artifacts.run_manifest import _base_artifact_key, _canonical_location


def test_textual_month_asset_keys_keep_their_contract_identity(tmp_path: Path):
    source = tmp_path / "twitter" / "network_data" / "reply" / "march2017.parquet"
    source.parent.mkdir(parents=True)

    assert _base_artifact_key("network_data_march") == "network_data"
    category, relative = _canonical_location(tmp_path, "network_data_march", source)
    assert category is ArtifactCategory.DATA
    assert relative == Path("data/network/march2017.parquet")


def test_dashboard_metric_and_community_keys_route_to_public_locations(tmp_path: Path):
    source = tmp_path / "twitter" / "count_user_messages" / "reply" / "03.parquet"
    source.parent.mkdir(parents=True)

    category, relative = _canonical_location(tmp_path, "count_user_messages_03", source)
    assert category is ArtifactCategory.DATA
    assert relative == Path("data/metrics/count_user_messages/03.parquet")

    summary_source = (
        tmp_path / "twitter" / "communities" / "summary" / "absolute" / "03.parquet"
    )
    summary_source.parent.mkdir(parents=True)
    category, relative = _canonical_location(
        tmp_path, "community_summary_absolute_03", summary_source
    )
    assert category is ArtifactCategory.DATA
    assert relative == Path("data/communities/summary/absolute/03.parquet")


def test_dashboard_graph_samples_route_to_additive_public_locations(tmp_path: Path):
    source = (
        tmp_path
        / "twitter"
        / "communities"
        / "graph_samples"
        / "absolute"
        / "03.parquet"
    )
    source.parent.mkdir(parents=True)

    assert (
        _base_artifact_key("community_graph_sample_absolute_march")
        == "community_graph_sample_absolute"
    )
    category, relative = _canonical_location(
        tmp_path, "community_graph_sample_absolute_march", source
    )
    assert category is ArtifactCategory.DATA
    assert relative == Path("data/communities/graph_samples/absolute/03.parquet")


def test_community_node_indexes_route_to_public_locations(tmp_path: Path):
    source = (
        tmp_path / "twitter" / "communities" / "node_index" / "absolute" / "03.parquet"
    )
    source.parent.mkdir(parents=True)

    assert (
        _base_artifact_key("community_node_index_absolute_march")
        == "community_node_index_absolute"
    )
    category, relative = _canonical_location(
        tmp_path, "community_node_index_absolute_march", source
    )
    assert category is ArtifactCategory.DATA
    assert relative == Path("data/communities/node_index/absolute/03.parquet")


def test_clustered_theme_keys_route_to_additive_theme_locations(tmp_path: Path):
    source = tmp_path / "theme_clusters" / "monthly" / "2017-03.parquet"
    source.parent.mkdir(parents=True)

    category, relative = _canonical_location(tmp_path, "theme_clusters_2017-03", source)
    assert category is ArtifactCategory.DATA
    assert relative == Path("data/themes/clusters/monthly/2017-03.parquet")

    evidence = tmp_path / "theme_clusters" / "evidence" / "2017-03.parquet"
    evidence.parent.mkdir(parents=True)
    category, relative = _canonical_location(
        tmp_path, "theme_cluster_observations_2017-03", evidence
    )
    assert category is ArtifactCategory.DATA
    assert relative == Path("data/themes/clusters/evidence/2017-03.parquet")

    families = tmp_path / "theme_clusters" / "canonical_families.parquet"
    families.parent.mkdir(parents=True, exist_ok=True)
    category, relative = _canonical_location(
        tmp_path, "theme_canonical_families", families
    )
    assert category is ArtifactCategory.DATA
    assert relative == Path("data/themes/clusters/canonical_families.parquet")


def test_theme_embedding_artifact_routes_to_durable_theme_embedding_location(
    tmp_path: Path,
):
    source = (
        tmp_path / "theme_clusters" / "embeddings" / "clustering_general_themes.parquet"
    )
    source.parent.mkdir(parents=True)

    category, relative = _canonical_location(
        tmp_path, "theme_embeddings_clustering", source
    )
    assert category is ArtifactCategory.DATA
    assert relative == Path("data/themes/embeddings/clustering_general_themes.parquet")


def test_theme_similarity_embedding_artifact_routes_to_durable_theme_embedding_location(
    tmp_path: Path,
):
    source = tmp_path / "theme_similarity" / "embeddings" / "similarity_themes.parquet"
    source.parent.mkdir(parents=True)

    category, relative = _canonical_location(
        tmp_path, "theme_embeddings_similarity", source
    )
    assert category is ArtifactCategory.DATA
    assert relative == Path("data/themes/embeddings/similarity_themes.parquet")


def test_community_evolution_read_models_route_to_durable_evolution_locations(
    tmp_path: Path,
):
    for key, filename in (
        ("community_paths", "community_paths.parquet"),
        ("community_path_membership", "community_path_membership.parquet"),
        ("community_path_theme_similarity", "community_path_theme_similarity.parquet"),
    ):
        source = tmp_path / "theme-output" / filename
        source.parent.mkdir(parents=True, exist_ok=True)
        category, relative = _canonical_location(tmp_path, key, source)
        assert category is ArtifactCategory.DATA
        assert relative == Path(f"data/evolution/{filename}")
