from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TopTheme(StrictModel):
    name: str
    count: int


class OverviewResponse(StrictModel):
    run_id: str
    platform: str | None = None
    content_type: str | None = None
    date_start: str | None = None
    date_end: str | None = None
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
    top_themes: list[TopTheme]
    model_metadata: dict[str, Any]
    config_metadata: dict[str, Any]
