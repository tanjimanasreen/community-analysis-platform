from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from copy import deepcopy
from functools import lru_cache
from typing import Any

from src.api.errors import ArtifactNotFoundError, ArtifactUnavailableError
from src.api.services.artifact_reader import ArtifactReader, normalize_value
from src.api.services.evolution_service import EvolutionService
from src.api.services.periods import (
    default_year,
    discover_periods,
    period_bounds,
    record_period,
    select_period_record,
)
from src.api.services.topic_service import TopicService
from src.artifacts.models import ArtifactRecord


class OverviewService:
    def __init__(
        self,
        reader: ArtifactReader,
        topics: TopicService,
        evolution: EvolutionService,
    ) -> None:
        self.reader = reader
        self.topics = topics
        self.evolution = evolution

    def overview(self, run_id: str) -> dict[str, Any]:
        manifest = self.reader.catalog.get_manifest(run_id)
        fingerprint = str(
            manifest.pipeline.get("completed_at") or manifest.status.value
        )
        return deepcopy(self._overview_cached(run_id, fingerprint))

    @lru_cache(maxsize=128)
    def _overview_cached(self, run_id: str, fingerprint: str) -> dict[str, Any]:
        del fingerprint
        manifest = self.reader.catalog.get_manifest(run_id)
        config = self.reader.read_safe_config(run_id)
        available_periods = discover_periods(manifest, config)
        monthly = [
            self._period_overview(run_id, period, config=config)
            for period in available_periods
        ]
        latest = monthly[-1] if monthly else {}
        persistent_count = self._persistent_count(run_id)
        interaction_values = [item.get("interaction_records") for item in monthly]
        run_interactions = (
            sum(int(value) for value in interaction_values)
            if monthly and all(value is not None for value in interaction_values)
            else self._row_count(run_id, "network_data")
        )

        inferred_start = None
        inferred_end = None
        if available_periods:
            inferred_start = period_bounds(available_periods[0])[0]
            inferred_end = period_bounds(available_periods[-1])[1]

        return {
            "run_id": run_id,
            "platform": _optional_text(manifest.dataset.get("platform")),
            "content_type": _optional_text(manifest.dataset.get("content_type")),
            "date_start": _optional_text(manifest.dataset.get("date_start"))
            or inferred_start,
            "date_end": _optional_text(manifest.dataset.get("date_end"))
            or inferred_end,
            # Legacy fields remain for other routes. They intentionally describe
            # the latest available period except for the run-level interaction total.
            "total_users": _maximum(latest.get("if_users"), latest.get("wif_users")),
            "total_messages": _maximum(
                latest.get("if_messages"), latest.get("wif_messages")
            ),
            "total_interactions": run_interactions,
            "if_users": latest.get("if_users"),
            "wif_users": latest.get("wif_users"),
            "if_messages": latest.get("if_messages"),
            "wif_messages": latest.get("wif_messages"),
            "if_community_count": latest.get("if_community_count"),
            "wif_community_count": latest.get("wif_community_count"),
            "matched_community_count": latest.get("matched_community_count"),
            "matched_percentage": latest.get("matched_percentage"),
            "persistent_community_count": persistent_count,
            "available_periods": available_periods,
            "periods": monthly,
            "run_summary": {
                "interaction_records": run_interactions,
                "persistent_community_count": persistent_count,
                "month_count": len(available_periods),
            },
            "top_themes": self._top_themes(run_id),
            "model_metadata": _model_metadata(config),
            "config_metadata": _config_metadata(
                config,
                platform=_optional_text(manifest.dataset.get("platform")),
                content_type=_optional_text(manifest.dataset.get("content_type")),
                available_periods=available_periods,
            ),
        }

    def _period_overview(
        self,
        run_id: str,
        period: str,
        *,
        config: Mapping[str, Any],
    ) -> dict[str, Any]:
        counts = self._period_counts(run_id, period, config=config)
        communities = self._period_community_counts(run_id, period, config=config)
        matched = communities.get("matched")
        denominator = max(
            communities.get("if") or 0,
            communities.get("wif") or 0,
        )
        matched_percentage = (
            round((matched or 0) * 100.0 / denominator, 2) if denominator else None
        )
        return {
            "period": period,
            "if_users": counts.get("if_users"),
            "wif_users": counts.get("wif_users"),
            "if_messages": counts.get("if_messages"),
            "wif_messages": counts.get("wif_messages"),
            "interaction_records": self._period_row_count(
                run_id, "network_data", period, config=config
            ),
            "if_community_count": communities.get("if"),
            "wif_community_count": communities.get("wif"),
            "matched_community_count": matched,
            "matched_percentage": matched_percentage,
        }

    def _period_counts(
        self,
        run_id: str,
        period: str,
        *,
        config: Mapping[str, Any],
    ) -> dict[str, int | None]:
        record = self._period_record(
            run_id, "count_user_messages", period, config=config
        )
        if record is None:
            return {}
        frame = self.reader.read_parquet_record(run_id, record)
        if frame.empty:
            return {}
        row = {key: normalize_value(value) for key, value in frame.iloc[-1].items()}
        users = row.get("user") if isinstance(row.get("user"), Mapping) else {}
        messages = (
            row.get("messages") if isinstance(row.get("messages"), Mapping) else {}
        )
        return {
            "if_users": _as_int(users.get("absolute")),
            "wif_users": _as_int(users.get("weighted")),
            "if_messages": _as_int(messages.get("absolute")),
            "wif_messages": _as_int(messages.get("weighted")),
        }

    def _period_community_counts(
        self,
        run_id: str,
        period: str,
        *,
        config: Mapping[str, Any],
    ) -> dict[str, int | None]:
        record = self._period_record(
            run_id, "communities_matched", period, config=config
        )
        if record is None:
            return {}
        frame = self.reader.read_parquet_record(run_id, record)
        if frame.empty:
            return {}
        row = {key: normalize_value(value) for key, value in frame.iloc[-1].items()}
        return {
            "matched": _as_int(row.get("total_matched")),
            "if": _as_int(row.get("total_absolute")),
            "wif": _as_int(row.get("total_weighted")),
        }

    def _period_record(
        self,
        run_id: str,
        key: str,
        period: str,
        *,
        config: Mapping[str, Any],
    ) -> ArtifactRecord | None:
        manifest = self.reader.catalog.get_manifest(run_id)
        records = _records_for_key(self.reader, run_id, key)
        if not records:
            return None
        fallback_year = default_year(config, manifest)
        matches = [
            record
            for record in records
            if record_period(record, fallback_year=fallback_year) == period
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            return select_period_record(
                records,
                period=period,
                fallback_year=fallback_year,
                run_id=run_id,
                artifact_key=key,
            )
        # Unsuffixed legacy artifacts are safe only when the run has one period.
        available_periods = discover_periods(manifest, config)
        if (
            len(records) == 1
            and records[0].key == key
            and len(available_periods) == 1
            and available_periods[0] == period
        ):
            return records[0]
        return None

    def _period_row_count(
        self,
        run_id: str,
        key: str,
        period: str,
        *,
        config: Mapping[str, Any],
    ) -> int | None:
        record = self._period_record(run_id, key, period, config=config)
        if record is None:
            return None
        return self.reader.parquet_row_count(run_id, record)

    def _row_count(self, run_id: str, key: str) -> int | None:
        records = _records_for_key(self.reader, run_id, key)
        if not records:
            return None
        return sum(self.reader.parquet_row_count(run_id, record) for record in records)

    def _top_themes(self, run_id: str) -> list[dict[str, Any]]:
        records = self.reader.find_records(run_id, key_prefix="themes_")
        if not records:
            return []
        counts: Counter[str] = Counter()
        for artifact in records:
            try:
                frame = self.reader.read_parquet_record(
                    run_id,
                    artifact,
                    columns=["general_theme_names", "general_theme_gpt"],
                )
            except (ArtifactNotFoundError, ArtifactUnavailableError):
                continue
            for row in frame.to_dict(orient="records"):
                names = row.get("general_theme_names")
                if names is None:
                    names = row.get("general_theme_gpt")
                for name in _theme_names(names):
                    counts[name] += 1
        return [{"name": name, "count": count} for name, count in counts.most_common(5)]

    def _persistent_count(self, run_id: str) -> int | None:
        try:
            return int(self.evolution.persistent_communities(run_id)["total"])
        except (ArtifactNotFoundError, ArtifactUnavailableError):
            return None


def _records_for_key(
    reader: ArtifactReader, run_id: str, key: str
) -> list[ArtifactRecord]:
    try:
        return [reader.get_record(run_id, key)]
    except (ArtifactNotFoundError, ArtifactUnavailableError):
        return sorted(
            reader.find_records(run_id, key_prefix=f"{key}_"),
            key=lambda record: record.key,
        )


def _theme_names(value: Any) -> list[str]:
    normalized = normalize_value(value)
    if normalized is None:
        return []
    if isinstance(normalized, Mapping):
        return [str(key) for key in normalized]
    if isinstance(normalized, (list, tuple, set)):
        return [str(item) for item in normalized if str(item).strip()]
    text = str(normalized).strip()
    return [text] if text else []


def _model_metadata(config: Mapping[str, Any]) -> dict[str, Any]:
    theme = config.get("theme") if isinstance(config.get("theme"), Mapping) else {}
    provider = (
        config.get("theme_provider")
        if isinstance(config.get("theme_provider"), Mapping)
        else {}
    )
    primary = _optional_text(provider.get("primary"))
    provider_name = primary
    model_name = _optional_text(theme.get("model"))
    if primary and ":" in primary:
        provider_name, configured_model = primary.split(":", 1)
        model_name = model_name or configured_model
    return {
        "theme_model": model_name,
        "similarity_model": theme.get("similarity_model")
        or theme.get("similarity_model_name"),
        "theme_provider": provider_name,
        "transition_threshold": theme.get("transition_threshold"),
    }


def _config_metadata(
    config: Mapping[str, Any],
    *,
    platform: str | None,
    content_type: str | None,
    available_periods: list[str],
) -> dict[str, Any]:
    safe: dict[str, Any] = {
        "analysis_scope": {
            "platform": platform,
            "content_type": content_type,
            "year": config.get("year"),
            "available_periods": available_periods,
        }
    }
    for key in ("graph_thresholds", "louvain", "lda"):
        value = config.get(key)
        if isinstance(value, Mapping):
            safe[key] = dict(value)
    theme = config.get("theme")
    provider = config.get("theme_provider")
    safe_theme: dict[str, Any] = {}
    if isinstance(theme, Mapping):
        for key in (
            "similarity_model",
            "similarity_model_name",
            "transition_threshold",
            "reply_transition_threshold",
            "render_visuals",
            "max_workers",
        ):
            if key in theme:
                safe_theme[key] = theme[key]
    if isinstance(provider, Mapping) and provider.get("primary") is not None:
        safe_theme["provider"] = provider.get("primary")
    if safe_theme:
        safe["theme"] = safe_theme
    return safe


def _optional_text(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _maximum(left: int | None, right: int | None) -> int | None:
    values = [value for value in (left, right) if value is not None]
    return max(values) if values else None
