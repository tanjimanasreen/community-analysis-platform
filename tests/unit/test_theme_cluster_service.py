from types import SimpleNamespace

import pandas as pd

from src.api.services.theme_cluster_service import ThemeClusterService


class FakeReader:
    def __init__(self, frames):
        self.frames = frames

    def find_records(self, run_id, *, key_prefix=None, **kwargs):
        return [
            SimpleNamespace(key=key)
            for key in self.frames
            if key.startswith(key_prefix or "")
        ]

    def read_parquet_record(self, run_id, record):
        return self.frames[record.key].copy()


def _summary(period, theme_id, label, count, denominator, keywords):
    return pd.DataFrame(
        [
            {
                "period": period,
                "canonical_theme_id": theme_id,
                "canonical_theme_label": label,
                "community_count": count,
                "total_themed_community_pairs": denominator,
                "percentage": count * 100.0 / denominator,
                "prominent_keywords": str(keywords),
                "monthly_cluster_ids": '["mc_1"]',
                "monthly_representative_themes": str([label]),
                "source_general_theme_labels": str([label, f"{label} variant"]),
                "community_pairs": '[{"absolute_community":"1","weighted_community":"11","source_labels":["x"],"keywords":["k"]}]',
                "mean_membership_probability": 0.9,
                "source_observation_count": 4,
                "excluded_records_missing_general_theme": 1,
                "excluded_records_ambiguous_general_theme_serialization": 2,
                "monthly_noise_observation_count": 1,
                "embedding_provider": "tei",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "monthly_cluster_contract_version": "1.0",
                "canonicalization_contract_version": "1.0",
            }
        ]
    )


def test_monthly_and_timeline_read_saved_clusters_without_recomputation():
    frames = {
        "theme_clusters_2017-01": _summary(
            "2017-01", "ct_a", "Immigration", 3, 4, ["immigration", "ban"]
        ),
        "theme_clusters_2017-02": _summary(
            "2017-02", "ct_a", "Immigration", 4, 5, ["immigration", "court"]
        ),
    }
    service = ThemeClusterService(FakeReader(frames))

    monthly = service.monthly("run-1", period="2017-01")
    timeline = service.timeline("run-1")

    assert monthly["themes"][0]["theme_id"] == "ct_a"
    assert monthly["themes"][0]["community_count"] == 3
    assert monthly["embedding_model"] == "sentence-transformers/all-MiniLM-L6-v2"
    assert timeline["periods"] == ["2017-01", "2017-02"]
    assert monthly["excluded_records_ambiguous_general_theme_serialization"] == 2
    assert timeline["excluded_records_ambiguous_general_theme_serialization"] == 4
    assert timeline["distinct_canonical_theme_count"] == 1
    assert timeline["most_discussed_theme"]["theme_id"] == "ct_a"
    assert timeline["most_discussed_theme"]["total_community_month_count"] == 7
    assert [
        point["community_count"] for point in timeline["most_discussed_theme"]["series"]
    ] == [3, 4]


def test_cluster_evidence_filters_by_canonical_theme_id():
    frames = {
        "theme_clusters_2017-01": _summary(
            "2017-01", "ct_a", "Immigration", 3, 4, ["immigration"]
        ),
        "theme_cluster_observations_2017-01": pd.DataFrame(
            [
                {
                    "period": "2017-01",
                    "canonical_theme_id": "ct_a",
                    "canonical_theme_label": "Immigration",
                    "monthly_cluster_id": "mc_a",
                    "monthly_representative_theme": "US Immigration Policy",
                    "source_general_theme_label": "Trump Immigration Policy",
                    "absolute_community": "1",
                    "weighted_community": "11",
                    "general_keywords": '["trump", "immigration"]',
                    "membership_probability": 0.87,
                },
                {
                    "period": "2017-01",
                    "canonical_theme_id": None,
                    "canonical_theme_label": None,
                    "monthly_cluster_id": None,
                    "monthly_representative_theme": None,
                    "source_general_theme_label": "Noise",
                    "absolute_community": "2",
                    "weighted_community": "12",
                    "general_keywords": '["noise"]',
                    "membership_probability": 0.0,
                },
            ]
        ),
    }
    service = ThemeClusterService(FakeReader(frames))

    response = service.evidence(
        "run-1", period="2017-01", canonical_theme_id="ct_a", limit=10, offset=0
    )

    assert response["total"] == 1
    assert (
        response["records"][0]["source_general_theme_label"]
        == "Trump Immigration Policy"
    )
    assert response["records"][0]["keywords"] == ["trump", "immigration"]


def test_cluster_schema_accepts_ambiguous_serialization_diagnostic():
    from src.api.schemas.themes import MonthlyClusteredThemeResponse

    service = ThemeClusterService(
        FakeReader(
            {
                "theme_clusters_2017-03": _summary(
                    "2017-03", "ct_a", "Immigration", 3, 4, ["immigration"]
                )
            }
        )
    )
    payload = service.monthly("run-1", period="2017-03")
    validated = MonthlyClusteredThemeResponse.model_validate(payload)
    assert validated.excluded_records_ambiguous_general_theme_serialization == 2


def test_legacy_cluster_artifact_without_new_diagnostic_remains_readable():
    legacy = _summary("2017-03", "ct_a", "Immigration", 3, 4, ["immigration"]).drop(
        columns=["excluded_records_ambiguous_general_theme_serialization"]
    )
    service = ThemeClusterService(FakeReader({"theme_clusters_2017-03": legacy}))

    payload = service.monthly("run-legacy", period="2017-03")

    assert payload["excluded_records_ambiguous_general_theme_serialization"] == 0
