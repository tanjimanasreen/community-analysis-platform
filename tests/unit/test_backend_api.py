import math
import sys
from pathlib import Path

import pandas as pd
import pytest

from backend.artifact_service import ArtifactNotFoundError, ArtifactService, normalize_value
from src.reporting import output_contract as contract
from src.themes import theme_inputs
from src.topics import topic_inputs


def _config(tmp_path, *, month="03", longitudinal=False):
    return {
        "output_base_path": str(tmp_path / "outputs"),
        "data_type": "twitter",
        "content_type": "reply",
        "month": month,
        "year": "2017",
        "api": {"longitudinal": longitudinal},
        "theme": {
            "output_dir": str(tmp_path / "theme"),
            "render_visuals": False,
        },
    }


def _sample_value(column, row_index=0):
    if column == "absolute_unigram_keywords":
        return "['alpha', 'beta']"
    if column in {
        "absolute_bigram_keywords",
        "weighted_unigram_keywords",
        "weighted_bigram_keywords",
        "messages",
        "absolute_members",
        "weighted_members",
        "common_members",
        "uncommon_members",
    }:
        return "['alpha']"
    if column in {"members", "messages_ids", "start_month_members", "end_month_members"}:
        return "[1, 2]"
    if column in {"all_keywords", "absolute_keywords", "weighted_keywords"}:
        return float("nan") if row_index == 0 else "alpha,beta"
    if "community" in column or column in {"source", "target", "from_id", "forwarder_id"}:
        return row_index + 1
    if column in {"weight", "jaccard_score"}:
        return 1.0
    if column.startswith("total_"):
        return 1
    if column == "month":
        return "03"
    return f"value_{row_index}"


def _write_csv(path, columns, row_count=1):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {column: _sample_value(column, row_index=index) for column in columns}
        for index in range(row_count)
    ]
    pd.DataFrame(rows, columns=columns).to_csv(path, index=False)


def _write_outputs(config, months, *, row_count=3):
    output_base = Path(config["output_base_path"])
    data_type = config["data_type"]
    content_type = config["content_type"]
    year = config["year"]
    base = output_base / data_type
    theme_dir = Path(config["theme"]["output_dir"])

    for month in months:
        _write_csv(base / "network_data" / content_type / f"{month}{year}.csv", contract.NETWORK_DATA_COLUMNS)
        _write_csv(base / "communities" / "graphs" / "absolute" / content_type / f"{month}.csv", contract.COMMUNITY_GRAPH_COLUMNS)
        _write_csv(base / "communities" / "graphs" / "weighted" / content_type / f"{month}.csv", contract.COMMUNITY_GRAPH_COLUMNS)
        _write_csv(base / "communities" / "matched" / content_type / f"{month}.csv", contract.MATCHED_COMMUNITY_SUMMARY_COLUMNS)
        _write_csv(base / "user_centrality" / content_type / f"{month}.csv", contract.USER_CENTRALITY_COLUMNS)
        _write_csv(base / "count_user_messages" / content_type / f"{month}.csv", contract.COUNT_USER_MESSAGES_COLUMNS)
        _write_csv(base / "daily_messages_stat" / content_type / f"{month}.csv", contract.DAILY_MESSAGES_STAT_COLUMNS)
        _write_csv(base / "LDA" / "scores" / content_type / f"{month}.csv", contract.LDA_SCORES_COLUMNS)
        matched_lda = base / "LDA" / "matched" / content_type / f"{month}_{year}.csv"
        _write_csv(matched_lda, contract.MATCHED_LDA_COLUMNS, row_count=row_count)
        _write_csv(theme_dir / f"{month}_{year}_with_themes.csv", contract.THEMED_OUTPUT_COLUMNS, row_count=row_count)
        theme_inputs.save_theme_inputs(
            matched_lda_csv=matched_lda,
            output_base_path=str(output_base),
            data_type=data_type,
            content_type=content_type,
            month=month,
            year=year,
        )
        topic_inputs.save_topic_inputs(
            absolute_community_messages=pd.DataFrame(
                {"community_number": [1], "messages": [["alpha"]], "messages_ids": [[1]], "total_messages": [1]}
            ),
            weighted_community_messages=pd.DataFrame(
                {"community_number": [1], "messages": [["alpha"]], "messages_ids": [[1]], "total_messages": [1]}
            ),
            matched_communities=pd.DataFrame(
                {"abs_community": [1], "per_community": [1], "jaccard_score": [1.0], "members": [[1, 2]]}
            ),
            partial_matched_communities=pd.DataFrame(columns=topic_inputs.PARTIAL_MATCHED_COMMUNITY_COLUMNS),
            output_base_path=str(output_base),
            data_type=data_type,
            content_type=content_type,
            month=month,
            year=year,
        )

    _write_csv(theme_dir / "community_transition.csv", contract.COMMUNITY_TRANSITION_COLUMNS)


def _client(config):
    from fastapi.testclient import TestClient

    from backend.main import create_app

    return TestClient(create_app(configs={"sample": config}))


def test_service_registers_runs_and_discovers_facets(tmp_path):
    config = _config(tmp_path)
    _write_outputs(config, ["03"])
    service = ArtifactService(configs={"sample": config})

    assert service.health()["read_only"] is True
    assert service.list_runs()[0]["run_id"] == "sample"
    assert service.facets("sample") == {
        "data_types": ["twitter"],
        "content_types": ["reply"],
        "years": ["2017"],
        "months": ["03"],
    }


def test_service_reads_tables_and_paginates(tmp_path):
    config = _config(tmp_path)
    _write_outputs(config, ["03"], row_count=3)
    service = ArtifactService(configs={"sample": config})

    page = service.topics("sample", "03", "matched", limit=1, offset=1)

    assert page["total"] == 3
    assert len(page["records"]) == 1
    assert page["limit"] == 1
    assert page["offset"] == 1
    assert page["records"][0]["absolute_unigram_keywords"] == ["alpha", "beta"]


def test_service_optional_missing_and_required_missing(tmp_path):
    config = _config(tmp_path)
    _write_outputs(config, ["03"])
    service = ArtifactService(configs={"sample": config})

    optional = service.communities("sample", "03", "partial", limit=100, offset=0)
    assert optional["missing"] is True
    assert optional["records"] == []

    required = Path(config["output_base_path"]) / "twitter" / "communities" / "matched" / "reply" / "03.csv"
    required.unlink()
    with pytest.raises(ArtifactNotFoundError):
        service.communities("sample", "03", "matched", limit=100, offset=0)


def test_normalize_value_handles_json_nulls_and_scalars():
    assert normalize_value(float("nan")) is None
    assert normalize_value(pd.NaT) is None
    assert normalize_value(pd.Series([1]).iloc[0]) == 1
    assert normalize_value("['a', 'b']") == ["a", "b"]
    assert normalize_value("{'a': 1}") == {"a": 1}
    assert normalize_value("plain text") == "plain text"
    assert math.isnan(float("nan"))


def test_fastapi_health_runs_facets_and_verification(tmp_path):
    config = _config(tmp_path)
    _write_outputs(config, ["03"])
    client = _client(config)

    assert client.get("/api/v1/health").json()["read_only"] is True
    assert client.get("/api/v1/runs").json()["runs"][0]["run_id"] == "sample"
    assert client.get("/api/v1/runs/sample/facets").json()["months"] == ["03"]
    assert client.get("/api/v1/runs/sample/verification").json()["ok"] is True


def test_fastapi_metadata_hides_absolute_paths(tmp_path):
    config = _config(tmp_path)
    _write_outputs(config, ["03"])
    client = _client(config)

    runs = client.get("/api/v1/runs").json()["runs"]
    artifacts = client.get("/api/v1/runs/sample/artifacts").json()["artifacts"]

    assert str(tmp_path) not in str(runs)
    assert str(tmp_path) not in str(artifacts)
    assert all(item["relative_path"].startswith(("output/", "theme/")) for item in artifacts)


def test_fastapi_longitudinal_facets_discover_manifest_months(tmp_path):
    config = _config(tmp_path, month="04", longitudinal=True)
    _write_outputs(config, ["03", "04"])
    client = _client(config)

    response = client.get("/api/v1/runs/sample/facets")

    assert response.status_code == 200
    assert response.json()["months"] == ["03", "04"]


def test_fastapi_table_pagination_and_json_normalization(tmp_path):
    config = _config(tmp_path)
    _write_outputs(config, ["03"], row_count=3)
    client = _client(config)

    response = client.get("/api/v1/runs/sample/themes?month=03&limit=2&offset=0")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["records"]) == 2
    assert body["records"][0]["all_keywords"] is None
    assert body["records"][0]["absolute_unigram_keywords"] == ["alpha", "beta"]


def test_fastapi_missing_required_artifact_returns_404(tmp_path):
    config = _config(tmp_path)
    _write_outputs(config, ["03"])
    missing = Path(config["output_base_path"]) / "twitter" / "LDA" / "matched" / "reply" / "03_2017.csv"
    missing.unlink()
    client = _client(config)

    response = client.get("/api/v1/runs/sample/topics?month=03&type=matched")

    assert response.status_code == 404
    assert "Missing required artifact" in response.json()["detail"]


def test_fastapi_optional_files_are_reported_missing(tmp_path):
    config = _config(tmp_path)
    _write_outputs(config, ["03"])
    client = _client(config)

    response = client.get("/api/v1/runs/sample/files")

    assert response.status_code == 200
    files = response.json()["files"]
    assert {item["category"] for item in files} == {"sankey", "membership_changes", "theme_similarity"}
    assert all(item["exists"] is False for item in files)


def test_verification_endpoint_reports_contract_failure_without_500(tmp_path):
    config = _config(tmp_path)
    _write_outputs(config, ["03"])
    broken = Path(config["output_base_path"]) / "twitter" / "network_data" / "reply" / "032017.csv"
    broken.unlink()
    client = _client(config)

    response = client.get("/api/v1/runs/sample/verification")

    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert "Missing required artifact" in response.json()["error"]


def test_api_does_not_import_or_call_pipeline_modules(tmp_path):
    for module_name in [
        "src.pipelines.social_network_pipeline",
        "src.pipelines.theme_pipeline",
        "src.topics.lda",
        "src.themes.theme_similarity",
    ]:
        sys.modules.pop(module_name, None)

    config = _config(tmp_path)
    _write_outputs(config, ["03"])
    client = _client(config)

    assert client.get("/api/v1/runs/sample/community-summary?month=03").status_code == 200
    assert "src.pipelines.social_network_pipeline" not in sys.modules
    assert "src.pipelines.theme_pipeline" not in sys.modules
    assert "src.topics.lda" not in sys.modules
    assert "src.themes.theme_similarity" not in sys.modules
