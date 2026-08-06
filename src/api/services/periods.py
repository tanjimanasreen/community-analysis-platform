from __future__ import annotations

import calendar
import re
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from src.api.errors import InvalidFilterError
from src.artifacts.models import ArtifactRecord, RunManifest

_MONTH_NAMES = {
    name.lower(): index for index, name in enumerate(calendar.month_name) if name
}
_MONTH_NAMES.update(
    {name.lower(): index for index, name in enumerate(calendar.month_abbr) if name}
)
_PERIOD_RE = re.compile(r"^(?P<year>\d{4})-(?P<month>0[1-9]|1[0-2])$")
_YEAR_MONTH_PATH_RE = re.compile(
    r"(?<!\d)(?P<month>0[1-9]|1[0-2])(?P<year>\d{4})(?!\d)"
)
_YEAR_PATH_RE = re.compile(r"(?<!\d)(?P<year>20\d{2}|19\d{2})(?!\d)")


def validate_period(period: str, *, run_id: str | None = None) -> tuple[int, int]:
    match = _PERIOD_RE.fullmatch(str(period).strip())
    if match is None:
        raise InvalidFilterError(
            "The period must use YYYY-MM format.",
            run_id=run_id,
        )
    return int(match.group("year")), int(match.group("month"))


def period_bounds(period: str) -> tuple[str, str]:
    year, month = validate_period(period)
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1).isoformat(), date(year, month, last_day).isoformat()


def default_year(config: Mapping[str, Any], manifest: RunManifest) -> int | None:
    candidates: list[Any] = [config.get("year")]
    dataset = manifest.dataset
    candidates.extend((dataset.get("date_start"), dataset.get("date_end")))
    for item in config.get("longitudinal_datasets", []) or []:
        if isinstance(item, Mapping):
            candidates.append(item.get("year"))
            candidates.append(item.get("input_path"))
    for candidate in candidates:
        year = _year_from_value(candidate)
        if year is not None:
            return year
    for record in manifest.artifacts:
        year = _year_from_value(record.path)
        if year is not None:
            return year
    return None


def discover_periods(
    manifest: RunManifest,
    config: Mapping[str, Any],
    *,
    prefixes: Sequence[str] = (
        "count_user_messages",
        "communities_matched",
        "network_data",
        "community_graph_sample_absolute",
        "community_graph_sample_weighted",
    ),
) -> list[str]:
    fallback_year = default_year(config, manifest)
    periods: set[str] = set()

    for item in config.get("longitudinal_datasets", []) or []:
        if not isinstance(item, Mapping):
            continue
        month = _month_from_value(item.get("month"))
        year = (
            _year_from_value(item.get("year") or item.get("input_path"))
            or fallback_year
        )
        if month is not None and year is not None:
            periods.add(f"{year:04d}-{month:02d}")

    config_month = _month_from_value(config.get("month"))
    if config_month is not None and fallback_year is not None:
        periods.add(f"{fallback_year:04d}-{config_month:02d}")

    for record in manifest.artifacts:
        if not any(
            record.key == prefix or record.key.startswith(f"{prefix}_")
            for prefix in prefixes
        ):
            continue
        period = record_period(record, fallback_year=fallback_year)
        if period is not None:
            periods.add(period)

    return sorted(periods)


def record_period(record: ArtifactRecord, *, fallback_year: int | None) -> str | None:
    path_match = _YEAR_MONTH_PATH_RE.search(record.path)
    if path_match is not None:
        year = int(path_match.group("year"))
        month = int(path_match.group("month"))
        return f"{year:04d}-{month:02d}"

    year = _year_from_value(record.path) or fallback_year
    month = _month_from_artifact_key(record.key)
    if month is None:
        month = _month_from_path(record.path)
    if month is None or year is None:
        return None
    return f"{year:04d}-{month:02d}"


def select_period_record(
    records: Sequence[ArtifactRecord],
    *,
    period: str,
    fallback_year: int | None,
    run_id: str,
    artifact_key: str,
) -> ArtifactRecord:
    validate_period(period, run_id=run_id)
    matches = [
        record
        for record in records
        if record_period(record, fallback_year=fallback_year) == period
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise InvalidFilterError(
            f"Multiple artifacts map to period {period} for {artifact_key}.",
            run_id=run_id,
        )
    available = sorted(
        {
            candidate
            for record in records
            if (candidate := record_period(record, fallback_year=fallback_year))
            is not None
        }
    )
    availability = f" Available periods: {', '.join(available)}." if available else ""
    raise InvalidFilterError(
        f"Period {period} is not available for {artifact_key}.{availability}",
        run_id=run_id,
    )


def _month_from_artifact_key(key: str) -> int | None:
    for token in reversed(re.split(r"[_\-.]", key)):
        month = _month_from_value(token)
        if month is not None:
            return month
    return None


def _month_from_path(path: str) -> int | None:
    stem = path.rsplit("/", 1)[-1].split(".", 1)[0]
    for token in re.split(r"[_\-.]", stem):
        month = _month_from_value(token)
        if month is not None:
            return month
    return None


def _month_from_value(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    if text.isdigit():
        month = int(text)
        return month if 1 <= month <= 12 else None
    return _MONTH_NAMES.get(text)


def _year_from_value(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    match = _YEAR_PATH_RE.search(text)
    if match is None:
        return None
    return int(match.group("year"))
