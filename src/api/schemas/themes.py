from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ThemeRecord(StrictModel):
    month: str | None = None
    absolute_community: str | int | None = None
    absolute_unigram_topic: Any = None
    absolute_unigram_keywords: Any = None
    weighted_community: str | int | None = None
    weighted_unigram_topic: Any = None
    weighted_unigram_keywords: Any = None
    absolute_bigram_topic: Any = None
    absolute_bigram_keywords: Any = None
    weighted_bigram_topic: Any = None
    weighted_bigram_keywords: Any = None
    members: Any = None
    general_theme_gpt: Any = None
    general_theme_names: Any = None
    absolute_theme_gpt: Any = None
    absolute_theme_names: Any = None
    weighted_theme_gpt: Any = None
    weighted_theme_names: Any = None
    all_keywords: Any = None
    absolute_keywords: Any = None
    weighted_keywords: Any = None


class ThemesResponse(StrictModel):
    run_id: str
    records: list[ThemeRecord]
    total: int
    limit: int
    offset: int
    provider_metadata: dict[str, Any] | None = None


class ThemeCommunityPairEvidence(StrictModel):
    absolute_community: str | None = None
    weighted_community: str | None = None
    keywords: list[str] = Field(default_factory=list)


class ThemeTrendItem(StrictModel):
    name: str
    community_count: int
    percentage: float
    keywords: list[str]
    community_pairs: list[ThemeCommunityPairEvidence]


class MonthlyThemeTrendResponse(StrictModel):
    run_id: str
    scope: str
    period: str
    complete: bool
    source_record_count: int
    excluded_records_without_pair: int
    total_themed_community_pairs: int
    distinct_exact_theme_count: int
    themes: list[ThemeTrendItem]


class ThemeTrendSeriesPoint(StrictModel):
    period: str
    community_count: int
    total_themed_community_pairs: int
    percentage: float


class DominantThemeTrend(StrictModel):
    name: str
    total_community_month_count: int
    months_present: int
    peak_period: str
    peak_month_count: int
    series: list[ThemeTrendSeriesPoint]
    keywords: list[str]


class MonthlyThemeTrendSummary(StrictModel):
    period: str
    source_record_count: int
    excluded_records_without_pair: int
    total_themed_community_pairs: int
    distinct_exact_theme_count: int
    themes: list[ThemeTrendItem]


class ThemeTimelineResponse(StrictModel):
    run_id: str
    scope: str
    available_periods: list[str]
    periods: list[str]
    complete: bool
    source_record_count: int
    excluded_records_without_pair: int
    monthly_summaries: list[MonthlyThemeTrendSummary]
    most_discussed_theme: DominantThemeTrend | None = None


class ClusteredThemeCommunityPairEvidence(StrictModel):
    absolute_community: str | None = None
    weighted_community: str | None = None
    source_labels: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class ClusteredThemeItem(StrictModel):
    theme_id: str
    name: str
    community_count: int
    percentage: float
    keywords: list[str] = Field(default_factory=list)
    monthly_cluster_ids: list[str] = Field(default_factory=list)
    monthly_representative_themes: list[str] = Field(default_factory=list)
    source_theme_labels: list[str] = Field(default_factory=list)
    community_pairs: list[ClusteredThemeCommunityPairEvidence] = Field(
        default_factory=list
    )
    mean_membership_probability: float | None = None


class MonthlyClusteredThemeSummary(StrictModel):
    period: str
    source_observation_count: int
    excluded_records_missing_general_theme: int
    excluded_records_ambiguous_general_theme_serialization: int
    monthly_noise_observation_count: int
    total_themed_community_pairs: int
    distinct_clustered_theme_count: int
    themes: list[ClusteredThemeItem]
    embedding_provider: str | None = None
    embedding_model: str | None = None
    monthly_cluster_contract_version: str | None = None
    canonicalization_contract_version: str | None = None


class MonthlyClusteredThemeResponse(MonthlyClusteredThemeSummary):
    run_id: str
    scope: str
    complete: bool


class ClusteredThemeSeriesPoint(StrictModel):
    period: str
    community_count: int
    total_themed_community_pairs: int
    percentage: float


class DominantClusteredTheme(StrictModel):
    theme_id: str
    name: str
    total_community_month_count: int
    months_present: int
    peak_period: str
    peak_month_count: int
    series: list[ClusteredThemeSeriesPoint]
    keywords: list[str] = Field(default_factory=list)


class ClusteredThemeTimelineResponse(StrictModel):
    run_id: str
    scope: str
    available_periods: list[str]
    periods: list[str]
    complete: bool
    source_observation_count: int
    excluded_records_missing_general_theme: int
    excluded_records_ambiguous_general_theme_serialization: int
    monthly_noise_observation_count: int
    distinct_canonical_theme_count: int
    monthly_summaries: list[MonthlyClusteredThemeSummary]
    most_discussed_theme: DominantClusteredTheme | None = None


class ClusteredThemeEvidenceRecord(StrictModel):
    period: str
    canonical_theme_id: str | None = None
    canonical_theme_label: str | None = None
    monthly_cluster_id: str | None = None
    monthly_representative_theme: str | None = None
    source_general_theme_label: str
    absolute_community: str | None = None
    weighted_community: str | None = None
    keywords: list[str] = Field(default_factory=list)
    membership_probability: float | None = None


class ClusteredThemeEvidenceResponse(StrictModel):
    run_id: str
    period: str
    canonical_theme_id: str
    records: list[ClusteredThemeEvidenceRecord]
    total: int
    limit: int
    offset: int
