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

from src.artifacts import RunStatus, load_run_manifest, validate_run_manifest
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
from src.reporting.output_contract import get_required_columns_by_artifact

COMMUNITY_MESSAGE_FRAME = pd.DataFrame(
    {
        "community_number": [1],
        "messages": [["hello"]],
        "messages_ids": [["m1"]],
        "total_messages": [1],
    }
)
MATCHED_COMMUNITY_FRAME = pd.DataFrame(
    {
        "abs_community": [1],
        "per_community": [2],
        "jaccard_score": [1.0],
        "members": [["u1"]],
    }
)


def _schema_frame(schema_name: str) -> pd.DataFrame:
    columns = get_required_columns_by_artifact()[schema_name]
    values = {}
    for column in columns:
        if any(
            token in column
            for token in ("members", "keywords", "theme_names", "theme_gpt")
        ):
            values[column] = [["value"]]
        elif column in {
            "month",
            "start_month",
            "end_month",
            "created_at",
        }:
            values[column] = ["march"]
        elif any(
            token in column
            for token in ("community", "total", "score", "user", "messages")
        ):
            values[column] = [1]
        else:
            values[column] = ["value"]
    return pd.DataFrame(values)


THEME_INPUT_FRAME = _schema_frame("matched_lda")


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


def _ref(
    path: Path, *, media_type: str = "application/octet-stream"
) -> ArtifactReference:
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
    absolute = root / "absolute.parquet"
    weighted = root / "weighted.parquet"
    matched = root / "matched.parquet"
    COMMUNITY_MESSAGE_FRAME.to_parquet(absolute, index=False)
    COMMUNITY_MESSAGE_FRAME.to_parquet(weighted, index=False)
    MATCHED_COMMUNITY_FRAME.to_parquet(matched, index=False)
    return TopicInputBundle(
        absolute_community_messages=_ref(absolute),
        weighted_community_messages=_ref(weighted),
        matched_communities=_ref(matched),
        partial_matched_communities=None,
        allowed_input_roots=(str(root),),
    )


def _write_theme_input(root: Path, month: str = "march") -> ThemeInputBundle:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{month}_2017.parquet"
    THEME_INPUT_FRAME.to_parquet(path, index=False)
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

    scores = out / data_type / "LDA" / "scores" / content_type / f"{month}.parquet"
    matched = (
        out / data_type / "LDA" / "matched" / content_type / f"{month}_{year}.parquet"
    )
    manifest = (
        out
        / data_type
        / "_intermediate"
        / "theme_inputs"
        / content_type
        / str(year)
        / "manifest.json"
    )
    scores.parent.mkdir(parents=True, exist_ok=True)
    matched.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    _schema_frame("lda_scores").to_parquet(scores, index=False)
    THEME_INPUT_FRAME.to_parquet(matched, index=False)
    manifest.write_text('{"schema_version": 1}\n', encoding="utf-8")


def _fake_theme_domain(**kwargs) -> None:
    out = Path(kwargs["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    year = kwargs["year"]
    for month in kwargs["monthly_data_dict"]:
        _schema_frame("themed_output").to_parquet(
            out / f"{month}_{year}_with_themes.parquet", index=False
        )
    _schema_frame("community_transition").to_parquet(
        out / "community_transition.parquet", index=False
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

    parquet_paths = {
        "network_data": (
            out / data_type / "network_data" / content_type / f"{month}{year}.parquet"
        ),
        "user_centrality": (
            out / data_type / "user_centrality" / content_type / f"{month}.parquet"
        ),
        "count_user_messages": (
            out / data_type / "count_user_messages" / content_type / f"{month}.parquet"
        ),
        "daily_messages_stat": (
            out / data_type / "daily_messages_stat" / content_type / f"{month}.parquet"
        ),
        "matched_communities": (
            out
            / data_type
            / "communities"
            / "matched"
            / content_type
            / f"{month}.parquet"
        ),
    }
    for schema_name, path in parquet_paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        _schema_frame(schema_name).to_parquet(path, index=False)

    topic_root = (
        out
        / data_type
        / "_intermediate"
        / "topic_inputs"
        / content_type
        / f"{month}_{year}"
    )
    topic_root.mkdir(parents=True, exist_ok=True)
    COMMUNITY_MESSAGE_FRAME.to_parquet(
        topic_root / "absolute_community_messages.parquet", index=False
    )
    COMMUNITY_MESSAGE_FRAME.to_parquet(
        topic_root / "weighted_community_messages.parquet", index=False
    )
    MATCHED_COMMUNITY_FRAME.to_parquet(
        topic_root / "matched_communities.parquet", index=False
    )
    (topic_root / "manifest.json").write_text(
        '{"schema_version": 1}\n', encoding="utf-8"
    )


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
    if type(obj).__name__ in {
        "Dictionary",
        "LdaModel",
        "LdaMulticore",
        "Client",
        "Session",
        "MlflowClient",
        "Run",
        "ActiveRun",
    }:
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
    run_root = output_root / "runs" / result.context.pipeline_run_id
    assert run_root.is_dir()
    manifest = load_run_manifest(run_root)
    assert manifest.status is RunStatus.COMPLETED
    assert validate_run_manifest(run_root) == manifest
    assert {record.key for record in manifest.artifacts} == {
        ref.asset_key for ref in result.artifacts
    }
    assert all((run_root / record.path).is_file() for record in manifest.artifacts)
    resolved_config = (run_root / "resolved_config.yaml").read_text(encoding="utf-8")
    assert "must-not-persist" not in resolved_config
    assert "credentials" not in resolved_config
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
