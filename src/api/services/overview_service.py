from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from src.api.errors import ArtifactNotFoundError, ArtifactUnavailableError
from src.api.services.artifact_reader import ArtifactReader, normalize_value
from src.api.services.evolution_service import EvolutionService
from src.api.services.topic_service import TopicService


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
        counts = self._counts(run_id)
        communities = self._community_counts(run_id)
        total_interactions = self._row_count(run_id, "network_data")
        top_themes = self._top_themes(run_id)
        persistent_count = self._persistent_count(run_id)
        config = self.reader.read_safe_config(run_id)

        matched = communities.get("matched")
        denominator = max(
            communities.get("if") or 0,
            communities.get("wif") or 0,
        )
        matched_percentage = (
            round((matched or 0) * 100.0 / denominator, 2) if denominator else None
        )

        return {
            "run_id": run_id,
            "platform": _optional_text(manifest.dataset.get("platform")),
            "content_type": _optional_text(manifest.dataset.get("content_type")),
            "date_start": _optional_text(manifest.dataset.get("date_start")),
            "date_end": _optional_text(manifest.dataset.get("date_end")),
            "total_users": _maximum(counts.get("if_users"), counts.get("wif_users")),
            "total_messages": _maximum(
                counts.get("if_messages"), counts.get("wif_messages")
            ),
            "total_interactions": total_interactions,
            "if_users": counts.get("if_users"),
            "wif_users": counts.get("wif_users"),
            "if_messages": counts.get("if_messages"),
            "wif_messages": counts.get("wif_messages"),
            "if_community_count": communities.get("if"),
            "wif_community_count": communities.get("wif"),
            "matched_community_count": matched,
            "matched_percentage": matched_percentage,
            "persistent_community_count": persistent_count,
            "top_themes": top_themes,
            "model_metadata": _model_metadata(config),
            "config_metadata": _config_metadata(config),
        }

    def _counts(self, run_id: str) -> dict[str, int | None]:
        try:
            frame = self.reader.read_csv(run_id, "count_user_messages")
        except (ArtifactNotFoundError, ArtifactUnavailableError):
            return {}
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

    def _community_counts(self, run_id: str) -> dict[str, int | None]:
        try:
            frame = self.reader.read_csv(run_id, "communities_matched")
        except (ArtifactNotFoundError, ArtifactUnavailableError):
            return {}
        if frame.empty:
            return {}
        row = {key: normalize_value(value) for key, value in frame.iloc[-1].items()}
        return {
            "matched": _as_int(row.get("total_matched")),
            "if": _as_int(row.get("total_absolute")),
            "wif": _as_int(row.get("total_weighted")),
        }

    def _row_count(self, run_id: str, key: str) -> int | None:
        try:
            record = self.reader.get_record(run_id, key)
        except (ArtifactNotFoundError, ArtifactUnavailableError):
            return None
        if record.rows is not None:
            self.reader.verified_path(run_id, record)
            return record.rows
        try:
            return len(self.reader.read_csv_record(run_id, record))
        except (ArtifactNotFoundError, ArtifactUnavailableError):
            return None

    def _top_themes(self, run_id: str) -> list[dict[str, Any]]:
        try:
            response = self.topics.themes(
                run_id,
                month=None,
                community_id=None,
                limit=100000,
                offset=0,
            )
        except (ArtifactNotFoundError, ArtifactUnavailableError):
            return []
        counts: Counter[str] = Counter()
        for record in response["records"]:
            names = record.get("general_theme_names")
            if names is None:
                names = record.get("general_theme_gpt")
            for name in _theme_names(names):
                counts[name] += 1
        return [{"name": name, "count": count} for name, count in counts.most_common(5)]

    def _persistent_count(self, run_id: str) -> int | None:
        try:
            return int(self.evolution.persistent_communities(run_id)["total"])
        except (ArtifactNotFoundError, ArtifactUnavailableError):
            return None


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
    return {
        "theme_model": theme.get("model"),
        "similarity_model": theme.get("similarity_model")
        or theme.get("similarity_model_name"),
        "theme_provider": provider.get("primary"),
    }


def _config_metadata(config: Mapping[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key in ("graph_thresholds", "louvain", "lda"):
        value = config.get(key)
        if isinstance(value, Mapping):
            safe[key] = dict(value)
    return safe


def _optional_text(value: Any) -> str | None:
    return None if value in {None, ""} else str(value)


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _maximum(left: int | None, right: int | None) -> int | None:
    values = [value for value in (left, right) if value is not None]
    return max(values) if values else None
