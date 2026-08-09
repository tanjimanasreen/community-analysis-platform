from __future__ import annotations

from typing import Any

import pandas as pd

from src.api.errors import (
    ArtifactNotFoundError,
    ArtifactUnavailableError,
)
from src.api.services.artifact_reader import ArtifactReader, filter_by_community
from src.api.services.periods import default_year, select_period_record
from src.api.services.theme_trend_service import exact_theme_names


class TopicService:
    def __init__(self, reader: ArtifactReader):
        self.reader = reader

    def topics(
        self,
        run_id: str,
        *,
        topic_type: str,
        community_id: str | None,
        period: str | None = None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        key = (
            "matched_communities_topics"
            if topic_type == "matched"
            else "partial_matched_communities_topics"
        )
        artifacts = sorted(
            self.reader.find_records(run_id, key_prefix=key),
            key=lambda record: record.key,
        )
        if not artifacts:
            raise ArtifactUnavailableError(run_id, key)
        if period is not None:
            manifest = self.reader.catalog.get_manifest(run_id)
            config = self.reader.read_safe_config(run_id)
            artifacts = [
                select_period_record(
                    artifacts,
                    period=period,
                    fallback_year=default_year(config, manifest),
                    run_id=run_id,
                    artifact_key=key,
                )
            ]

        if community_id is None:
            frame, total = self.reader.read_parquet_records_page(
                run_id,
                artifacts,
                limit=limit,
                offset=offset,
            )
            page, _ = self.reader.page(frame, limit=limit, offset=0)
        else:
            # Community filtering may span both absolute and weighted columns,
            # so retain the compatibility path for this small targeted query.
            frames = [
                self.reader.read_parquet_record(run_id, artifact)
                for artifact in artifacts
            ]
            frame = pd.concat(frames, ignore_index=True)
            frame = filter_by_community(frame, community_id)
            page, total = self.reader.page(frame, limit=limit, offset=offset)

        return {
            "run_id": run_id,
            "topic_type": topic_type,
            "records": page,
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
        period: str | None = None,
        exact_theme: str | None = None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        artifacts = sorted(
            self.reader.find_records(run_id, key_prefix="themes_"),
            key=lambda record: record.key,
        )
        if not artifacts:
            raise ArtifactUnavailableError(run_id, "themes_*")
        if period is not None:
            manifest = self.reader.catalog.get_manifest(run_id)
            config = self.reader.read_safe_config(run_id)
            artifacts = [
                select_period_record(
                    artifacts,
                    period=period,
                    fallback_year=default_year(config, manifest),
                    run_id=run_id,
                    artifact_key="themes",
                )
            ]
        elif month is not None:
            artifacts = [
                artifact
                for artifact in artifacts
                if _theme_month(artifact.key) == month
            ]
        if not artifacts:
            raise ArtifactUnavailableError(run_id, f"themes_{period or month or '*'}")

        if community_id is None and exact_theme is None:
            frame, total = self._theme_page(
                run_id,
                artifacts,
                limit=limit,
                offset=offset,
            )
            page, _ = self.reader.page(frame, limit=limit, offset=0)
        else:
            frames = []
            for artifact in artifacts:
                frame = self.reader.read_parquet_record(run_id, artifact).copy()
                if "month" not in frame.columns:
                    frame.insert(0, "month", _theme_month(artifact.key))
                frames.append(frame)
            combined = (
                pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            )
            combined = filter_by_community(combined, community_id)
            combined = _filter_by_exact_theme(combined, exact_theme)
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

    def _theme_page(
        self,
        run_id: str,
        artifacts,
        *,
        limit: int,
        offset: int,
    ) -> tuple[pd.DataFrame, int]:
        total = sum(self.reader.parquet_row_count(run_id, item) for item in artifacts)
        if offset >= total or limit <= 0:
            return pd.DataFrame(), total

        remaining_offset = offset
        remaining_limit = limit
        frames: list[pd.DataFrame] = []
        for artifact in artifacts:
            rows = self.reader.parquet_row_count(run_id, artifact)
            if remaining_offset >= rows:
                remaining_offset -= rows
                continue
            frame = self.reader.read_parquet_record_slice(
                run_id,
                artifact,
                offset=remaining_offset,
                limit=remaining_limit,
            ).copy()
            if "month" not in frame.columns:
                frame.insert(0, "month", _theme_month(artifact.key))
            frames.append(frame)
            remaining_limit -= len(frame)
            remaining_offset = 0
            if remaining_limit <= 0:
                break
        if not frames:
            return pd.DataFrame(), total
        return pd.concat(frames, ignore_index=True), total


def _theme_month(key: str) -> str:
    return key.split("themes_", 1)[1] if key.startswith("themes_") else key


def _filter_by_exact_theme(
    frame: pd.DataFrame, exact_theme: str | None
) -> pd.DataFrame:
    if exact_theme is None:
        return frame
    wanted = " ".join(exact_theme.strip().split())
    if not wanted or frame.empty:
        return frame.iloc[0:0]
    mask = frame.apply(
        lambda row: wanted in exact_theme_names(row.to_dict()),
        axis=1,
    )
    return frame.loc[mask]
