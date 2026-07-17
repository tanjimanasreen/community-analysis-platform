from __future__ import annotations

from typing import Any

import pandas as pd

from src.api.errors import (
    ArtifactNotFoundError,
    ArtifactUnavailableError,
)
from src.api.services.artifact_reader import ArtifactReader, filter_by_community


class TopicService:
    def __init__(self, reader: ArtifactReader):
        self.reader = reader

    def topics(
        self,
        run_id: str,
        *,
        topic_type: str,
        community_id: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        key = (
            "matched_communities_topics"
            if topic_type == "matched"
            else "partial_matched_communities_topics"
        )
        try:
            frame = self.reader.read_csv(run_id, key)
        except ArtifactNotFoundError as exc:
            raise ArtifactUnavailableError(run_id, key) from exc
        frame = filter_by_community(frame, community_id)
        records, total = self.reader.page(frame, limit=limit, offset=offset)
        return {
            "run_id": run_id,
            "topic_type": topic_type,
            "records": records,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def themes(
        self,
        run_id: str,
        *,
        month: str | None,
        community_id: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        records = self.reader.find_records(run_id, key_prefix="themes_")
        if month is not None:
            records = [
                record for record in records if _theme_month(record.key) == month
            ]
        if not records:
            raise ArtifactUnavailableError(run_id, f"themes_{month or '*'}")

        frames = []
        for record in records:
            frame = self.reader.read_csv_record(run_id, record).copy()
            if "month" not in frame.columns:
                frame.insert(0, "month", _theme_month(record.key))
            frames.append(frame)
        combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        combined = filter_by_community(combined, community_id)
        page, total = self.reader.page(combined, limit=limit, offset=offset)

        provider_metadata = None
        try:
            provider_metadata = self.reader.read_json(run_id, "provider_run_summary")
        except (ArtifactNotFoundError, ArtifactUnavailableError):
            provider_metadata = None
        return {
            "run_id": run_id,
            "records": page,
            "total": total,
            "limit": limit,
            "offset": offset,
            "provider_metadata": provider_metadata,
        }


def _theme_month(key: str) -> str:
    return key.split("themes_", 1)[1] if key.startswith("themes_") else key
