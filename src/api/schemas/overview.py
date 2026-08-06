from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TopTheme(StrictModel):
    name: str
    count: int


class OverviewPeriod(StrictModel):
    period: str = Field(description="Canonical calendar period in YYYY-MM form.")
    if_users: int | None = None
    wif_users: int | None = None
    if_messages: int | None = None
    wif_messages: int | None = None
    interaction_records: int | None = Field(
        default=None,
        description="Rows in the canonical monthly network artifact.",
    )
    if_community_count: int | None = None
    wif_community_count: int | None = None
    matched_community_count: int | None = None
    matched_percentage: float | None = None


class OverviewRunSummary(StrictModel):
    interaction_records: int | None = Field(
        default=None,
        description="Rows across all canonical monthly network artifacts.",
    )
    persistent_community_count: int | None = None
    month_count: int


class OverviewResponse(StrictModel):
    run_id: str
    platform: str | None = None
    content_type: str | None = None
    date_start: str | None = None
    date_end: str | None = None
    # Backward-compatible latest-period fields used by existing routes.
    total_users: int | None = None
    total_messages: int | None = None
    total_interactions: int | None = None
    if_users: int | None = None
    wif_users: int | None = None
    if_messages: int | None = None
    wif_messages: int | None = None
    if_community_count: int | None = None
    wif_community_count: int | None = None
    matched_community_count: int | None = None
    matched_percentage: float | None = None
    persistent_community_count: int | None = None
    available_periods: list[str]
    periods: list[OverviewPeriod]
    run_summary: OverviewRunSummary
    top_themes: list[TopTheme]
    model_metadata: dict[str, Any]
    config_metadata: dict[str, Any]
