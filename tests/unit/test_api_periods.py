from __future__ import annotations

import pytest

from src.api.errors import InvalidFilterError
from src.api.services.periods import (
    discover_periods,
    period_bounds,
    record_period,
    select_period_record,
    validate_period,
)
from src.artifacts.models import (
    ArtifactCategory,
    ArtifactRecord,
    RunManifest,
    RunStatus,
)


def _record(key: str, path: str) -> ArtifactRecord:
    return ArtifactRecord(
        key=key,
        path=path,
        category=ArtifactCategory.DATA,
        media_type="application/vnd.apache.parquet",
        schema_version="1",
        sha256="0" * 64,
        rows=1,
        byte_size=1,
        stage="network_community",
    )


def _manifest(*records: ArtifactRecord) -> RunManifest:
    return RunManifest(
        run_id="run-periods",
        status=RunStatus.COMPLETED,
        dataset={
            "platform": "twitter",
            "content_type": "retweet_quote",
            "date_start": None,
            "date_end": None,
        },
        code={},
        pipeline={},
        artifacts=tuple(records),
    )


def test_period_validation_and_calendar_bounds() -> None:
    assert validate_period("2017-04") == (2017, 4)
    assert period_bounds("2024-02") == ("2024-02-01", "2024-02-29")

    with pytest.raises(InvalidFilterError):
        validate_period("2017-13", run_id="run-periods")


def test_period_discovery_prefers_explicit_longitudinal_configuration() -> None:
    manifest = _manifest(
        _record("community_graph_sample_absolute_04", "data/graphs/04.parquet"),
        _record("network_data_03", "data/network/03.parquet"),
    )
    config = {
        "year": 2017,
        "longitudinal_datasets": [
            {"month": "March", "input_path": "data/raw/2017/march.csv"},
            {"month": "04", "input_path": "data/raw/2017/april.csv"},
        ],
    }

    assert discover_periods(manifest, config) == ["2017-03", "2017-04"]


def test_record_period_supports_numeric_and_named_artifact_suffixes() -> None:
    assert (
        record_period(
            _record("network_data_04", "data/network/april.parquet"),
            fallback_year=2017,
        )
        == "2017-04"
    )
    assert (
        record_period(
            _record("network_data_march", "data/network/march.parquet"),
            fallback_year=2017,
        )
        == "2017-03"
    )


def test_select_period_record_returns_exact_month_and_lists_availability() -> None:
    records = [
        _record("communities_absolute_03", "data/communities/03.parquet"),
        _record("communities_absolute_04", "data/communities/04.parquet"),
    ]

    assert (
        select_period_record(
            records,
            period="2017-04",
            fallback_year=2017,
            run_id="run-periods",
            artifact_key="communities_absolute",
        ).key
        == "communities_absolute_04"
    )

    with pytest.raises(InvalidFilterError, match="Available periods: 2017-03, 2017-04"):
        select_period_record(
            records,
            period="2017-05",
            fallback_year=2017,
            run_id="run-periods",
            artifact_key="communities_absolute",
        )
