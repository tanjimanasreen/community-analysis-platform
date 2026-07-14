from __future__ import annotations

import dataclasses
import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from unittest.mock import patch

import networkx as nx
import pandas as pd
import pytest
from prefect import flow
from prefect.task_runners import ThreadPoolTaskRunner
from prefect.testing.utilities import prefect_test_harness
from prefect.settings import (
    PREFECT_RESULTS_LOCAL_STORAGE_PATH,
    temporary_settings,
)

from src.orchestration.composition_flow import run_monthly_analysis_flow
from src.orchestration.models import (
    ArtifactReference,
    PipelineRunContext,
    PipelineRunResult,
    ThemeInputBundle,
    ThemeOutputBundle,
    TopicInputBundle,
    TopicOutputBundle,
)
from src.orchestration.tasks import (
    run_monthly_themes_task,
    run_monthly_topic_phase_task,
    validate_run_configuration_task,
)
from src.providers.base import BaseLLMProvider


COMMUNITY_MESSAGE_CSV = pd.DataFrame(
    {
        "community_number": [1],
        "messages": [["hello"]],
        "messages_ids": [["m1"]],
        "total_messages": [1],
    }
)
MATCHED_COMMUNITY_CSV = pd.DataFrame(
    {
        "abs_community": [1],
        "per_community": [2],
        "jaccard_score": [1.0],
        "members": [["u1"]],
    }
)
THEME_INPUT_CSV = pd.DataFrame(
    {
        "members": [["u1"]],
        "absolute_community": [1],
        "weighted_community": [2],
        "absolute_unigram_keywords": [["a"]],
        "absolute_bigram_keywords": [["b"]],
        "weighted_unigram_keywords": [["c"]],
        "weighted_bigram_keywords": [["d"]],
    }
)


@pytest.fixture(autouse=True)
def prefect_harness():
    with prefect_test_harness():
        yield


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_with_result_storage(results_root: Path, callable_, *args, **kwargs):
    results_root.mkdir(parents=True, exist_ok=True)

    with temporary_settings(
        updates={
            PREFECT_RESULTS_LOCAL_STORAGE_PATH: str(results_root),
        }
    ):
        return callable_(*args, **kwargs)


def _ref(path: Path, *, media_type: str = "text/csv") -> ArtifactReference:
    return ArtifactReference(
        path=str(path),
        sha256=_sha256(path),
        media_type=media_type,
        byte_size=path.stat().st_size,
        asset_key=path.stem,
    )


def _full_config(input_path: Path, output_root: Path) -> dict:
    return {
        "output_base_path": str(output_root),
        "input_path": str(input_path),
        "data_type": "twitter",
        "content_type": "reply",
        "month": "march",
        "year": "2017",
        "creator_relation": "REPLIED_TO",
        "spreader_relation": "REPLIED_BY",
        "creator_node_column": "target",
        "spreader_node_column": "target",
        "text_node_column": "source",
        "date_column": "created_at",
        "graph_thresholds": {
            "min_total_post": 0,
            "min_shared_post": 0,
            "min_members": 1,
        },
        "theme_provider": {"primary": "mock", "fallback_chain": []},
        "render_visuals": False,
        "provider": {"credentials": {"token": "must-not-persist"}},
    }


def _context(output_root: Path, run_id: str) -> PipelineRunContext:
    return PipelineRunContext.create(
        pipeline_run_id=run_id,
        git_commit="HEAD",
        config_digest="test-digest",
        output_root=str(output_root),
        datasets=[],
    )


def _write_topic_inputs(root: Path) -> TopicInputBundle:
    root.mkdir(parents=True, exist_ok=True)
    absolute = root / "absolute.csv"
    weighted = root / "weighted.csv"
    matched = root / "matched.csv"
    COMMUNITY_MESSAGE_CSV.to_csv(absolute, index=False)
    COMMUNITY_MESSAGE_CSV.to_csv(weighted, index=False)
    MATCHED_COMMUNITY_CSV.to_csv(matched, index=False)
    return TopicInputBundle(
        absolute_community_messages=_ref(absolute),
        weighted_community_messages=_ref(weighted),
        matched_communities=_ref(matched),
        partial_matched_communities=None,
        allowed_input_roots=(str(root),),
    )


def _write_theme_input(root: Path, month: str = "march") -> ThemeInputBundle:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{month}_2017.csv"
    THEME_INPUT_CSV.to_csv(path, index=False)
    return ThemeInputBundle(
        monthly_topic_outputs={month: _ref(path)},
        allowed_input_roots=(str(root),),
    )


def _fake_topic_domain(**kwargs) -> None:
    out = Path(kwargs["output_dir"])
    data_type = kwargs["data_type"]
    content_type = kwargs["content_type"]
    month = kwargs["month"]
    year = kwargs["year"]

    scores = out / data_type / "LDA" / "scores" / content_type / f"{month}.csv"
    matched = (
        out
        / data_type
        / "LDA"
        / "matched"
        / content_type
        / f"{month}_{year}.csv"
    )
    manifest = (
        out
        / data_type
        / "_intermediate"
        / "theme_inputs"
        / content_type
        / f"{month}_{year}"
        / "manifest.json"
    )
    scores.parent.mkdir(parents=True, exist_ok=True)
    matched.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"month": [month], "score": [0.5]}).to_csv(scores, index=False)
    THEME_INPUT_CSV.to_csv(matched, index=False)
    manifest.write_text("{}\n", encoding="utf-8")


def _fake_theme_domain(**kwargs) -> None:
    out = Path(kwargs["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    year = kwargs["year"]
    for month in kwargs["monthly_data_dict"]:
        pd.DataFrame({"community": [1], "theme": ["Technology"]}).to_csv(
            out / f"{month}_{year}_with_themes.csv", index=False
        )
    pd.DataFrame({"source": [], "target": [], "score": []}).to_csv(
        out / "community_transition.csv", index=False
    )
    sankey = out / "sankey"
    sankey.mkdir(exist_ok=True)
    (sankey / "community_transition.html").write_text("<html></html>", encoding="utf-8")
    (sankey / "stale-debug.png").write_bytes(b"stale")


def _fake_network_domain(**kwargs) -> None:
    out = Path(kwargs["output_dir"])
    data_type = kwargs["data_type"]
    content_type = kwargs["content_type"]
    month = kwargs["month"]
    year = kwargs["year"]

    csv_paths = [
        out / data_type / "network_data" / content_type / f"{month}{year}.csv",
        out / data_type / "user_centrality" / content_type / f"{month}.csv",
        out / data_type / "count_user_messages" / content_type / f"{month}.csv",
        out / data_type / "daily_messages_stat" / content_type / f"{month}.csv",
        out / data_type / "communities" / "matched" / content_type / f"{month}.csv",
    ]
    for path in csv_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"value": [1]}).to_csv(path, index=False)

    topic_root = (
        out
        / data_type
        / "_intermediate"
        / "topic_inputs"
        / content_type
        / f"{month}_{year}"
    )
    topic_root.mkdir(parents=True, exist_ok=True)
    COMMUNITY_MESSAGE_CSV.to_csv(
        topic_root / "absolute_community_messages.csv", index=False
    )
    COMMUNITY_MESSAGE_CSV.to_csv(
        topic_root / "weighted_community_messages.csv", index=False
    )
    MATCHED_COMMUNITY_CSV.to_csv(topic_root / "matched_communities.csv", index=False)
    (topic_root / "manifest.json").write_text("{}\n", encoding="utf-8")


def _assert_result_boundary(obj, path: str = "root") -> None:
    forbidden_types = (
        pd.DataFrame,
        pd.Series,
        nx.Graph,
        nx.DiGraph,
        nx.MultiGraph,
        nx.MultiDiGraph,
        BaseLLMProvider,
    )
    if isinstance(obj, forbidden_types):
        pytest.fail(f"Forbidden type {type(obj)!r} at {path}")
    if type(obj).__name__ in {"Dictionary", "LdaModel", "Client", "Session"}:
        pytest.fail(f"Forbidden type {type(obj)!r} at {path}")
    if isinstance(obj, (bytes, bytearray)) and len(obj) > 1024:
        pytest.fail(f"Large byte payload at {path}: {len(obj)} bytes")

    if dataclasses.is_dataclass(obj):
        for field in dataclasses.fields(obj):
            _assert_result_boundary(getattr(obj, field.name), f"{path}.{field.name}")
    elif isinstance(obj, Mapping):
        for key, value in obj.items():
            normalized = str(key).lower()
            if any(
                token in normalized
                for token in (
                    "prompt",
                    "message",
                    "response",
                    "authorization",
                    "credential",
                    "api_key",
                    "token",
                    "secret",
                    "password",
                )
            ):
                pytest.fail(f"Forbidden result key {key!r} at {path}")
            _assert_result_boundary(value, f"{path}[{key!r}]")
    elif isinstance(obj, (list, tuple, set, frozenset)):
        for index, value in enumerate(obj):
            _assert_result_boundary(value, f"{path}[{index}]")


def _serialized_size(obj) -> int:
    return len(json.dumps(dataclasses.asdict(obj), sort_keys=True).encode("utf-8"))


def _assert_persisted_results_safe(results_root: Path) -> None:
    files = [path for path in results_root.rglob("*") if path.is_file()]
    assert files, "Prefect did not persist any task/flow results"
    combined = b"".join(path.read_bytes() for path in files)
    assert b"must-not-persist" not in combined
    assert len(combined) < 5 * 1024 * 1024


@flow(
    name="topic-only-smoke-flow",
    task_runner=ThreadPoolTaskRunner(max_workers=1),
    persist_result=True,
)
def _topic_only_flow(bundle, config, context) -> TopicOutputBundle:
    validated = validate_run_configuration_task(config)
    return run_monthly_topic_phase_task(bundle, validated, context)


@flow(
    name="theme-only-smoke-flow",
    task_runner=ThreadPoolTaskRunner(max_workers=1),
    persist_result=True,
)
def _theme_only_flow(bundle, config, context) -> ThemeOutputBundle:
    validated = validate_run_configuration_task(config)
    return run_monthly_themes_task(bundle, validated, context)


def test_smoke_topic_phase_alone(monkeypatch, tmp_path):
    results_root = tmp_path / "prefect-results"
    input_path = tmp_path / "unused.csv"
    input_path.write_text("value\n1\n", encoding="utf-8")
    output_root = tmp_path / "output"
    bundle = _write_topic_inputs(tmp_path / "topic-inputs")

    with patch(
        "src.pipelines.social_network_pipeline.run_topic_phase",
        side_effect=_fake_topic_domain,
    ):
        result = _run_with_result_storage(
            results_root,
            _topic_only_flow,
            bundle,
            _full_config(input_path, output_root),
            _context(output_root, "topic-only"),
        )

    assert isinstance(result, TopicOutputBundle)
    assert Path(result.lda_scores.path).is_file()
    _assert_result_boundary(result)
    assert _serialized_size(result) < 100 * 1024
    _assert_persisted_results_safe(results_root)


def test_smoke_theme_phase_alone(monkeypatch, tmp_path):
    results_root = tmp_path / "prefect-results"
    input_path = tmp_path / "unused.csv"
    input_path.write_text("value\n1\n", encoding="utf-8")
    output_root = tmp_path / "output"
    bundle = _write_theme_input(tmp_path / "theme-inputs")

    with patch(
        "src.pipelines.theme_pipeline.run_theme_pipeline_from_monthly_data",
        side_effect=_fake_theme_domain,
    ):
        result = _run_with_result_storage(
            results_root,
            _theme_only_flow,
            bundle,
            _full_config(input_path, output_root),
            _context(output_root, "theme-only"),
        )

    assert isinstance(result, ThemeOutputBundle)
    assert result.provider_run_summary is not None
    assert not any("stale-debug.png" in ref.path for ref in result.visualizations)
    _assert_result_boundary(result)
    assert _serialized_size(result) < 100 * 1024
    _assert_persisted_results_safe(results_root)


def test_smoke_full_network_topic_theme_composition(monkeypatch, tmp_path):
    results_root = tmp_path / "prefect-results"
    dataset = tmp_path / "dataset.csv"
    pd.DataFrame({"value": [1]}).to_csv(dataset, index=False)
    output_root = tmp_path / "output"

    with (
        patch(
            "src.pipelines.social_network_pipeline.run_network_community_pipeline",
            side_effect=_fake_network_domain,
        ),
        patch(
            "src.pipelines.social_network_pipeline.run_topic_phase",
            side_effect=_fake_topic_domain,
        ),
        patch(
            "src.pipelines.theme_pipeline.run_theme_pipeline_from_monthly_data",
            side_effect=_fake_theme_domain,
        ),
    ):
        result = _run_with_result_storage(
            results_root,
            run_monthly_analysis_flow,
            config=_full_config(dataset, output_root),
            dataset_path=str(dataset),
            dataset_id="smoke-dataset",
            run_topics=True,
            run_themes=True,
        )

    assert isinstance(result, PipelineRunResult)
    run_root = output_root / result.context.pipeline_run_id
    assert run_root.is_dir()
    assert result.context.prefect_flow_run_id is not None
    assert any(ref.asset_key == "lda_scores" for ref in result.artifacts)
    assert any(ref.asset_key == "provider_run_summary" for ref in result.artifacts)
    assert not any("stale-debug.png" in ref.path for ref in result.artifacts)
    for ref in result.artifacts:
        assert Path(ref.path).resolve().is_relative_to(run_root.resolve())
        assert Path(ref.path).is_file()
        assert _sha256(Path(ref.path)) == ref.sha256
        assert Path(ref.path).stat().st_size == ref.byte_size
    _assert_result_boundary(result)
    assert _serialized_size(result) < 250 * 1024
    _assert_persisted_results_safe(results_root)
