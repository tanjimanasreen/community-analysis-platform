from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pytest

from src.api.errors import ArtifactUnavailableError, InvalidFilterError
from src.api.services.theme_trend_service import ThemeTrendService


@dataclass
class Record:
    key: str
    path: str


class Manifest:
    dataset = {"date_start": "2017-01-01", "date_end": "2017-04-30"}


class Catalog:
    def get_manifest(self, run_id: str):
        assert run_id == "run-theme"
        return Manifest()


class Reader:
    def __init__(self, frames: dict[str, pd.DataFrame]):
        self.frames = frames
        self.catalog = Catalog()
        self.read_keys: list[str] = []

    def find_records(self, run_id: str, *, key_prefix: str):
        assert run_id == "run-theme"
        assert key_prefix == "themes_"
        return [Record(key, f"data/themes/{key}.parquet") for key in self.frames]

    def read_parquet_record(self, run_id: str, record: Record):
        assert run_id == "run-theme"
        self.read_keys.append(record.key)
        return self.frames[record.key].copy()

    def read_safe_config(self, run_id: str):
        assert run_id == "run-theme"
        return {"year": "2017"}


def row(
    absolute,
    weighted,
    general,
    *,
    all_keywords=None,
    absolute_names=None,
    weighted_names=None,
    absolute_keywords=None,
    weighted_keywords=None,
):
    return {
        "absolute_community": absolute,
        "weighted_community": weighted,
        "general_theme_names": general,
        "general_theme_gpt": None,
        "absolute_theme_names": absolute_names,
        "absolute_theme_gpt": None,
        "weighted_theme_names": weighted_names,
        "weighted_theme_gpt": None,
        "all_keywords": all_keywords,
        "absolute_keywords": absolute_keywords,
        "weighted_keywords": weighted_keywords,
    }


def service(frames: dict[str, list[dict]]) -> ThemeTrendService:
    return ThemeTrendService(
        Reader({key: pd.DataFrame(records) for key, records in frames.items()})
    )


def test_monthly_uses_distinct_pairs_exact_labels_and_general_precedence():
    result = service(
        {
            "themes_01": [
                row(1, 11, ["Policy"], all_keywords=["ban", "court"]),
                row(1, 11, ["Policy"], all_keywords=["ban", "appeal"]),
                row(2, 12, ["Policy", "Protest"], all_keywords=["protest", "ban"]),
                row(
                    3,
                    13,
                    None,
                    absolute_names=["Fallback IF"],
                    weighted_names=["Fallback WIF"],
                    absolute_keywords=["if-keyword"],
                    weighted_keywords=["wif-keyword"],
                ),
                row(None, None, ["Excluded"], all_keywords=["ignored"]),
            ]
        }
    ).monthly("run-theme", period="2017-01")

    assert result["complete"] is True
    assert result["total_themed_community_pairs"] == 3
    assert result["excluded_records_without_pair"] == 1
    assert [item["name"] for item in result["themes"]] == [
        "Policy",
        "Fallback IF",
        "Fallback WIF",
        "Protest",
    ]
    policy = result["themes"][0]
    assert policy["community_count"] == 2
    assert policy["percentage"] == 66.666667
    assert policy["keywords"][:3] == ["ban", "court", "appeal"]
    assert len(policy["community_pairs"]) == 2


def test_exact_labels_are_not_merged_by_topic_or_case_similarity():
    result = service(
        {
            "themes_01": [
                row(1, 1, ["Travel Ban"], all_keywords=["ban"]),
                row(2, 2, ["travel ban"], all_keywords=["court"]),
                row(3, 3, ["Travel-Ban"], all_keywords=["policy"]),
            ]
        }
    ).monthly("run-theme", period="2017-01")

    assert [item["name"] for item in result["themes"]] == [
        "Travel Ban",
        "Travel-Ban",
        "travel ban",
    ]


def test_timeline_ranks_exact_label_by_community_month_tie_breaks():
    result = service(
        {
            "themes_01": [
                row(1, 1, ["Policy"], all_keywords=["ban"]),
                row(2, 2, ["Activism"], all_keywords=["protest"]),
            ],
            "themes_02": [
                row(3, 3, ["Policy"], all_keywords=["court"]),
                row(4, 4, ["Policy"], all_keywords=["ban"]),
                row(5, 5, ["Activism"], all_keywords=["rally"]),
            ],
            "themes_03": [
                row(6, 6, ["Activism"], all_keywords=["protest"]),
                row(7, 7, ["Activism"], all_keywords=["rights"]),
            ],
        }
    ).timeline("run-theme", period_start="2017-01", period_end="2017-03")

    assert result["available_periods"] == ["2017-01", "2017-02", "2017-03"]
    assert result["periods"] == ["2017-01", "2017-02", "2017-03"]
    leader = result["most_discussed_theme"]
    assert leader["name"] == "Activism"
    assert leader["total_community_month_count"] == 4
    assert leader["months_present"] == 3
    assert leader["peak_period"] == "2017-03"
    assert [point["community_count"] for point in leader["series"]] == [1, 1, 2]
    assert leader["keywords"][:2] == ["protest", "rally"]


def test_reads_only_artifacts_needed_for_the_requested_period_or_range():
    reader = Reader(
        {
            "themes_01": pd.DataFrame([row(1, 1, ["January"])]),
            "themes_02": pd.DataFrame([row(2, 2, ["February"])]),
            "themes_03": pd.DataFrame([row(3, 3, ["March"])]),
        }
    )
    trend_service = ThemeTrendService(reader)

    trend_service.monthly("run-theme", period="2017-02")
    assert reader.read_keys == ["themes_02"]

    reader.read_keys.clear()
    trend_service.timeline("run-theme", period_start="2017-02", period_end="2017-03")
    assert reader.read_keys == ["themes_02", "themes_03"]


def test_timeline_handles_more_than_500_records_without_pagination():
    records = [
        row(index, index, ["Large Theme"], all_keywords=["evidence"])
        for index in range(650)
    ]
    result = service({"themes_04": records}).timeline("run-theme")

    assert result["complete"] is True
    assert result["source_record_count"] == 650
    assert result["monthly_summaries"][0]["total_themed_community_pairs"] == 650
    assert result["most_discussed_theme"]["total_community_month_count"] == 650


def test_timeline_orders_periods_across_year_boundaries():
    result = service(
        {
            "themes_2017-01": [row(2, 2, ["January"], all_keywords=["new"])],
            "themes_2016-12": [row(1, 1, ["December"], all_keywords=["old"])],
        }
    ).timeline("run-theme")

    assert result["periods"] == ["2016-12", "2017-01"]
    assert [item["period"] for item in result["monthly_summaries"]] == [
        "2016-12",
        "2017-01",
    ]


def test_provider_mapping_fields_are_normalized_without_external_calls():
    frame = pd.DataFrame(
        [
            {
                **row(1, 1, None),
                "general_theme_gpt": '{"Policy": ["ban", "court"]}',
                "absolute_theme_gpt": None,
                "weighted_theme_gpt": None,
            }
        ]
    )
    result = ThemeTrendService(Reader({"themes_01": frame})).monthly(
        "run-theme", period="2017-01"
    )

    assert result["themes"][0]["name"] == "Policy"
    assert result["themes"][0]["keywords"] == ["ban", "court"]


def test_provider_mapping_keeps_keywords_with_their_exact_label():
    frame = pd.DataFrame(
        [
            {
                **row(1, 1, None),
                "general_theme_gpt": '{"Policy": ["ban"], "Activism": ["protest"]}',
                "absolute_theme_gpt": None,
                "weighted_theme_gpt": None,
            }
        ]
    )
    result = ThemeTrendService(Reader({"themes_01": frame})).monthly(
        "run-theme", period="2017-01"
    )

    themes = {item["name"]: item for item in result["themes"]}
    assert themes["Policy"]["keywords"] == ["ban"]
    assert themes["Activism"]["keywords"] == ["protest"]


def test_unavailable_artifacts_and_invalid_ranges_are_explicit():
    empty = ThemeTrendService(Reader({}))
    with pytest.raises(ArtifactUnavailableError):
        empty.timeline("run-theme")

    populated = service({"themes_01": [row(1, 1, ["Policy"])]})
    with pytest.raises(InvalidFilterError):
        populated.timeline("run-theme", period_start="2017-02", period_end="2017-01")
    with pytest.raises(InvalidFilterError):
        populated.monthly("run-theme", period="January 2017")
    with pytest.raises(InvalidFilterError):
        populated.timeline("run-theme", scope="partial")
