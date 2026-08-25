import os
from src.orchestration.hashing import hash_mapping, hash_file, build_stage_cache_key


def test_hash_mapping_order_independence():
    dict1 = {"a": 1, "b": 2}
    dict2 = {"b": 2, "a": 1}
    assert hash_mapping(dict1) == hash_mapping(dict2)


def test_hash_mapping_relevance():
    dict1 = {"a": 1, "b": 2}
    dict2 = {"a": 1, "b": 3}
    assert hash_mapping(dict1) != hash_mapping(dict2)


def test_hash_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello", encoding="utf-8")
    h1 = hash_file(str(f))
    f.write_text("hello world", encoding="utf-8")
    h2 = hash_file(str(f))
    assert h1 != h2


def test_build_stage_cache_key():
    key1 = build_stage_cache_key(
        stage="test",
        semantic_version="v1",
        input_hashes=["hashB", "hashA"],
        config_subset={"param": 1},
    )
    key2 = build_stage_cache_key(
        stage="test",
        semantic_version="v1",
        input_hashes=["hashA", "hashB"],  # different order
        config_subset={"param": 1},
    )
    key3 = build_stage_cache_key(
        stage="test",
        semantic_version="v2",
        input_hashes=["hashA", "hashB"],
        config_subset={"param": 1},
    )
    assert key1 == key2
    assert key1 != key3


def test_hash_code_dependencies_changes_when_dependency_changes(tmp_path):
    from src.orchestration.hashing import hash_code_dependencies

    source = tmp_path / "src" / "stage"
    source.mkdir(parents=True)
    module = source / "logic.py"
    module.write_text("VALUE = 1\n", encoding="utf-8")

    before = hash_code_dependencies(["src/stage"], project_root=tmp_path)
    module.write_text("VALUE = 2\n", encoding="utf-8")
    after = hash_code_dependencies(["src/stage"], project_root=tmp_path)

    assert before != after


def test_stage_code_fingerprints_are_deterministic_and_scoped():
    from src.orchestration.hashing import build_stage_code_fingerprint

    network_first = build_stage_code_fingerprint("network_community")
    network_second = build_stage_code_fingerprint("network_community")
    topic = build_stage_code_fingerprint("topic_model")

    assert network_first == network_second
    assert len(network_first) == 64
    assert network_first != topic


def test_stage_code_fingerprint_rejects_unknown_stage():
    import pytest

    from src.orchestration.hashing import build_stage_code_fingerprint

    with pytest.raises(ValueError, match="unknown analytical stage"):
        build_stage_code_fingerprint("unknown")


def test_network_cache_key_is_independent_of_pipeline_run_id(tmp_path):
    from src.orchestration.hashing import network_cache_key_fn
    from src.orchestration.models import (
        DatasetIdentity,
        PipelineRunContext,
        ValidatedRunConfiguration,
    )

    dataset = DatasetIdentity(
        dataset_id="dataset",
        path=str(tmp_path / "input.csv"),
        sha256="a" * 64,
    )
    config = ValidatedRunConfiguration(
        config_digest="digest",
        output_root=str(tmp_path),
        raw_config={
            "data_type": "twitter",
            "content_type": "reply",
            "month": "01",
            "year": "2017",
            "graph_thresholds": {"min_total_post": 10, "min_shared_post": 5},
            "louvain": {"resolution": 1, "seed": 123},
        },
    )
    first = PipelineRunContext.create(
        "run-a", "abc", "digest", str(tmp_path), [dataset]
    )
    second = PipelineRunContext.create(
        "run-b", "def", "digest", str(tmp_path), [dataset]
    )
    params = {"dataset_identity": dataset, "config": config}

    assert network_cache_key_fn(first, params) == network_cache_key_fn(second, params)


def test_artifact_reuse_toggle_does_not_change_analytical_cache_identity(tmp_path):
    from src.orchestration.hashing import network_cache_key_fn
    from src.orchestration.models import DatasetIdentity, ValidatedRunConfiguration

    dataset = DatasetIdentity(
        dataset_id="dataset",
        path=str(tmp_path / "input.csv"),
        sha256="a" * 64,
    )
    base = {
        "data_type": "telegram",
        "content_type": "forward",
        "month": "01",
        "year": "2019",
        "date_column": "forwarded_date",
        "graph_thresholds": {"min_total_post": 10, "min_shared_post": 5},
        "louvain": {"resolution": 1, "seed": 123},
    }
    enabled = ValidatedRunConfiguration(
        "digest-a", str(tmp_path), {**base, "orchestration": {"artifact_reuse": True}}
    )
    disabled = ValidatedRunConfiguration(
        "digest-b", str(tmp_path), {**base, "orchestration": {"artifact_reuse": False}}
    )

    assert network_cache_key_fn(
        None, {"dataset_identity": dataset, "config": enabled}
    ) == network_cache_key_fn(None, {"dataset_identity": dataset, "config": disabled})


def test_topic_cache_key_preserves_input_roles(monkeypatch, tmp_path):
    from src.orchestration import hashing
    from src.orchestration.models import (
        ArtifactReference,
        TopicInputBundle,
        ValidatedRunConfiguration,
    )

    monkeypatch.setattr(hashing, "build_stage_code_fingerprint", lambda _stage: "code")

    def ref(name: str, digest: str) -> ArtifactReference:
        return ArtifactReference(
            path=str(tmp_path / name),
            sha256=digest,
            media_type="application/octet-stream",
            asset_key=name,
        )

    config = ValidatedRunConfiguration("digest", str(tmp_path), {"lda": {}})
    first = TopicInputBundle(
        absolute_community_messages=ref("absolute", "a" * 64),
        weighted_community_messages=ref("weighted", "b" * 64),
        matched_communities=ref("matched", "c" * 64),
        partial_matched_communities=None,
    )
    swapped = TopicInputBundle(
        absolute_community_messages=ref("absolute", "b" * 64),
        weighted_community_messages=ref("weighted", "a" * 64),
        matched_communities=ref("matched", "c" * 64),
        partial_matched_communities=None,
    )

    assert hashing.topic_stage_cache_key(
        first, config
    ) != hashing.topic_stage_cache_key(swapped, config)


def test_theme_cache_key_preserves_period_to_artifact_mapping(monkeypatch, tmp_path):
    from src.orchestration import hashing
    from src.orchestration.models import (
        ArtifactReference,
        ThemeInputBundle,
        ValidatedRunConfiguration,
    )

    monkeypatch.setattr(hashing, "build_stage_code_fingerprint", lambda _stage: "code")

    def ref(name: str, digest: str) -> ArtifactReference:
        return ArtifactReference(
            path=str(tmp_path / name),
            sha256=digest,
            media_type="application/octet-stream",
            asset_key=name,
        )

    config = ValidatedRunConfiguration(
        "digest",
        str(tmp_path),
        {"data_type": "telegram", "content_type": "forwarded_message", "year": 2019},
    )
    first = ThemeInputBundle(
        monthly_topic_outputs={
            "01": ref("jan", "a" * 64),
            "02": ref("feb", "b" * 64),
        }
    )
    swapped = ThemeInputBundle(
        monthly_topic_outputs={
            "01": ref("jan", "b" * 64),
            "02": ref("feb", "a" * 64),
        }
    )

    assert hashing.theme_stage_cache_key(
        first, config
    ) != hashing.theme_stage_cache_key(swapped, config)


def test_topic_cache_key_changes_with_output_routing_config(monkeypatch, tmp_path):
    from src.orchestration import hashing
    from src.orchestration.models import (
        ArtifactReference,
        TopicInputBundle,
        ValidatedRunConfiguration,
    )

    monkeypatch.setattr(hashing, "build_stage_code_fingerprint", lambda _stage: "code")

    def ref(name: str, digest: str) -> ArtifactReference:
        return ArtifactReference(
            path=str(tmp_path / name),
            sha256=digest,
            media_type="application/octet-stream",
            asset_key=name,
        )

    bundle = TopicInputBundle(
        absolute_community_messages=ref("absolute", "a" * 64),
        weighted_community_messages=ref("weighted", "b" * 64),
        matched_communities=ref("matched", "c" * 64),
        partial_matched_communities=None,
    )
    january = ValidatedRunConfiguration(
        "digest-a",
        str(tmp_path),
        {
            "data_type": "twitter",
            "content_type": "reply",
            "month": "01",
            "year": "2017",
        },
    )
    february = ValidatedRunConfiguration(
        "digest-b",
        str(tmp_path),
        {
            "data_type": "twitter",
            "content_type": "reply",
            "month": "02",
            "year": "2017",
        },
    )

    assert hashing.topic_stage_cache_key(
        bundle, january
    ) != hashing.topic_stage_cache_key(bundle, february)


def test_theme_cache_key_excludes_operational_provider_tuning(monkeypatch, tmp_path):
    from src.orchestration import hashing
    from src.orchestration.models import (
        ArtifactReference,
        ThemeInputBundle,
        ValidatedRunConfiguration,
    )

    monkeypatch.setattr(hashing, "build_stage_code_fingerprint", lambda _stage: "code")
    ref = ArtifactReference(
        path=str(tmp_path / "topic.parquet"),
        sha256="a" * 64,
        media_type="application/octet-stream",
        asset_key="matched_communities_topics_01",
    )
    bundle = ThemeInputBundle(monthly_topic_outputs={"01": ref})
    base = {
        "data_type": "telegram",
        "content_type": "forward",
        "year": "2019",
        "theme_provider": {"primary": "openai:gpt-5-nano", "fallback": False},
        "providers": {
            "openai": {
                "rate_limit_rpm": 240,
                "timeout_seconds": 300,
                "max_retries": 2,
                "max_output_tokens": 32768,
                "reasoning_effort": "low",
            }
        },
    }
    first = ValidatedRunConfiguration("a", str(tmp_path), base)
    operational_change = {
        **base,
        "providers": {
            "openai": {
                **base["providers"]["openai"],
                "rate_limit_rpm": 120,
                "timeout_seconds": 600,
            }
        },
    }
    second = ValidatedRunConfiguration("b", str(tmp_path), operational_change)

    assert hashing.theme_stage_cache_key(
        bundle, first
    ) == hashing.theme_stage_cache_key(bundle, second)


def test_theme_cache_key_changes_with_generation_setting(monkeypatch, tmp_path):
    from src.orchestration import hashing
    from src.orchestration.models import (
        ArtifactReference,
        ThemeInputBundle,
        ValidatedRunConfiguration,
    )

    monkeypatch.setattr(hashing, "build_stage_code_fingerprint", lambda _stage: "code")
    ref = ArtifactReference(
        path=str(tmp_path / "topic.parquet"),
        sha256="a" * 64,
        media_type="application/octet-stream",
        asset_key="matched_communities_topics_01",
    )
    bundle = ThemeInputBundle(monthly_topic_outputs={"01": ref})

    def config(reasoning_effort: str) -> ValidatedRunConfiguration:
        return ValidatedRunConfiguration(
            reasoning_effort,
            str(tmp_path),
            {
                "data_type": "telegram",
                "content_type": "forward",
                "year": "2019",
                "theme_provider": {"primary": "openai:gpt-5-nano", "fallback": False},
                "providers": {
                    "openai": {
                        "max_output_tokens": 32768,
                        "reasoning_effort": reasoning_effort,
                    }
                },
            },
        )

    assert hashing.theme_stage_cache_key(
        bundle, config("low")
    ) != hashing.theme_stage_cache_key(bundle, config("medium"))


def test_theme_cache_key_changes_with_canonicalization_contract(monkeypatch, tmp_path):
    from src.orchestration import hashing
    from src.orchestration.models import (
        ArtifactReference,
        ThemeInputBundle,
        ValidatedRunConfiguration,
    )
    from src.themes import theme_clustering

    monkeypatch.setattr(hashing, "build_stage_code_fingerprint", lambda _stage: "code")
    bundle = ThemeInputBundle(
        monthly_topic_outputs={
            "01": ArtifactReference(
                path=str(tmp_path / "topic.parquet"),
                sha256="a" * 64,
                media_type="application/octet-stream",
                asset_key="matched_communities_topics_01",
            )
        }
    )
    config = ValidatedRunConfiguration(
        "digest",
        str(tmp_path),
        {"data_type": "twitter", "content_type": "reply", "year": "2017"},
    )

    monkeypatch.setattr(theme_clustering, "CANONICALIZATION_CONTRACT_VERSION", "3.0")
    legacy_key = hashing.theme_stage_cache_key(bundle, config)
    monkeypatch.setattr(theme_clustering, "CANONICALIZATION_CONTRACT_VERSION", "4.0")
    current_key = hashing.theme_stage_cache_key(bundle, config)

    assert legacy_key != current_key


def test_theme_cache_key_changes_with_monthly_clustering_contract(monkeypatch, tmp_path):
    from src.orchestration import hashing
    from src.orchestration.models import (
        ArtifactReference,
        ThemeInputBundle,
        ValidatedRunConfiguration,
    )
    from src.themes import theme_clustering

    monkeypatch.setattr(hashing, "build_stage_code_fingerprint", lambda _stage: "code")
    bundle = ThemeInputBundle(
        monthly_topic_outputs={
            "06": ArtifactReference(
                path=str(tmp_path / "topic.parquet"),
                sha256="a" * 64,
                media_type="application/octet-stream",
                asset_key="matched_communities_topics_06",
            )
        }
    )
    config = ValidatedRunConfiguration(
        "digest",
        str(tmp_path),
        {"data_type": "telegram", "content_type": "forward", "year": "2019"},
    )

    monkeypatch.setattr(theme_clustering, "MONTHLY_CLUSTER_CONTRACT_VERSION", "2.2")
    legacy_key = hashing.theme_stage_cache_key(bundle, config)
    monkeypatch.setattr(theme_clustering, "MONTHLY_CLUSTER_CONTRACT_VERSION", "3.0")
    current_key = hashing.theme_stage_cache_key(bundle, config)

    assert legacy_key != current_key


def test_theme_cache_key_includes_promoted_stage_a_geometry(monkeypatch, tmp_path):
    from src.orchestration import hashing
    from src.orchestration.models import (
        ArtifactReference,
        ThemeInputBundle,
        ValidatedRunConfiguration,
    )
    from src.themes import theme_clustering

    monkeypatch.setattr(hashing, "build_stage_code_fingerprint", lambda _stage: "code")
    bundle = ThemeInputBundle(
        monthly_topic_outputs={
            "06": ArtifactReference(
                path=str(tmp_path / "topic.parquet"),
                sha256="a" * 64,
                media_type="application/octet-stream",
                asset_key="matched_communities_topics_06",
            )
        }
    )
    config = ValidatedRunConfiguration(
        "digest",
        str(tmp_path),
        {"data_type": "telegram", "content_type": "forward", "year": "2019"},
    )

    monkeypatch.setattr(theme_clustering, "MONTHLY_CLUSTERING_INPUT_NORMALIZED", False)
    monkeypatch.setattr(theme_clustering, "MONTHLY_CLUSTER_SELECTION_METHOD", "eom")
    legacy_key = hashing.theme_stage_cache_key(bundle, config)
    monkeypatch.setattr(theme_clustering, "MONTHLY_CLUSTERING_INPUT_NORMALIZED", True)
    monkeypatch.setattr(theme_clustering, "MONTHLY_CLUSTER_SELECTION_METHOD", "leaf")
    promoted_key = hashing.theme_stage_cache_key(bundle, config)

    assert legacy_key != promoted_key


def test_theme_stage_cache_version_promotes_with_stage_a_contract():
    from src.orchestration.hashing import THEME_STAGE_CACHE_VERSION

    assert THEME_STAGE_CACHE_VERSION == "3.0.0"


def test_topic_cache_key_changes_when_translation_provider_changes(
    monkeypatch, tmp_path
):
    from src.orchestration import hashing
    from src.orchestration.models import (
        ArtifactReference,
        TopicInputBundle,
        ValidatedRunConfiguration,
    )

    monkeypatch.setattr(hashing, "build_stage_code_fingerprint", lambda _stage: "code")

    def ref(name, digest):
        return ArtifactReference(
            path=str(tmp_path / name),
            sha256=digest,
            media_type="application/octet-stream",
            asset_key=name,
        )

    bundle = TopicInputBundle(
        absolute_community_messages=ref("absolute", "a" * 64),
        weighted_community_messages=ref("weighted", "b" * 64),
        matched_communities=ref("matched", "c" * 64),
        partial_matched_communities=None,
    )

    def config(provider, cache_path=".cache/a.sqlite3", timeout=30):
        return ValidatedRunConfiguration(
            provider,
            str(tmp_path),
            {
                "data_type": "telegram",
                "content_type": "forward",
                "month": "02",
                "year": "2019",
                "translation": {
                    "enabled": True,
                    "provider": provider,
                    "target_language": "en",
                    "contract_version": "v1",
                    "cache_path": cache_path,
                    "timeout_seconds": timeout,
                },
            },
        )

    assert hashing.topic_stage_cache_key(
        bundle, config("azure")
    ) != hashing.topic_stage_cache_key(bundle, config("aws"))
    assert hashing.topic_stage_cache_key(
        bundle, config("azure")
    ) == hashing.topic_stage_cache_key(
        bundle, config("azure", cache_path="/tmp/elsewhere.sqlite3", timeout=90)
    )


def test_disabled_translation_provider_does_not_change_topic_cache(
    monkeypatch, tmp_path
):
    from src.orchestration import hashing
    from src.orchestration.models import (
        ArtifactReference,
        TopicInputBundle,
        ValidatedRunConfiguration,
    )

    monkeypatch.setattr(hashing, "build_stage_code_fingerprint", lambda _stage: "code")
    ref = lambda name, digest: ArtifactReference(
        path=str(tmp_path / name),
        sha256=digest,
        media_type="application/octet-stream",
        asset_key=name,
    )
    bundle = TopicInputBundle(
        absolute_community_messages=ref("absolute", "a" * 64),
        weighted_community_messages=ref("weighted", "b" * 64),
        matched_communities=ref("matched", "c" * 64),
        partial_matched_communities=None,
    )
    first = ValidatedRunConfiguration(
        "a", str(tmp_path), {"translation": {"enabled": False, "provider": "azure"}}
    )
    second = ValidatedRunConfiguration(
        "b", str(tmp_path), {"translation": {"enabled": False, "provider": "aws"}}
    )
    assert hashing.topic_stage_cache_key(
        bundle, first
    ) == hashing.topic_stage_cache_key(bundle, second)
