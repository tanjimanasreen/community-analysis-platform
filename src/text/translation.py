from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import time
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence

import pandas as pd

TRANSLATION_CONTRACT_VERSION = "v1"
_SUPPORTED_PROVIDERS = {"azure", "aws"}
_LOGGER = logging.getLogger(__name__)


class TranslationError(RuntimeError):
    """Raised when configured language detection/translation cannot complete."""


@dataclass(frozen=True)
class TranslationOptions:
    enabled: bool = False
    provider: str = "azure"
    target_language: str = "en"
    contract_version: str = TRANSLATION_CONTRACT_VERSION
    cache_path: str = ".cache/translation_cache.sqlite3"
    timeout_seconds: float = 30.0
    # Pause before the very first API chunk to let Azure's sliding-window rate limiter
    # reset after rapid preceding work (e.g. network/community stage cache hits).
    # Default 2.0 s is safe for both F0 (free) and S1 (standard) tiers.
    initial_delay_seconds: float = 2.0
    # Inter-chunk delay injected between successive HTTP calls to avoid burst-rate 429s.
    # Default 0.5 s is safe for both F0 and S1 tiers; set to 0 to disable.
    inter_chunk_delay_seconds: float = 0.5
    # Maximum number of per-request retry attempts on transient errors (including 429).
    # Each retry waits `Retry-After` seconds (from the response header) or falls back
    # to exponential backoff (2^attempt seconds, capped at 60 s).
    # 8 retries cover up to ~3 minutes of persistent throttling (1+2+4+8+16+32+60+60).
    max_retries: int = 8

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any] | None) -> "TranslationOptions":
        data = dict(raw or {})
        return cls(
            enabled=bool(data.get("enabled", False)),
            provider=str(data.get("provider", "azure")).strip().lower(),
            target_language=str(data.get("target_language", "en")).strip().lower(),
            contract_version=str(
                data.get("contract_version", TRANSLATION_CONTRACT_VERSION)
            ).strip(),
            cache_path=str(
                data.get("cache_path", ".cache/translation_cache.sqlite3")
            ).strip(),
            timeout_seconds=float(data.get("timeout_seconds", 30.0)),
            initial_delay_seconds=float(data.get("initial_delay_seconds", 2.0)),
            inter_chunk_delay_seconds=float(data.get("inter_chunk_delay_seconds", 0.5)),
            max_retries=int(data.get("max_retries", 8)),
        )


@dataclass(frozen=True)
class LanguageDetectionRecord:
    source_text: str
    source_hash: str
    detected_language: str
    language_confidence: float | None
    translation_supported: bool
    provider: str
    contract_version: str
    created_at: str
    cache_hit: bool = False


@dataclass(frozen=True)
class TranslationRecord:
    source_text: str
    source_hash: str
    detected_language: str
    language_confidence: float | None
    translated_text: str
    translation_applied: bool
    provider: str
    target_language: str
    contract_version: str
    created_at: str
    cache_hit: bool = False
    status: str = "success"


@dataclass(frozen=True)
class TranslationPreparationResult:
    absolute_community_messages: pd.DataFrame
    weighted_community_messages: pd.DataFrame
    provenance_path: Path
    unique_message_count: int
    cache_hit_count: int
    translated_count: int


@dataclass(frozen=True)
class TranslationWorkloadPlan:
    """Provider-free estimate of translation work after persistent-cache reuse."""

    provider: str
    target_language: str
    contract_version: str
    total_message_occurrences: int
    unique_message_count: int
    cache_hit_count: int
    cache_miss_count: int
    cache_miss_character_count: int
    language_detection_request_count: int
    translation_request_min_count: int
    translation_request_max_count: int
    potential_item_limit_count: int


@dataclass(frozen=True)
class TranslationDetectionIssue:
    """Message-level diagnostic emitted by detection-only planning."""

    source_text: str
    source_hash: str
    detected_language: str
    language_confidence: float | None
    character_count: int
    reason: str
    fallback_strategy: str
    blocks_full_run: bool


@dataclass(frozen=True)
class TranslationDetectionPlan:
    """Exact post-detection translation workload without translation calls."""

    provider: str
    target_language: str
    contract_version: str
    total_message_occurrences: int
    unique_message_count: int
    translation_cache_hit_count: int
    detection_cache_hit_count: int
    newly_detected_count: int
    language_detection_request_count: int
    target_language_count: int
    translation_candidate_count: int
    translation_candidate_character_count: int
    exact_translation_request_count: int
    unsupported_translation_count: int
    potential_item_limit_count: int
    language_counts: Mapping[str, int]
    azure_auto_detect_fallback_count: int = 0
    azure_auto_detect_fallback_request_count: int = 0
    issues: tuple[TranslationDetectionIssue, ...] = ()


class TranslationProvider(Protocol):
    name: str

    def detect_many(self, texts: Sequence[str]) -> list[LanguageDetectionRecord]: ...

    def translate_detected_many(
        self,
        detections: Sequence[LanguageDetectionRecord],
        *,
        target_language: str,
    ) -> list[TranslationRecord]: ...

    def translate_many(
        self, texts: Sequence[str], *, target_language: str
    ) -> list[TranslationRecord]: ...


def source_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def translation_cache_key(
    text: str,
    *,
    provider: str,
    target_language: str,
    contract_version: str,
) -> str:
    payload = {
        "source_hash": source_text_hash(text),
        "provider": provider,
        "target_language": target_language,
        "contract_version": contract_version,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical).hexdigest()


def language_detection_cache_key(
    text: str,
    *,
    provider: str,
    contract_version: str,
) -> str:
    payload = {
        "source_hash": source_text_hash(text),
        "provider": provider,
        "contract_version": contract_version,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical).hexdigest()


def translation_provenance_path(
    output_dir: str | Path,
    *,
    data_type: str,
    content_type: str,
    year: str,
    month: str,
) -> Path:
    return (
        Path(output_dir)
        / data_type
        / "_intermediate"
        / "translations"
        / content_type
        / str(year)
        / f"{month}.parquet"
    )


class SQLiteTranslationCache:
    """Persistent per-message translation cache.

    Cache identity intentionally includes provider and translation-contract version,
    so changing Azure↔AWS or changing the translation contract never silently reuses
    a result produced under a different analytical transformation.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS translations (
                    cache_key TEXT PRIMARY KEY,
                    source_hash TEXT NOT NULL,
                    source_text TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    target_language TEXT NOT NULL,
                    contract_version TEXT NOT NULL,
                    detected_language TEXT NOT NULL,
                    language_confidence REAL,
                    translated_text TEXT NOT NULL,
                    translation_applied INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_translation_source_hash "
                "ON translations(source_hash)"
            )
            connection.execute("""
                CREATE TABLE IF NOT EXISTS language_detections (
                    cache_key TEXT PRIMARY KEY,
                    source_hash TEXT NOT NULL,
                    source_text TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    contract_version TEXT NOT NULL,
                    detected_language TEXT NOT NULL,
                    language_confidence REAL,
                    translation_supported INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_language_detection_source_hash "
                "ON language_detections(source_hash)"
            )

    def get_many(
        self,
        texts: Sequence[str],
        *,
        provider: str,
        target_language: str,
        contract_version: str,
    ) -> dict[str, TranslationRecord]:
        if not texts:
            return {}
        keys = {
            translation_cache_key(
                text,
                provider=provider,
                target_language=target_language,
                contract_version=contract_version,
            ): text
            for text in texts
        }
        found: dict[str, TranslationRecord] = {}
        key_list = list(keys)
        with self._connect() as connection:
            for offset in range(0, len(key_list), 500):
                chunk = key_list[offset : offset + 500]
                placeholders = ",".join("?" for _ in chunk)
                rows = connection.execute(
                    f"SELECT * FROM translations WHERE cache_key IN ({placeholders})",
                    chunk,
                ).fetchall()
                for row in rows:
                    expected_text = keys.get(str(row["cache_key"]))
                    if (
                        expected_text is None
                        or str(row["source_text"]) != expected_text
                    ):
                        # Treat inconsistent/corrupt cache records as misses.
                        continue
                    found[expected_text] = TranslationRecord(
                        source_text=expected_text,
                        source_hash=str(row["source_hash"]),
                        detected_language=str(row["detected_language"]),
                        language_confidence=(
                            None
                            if row["language_confidence"] is None
                            else float(row["language_confidence"])
                        ),
                        translated_text=str(row["translated_text"]),
                        translation_applied=bool(row["translation_applied"]),
                        provider=str(row["provider"]),
                        target_language=str(row["target_language"]),
                        contract_version=str(row["contract_version"]),
                        created_at=str(row["created_at"]),
                        cache_hit=True,
                        status=str(row["status"]),
                    )
        return found

    def get_detections(
        self,
        texts: Sequence[str],
        *,
        provider: str,
        contract_version: str,
    ) -> dict[str, LanguageDetectionRecord]:
        if not texts:
            return {}
        keys = {
            language_detection_cache_key(
                text, provider=provider, contract_version=contract_version
            ): text
            for text in texts
        }
        found: dict[str, LanguageDetectionRecord] = {}
        key_list = list(keys)
        with self._connect() as connection:
            for offset in range(0, len(key_list), 500):
                chunk = key_list[offset : offset + 500]
                placeholders = ",".join("?" for _ in chunk)
                rows = connection.execute(
                    f"SELECT * FROM language_detections WHERE cache_key IN ({placeholders})",
                    chunk,
                ).fetchall()
                for row in rows:
                    expected_text = keys.get(str(row["cache_key"]))
                    if (
                        expected_text is None
                        or str(row["source_text"]) != expected_text
                    ):
                        continue
                    found[expected_text] = LanguageDetectionRecord(
                        source_text=expected_text,
                        source_hash=str(row["source_hash"]),
                        detected_language=str(row["detected_language"]),
                        language_confidence=(
                            None
                            if row["language_confidence"] is None
                            else float(row["language_confidence"])
                        ),
                        translation_supported=bool(row["translation_supported"]),
                        provider=str(row["provider"]),
                        contract_version=str(row["contract_version"]),
                        created_at=str(row["created_at"]),
                        cache_hit=True,
                    )
        return found

    def put_detections(self, records: Sequence[LanguageDetectionRecord]) -> None:
        if not records:
            return
        rows = []
        for record in records:
            key = language_detection_cache_key(
                record.source_text,
                provider=record.provider,
                contract_version=record.contract_version,
            )
            rows.append(
                (
                    key,
                    record.source_hash,
                    record.source_text,
                    record.provider,
                    record.contract_version,
                    record.detected_language,
                    record.language_confidence,
                    int(record.translation_supported),
                    record.created_at,
                )
            )
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO language_detections (
                    cache_key, source_hash, source_text, provider, contract_version,
                    detected_language, language_confidence, translation_supported, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    def put_many(self, records: Sequence[TranslationRecord]) -> None:
        if not records:
            return
        rows = []
        for record in records:
            if record.status not in {"success", "success_auto_detect_fallback"}:
                continue
            key = translation_cache_key(
                record.source_text,
                provider=record.provider,
                target_language=record.target_language,
                contract_version=record.contract_version,
            )
            rows.append(
                (
                    key,
                    record.source_hash,
                    record.source_text,
                    record.provider,
                    record.target_language,
                    record.contract_version,
                    record.detected_language,
                    record.language_confidence,
                    record.translated_text,
                    int(record.translation_applied),
                    record.created_at,
                    record.status,
                )
            )
        if not rows:
            return
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO translations (
                    cache_key, source_hash, source_text, provider, target_language,
                    contract_version, detected_language, language_confidence,
                    translated_text, translation_applied, created_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )


def _chunk_texts(
    texts: Sequence[str],
    *,
    max_items: int,
    max_total_chars: int,
    max_item_chars: int,
) -> Iterable[list[str]]:
    chunk: list[str] = []
    char_count = 0
    for text in texts:
        if len(text) > max_item_chars:
            raise TranslationError(
                "translation input exceeds provider item limit: "
                f"source_hash={source_text_hash(text)[:12]} characters={len(text)} "
                f"limit={max_item_chars}"
            )
        if chunk and (
            len(chunk) >= max_items or char_count + len(text) > max_total_chars
        ):
            yield chunk
            chunk = []
            char_count = 0
        chunk.append(text)
        char_count += len(text)
    if chunk:
        yield chunk


class AzureTranslationProvider:
    name = "azure"

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str = "https://api.cognitive.microsofttranslator.com",
        region: str | None = None,
        timeout_seconds: float = 30.0,
        inter_chunk_delay_seconds: float = 0.5,
        initial_delay_seconds: float = 2.0,
        max_retries: int = 8,
        session: Any | None = None,
    ):
        if not api_key.strip():
            raise TranslationError("AZURE_TRANSLATOR_KEY is required")
        self.api_key = api_key.strip()
        self.endpoint = endpoint.rstrip("/")
        self.region = region.strip() if region else None
        self.timeout_seconds = timeout_seconds
        # Operational rate-limit parameters (do not participate in cache identity).
        self.inter_chunk_delay_seconds = inter_chunk_delay_seconds
        # Pause before the very first API chunk so Azure's sliding window has time
        # to reset after rapid preceding work (network stage cache hits, etc.).
        self.initial_delay_seconds = initial_delay_seconds
        self.max_retries = max_retries
        if session is None:
            import requests

            session = requests.Session()
        self.session = session

    def _post(self, route: str, *, params: Mapping[str, str], texts: Sequence[str]):
        """POST to Azure Translator with Retry-After-aware exponential backoff on 429.

        Azure enforces sliding-window rate limits on its Translator service. Rapid
        sequential calls — even within a single batch job — can trigger 429 on both
        the F0 (free) and S1 (standard) tiers.  This method retries up to
        ``self.max_retries`` times, honouring the ``Retry-After`` header when present
        and falling back to exponential backoff (2^attempt seconds, capped at 60 s).
        """
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": "application/json",
        }
        if self.region:
            headers["Ocp-Apim-Subscription-Region"] = self.region

        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    f"{self.endpoint}{route}",
                    params=dict(params),
                    headers=headers,
                    json=[{"Text": text} for text in texts],
                    timeout=self.timeout_seconds,
                )
                if response.status_code == 429:
                    # Honour Retry-After if Azure provides it; fall back to backoff.
                    retry_after_raw = response.headers.get("Retry-After")
                    if retry_after_raw is not None:
                        try:
                            wait_seconds = max(1.0, float(retry_after_raw))
                        except ValueError:
                            wait_seconds = min(60.0, 2.0**attempt)
                    else:
                        wait_seconds = min(60.0, 2.0**attempt)
                    _LOGGER.warning(
                        "azure_translator_429 route=%s attempt=%d/%d "
                        "retry_after_seconds=%.1f",
                        route,
                        attempt + 1,
                        self.max_retries,
                        wait_seconds,
                    )
                    time.sleep(wait_seconds)
                    # Track as a descriptive error so exhaustion message is meaningful.
                    last_exc = RuntimeError(
                        f"429 Too Many Requests (Retry-After={wait_seconds:.0f}s)"
                    )
                    continue
                response.raise_for_status()
                payload = response.json()
                break
            except Exception as exc:
                last_exc = exc
                if attempt < self.max_retries - 1:
                    backoff = min(60.0, 2.0**attempt)
                    _LOGGER.warning(
                        "azure_translator_error route=%s attempt=%d/%d "
                        "error=%r retry_in=%.1fs",
                        route,
                        attempt + 1,
                        self.max_retries,
                        exc,
                        backoff,
                    )
                    time.sleep(backoff)
                continue
        else:
            # All attempts exhausted.
            raise TranslationError(
                f"Azure Translator request failed for {route} after "
                f"{self.max_retries} attempt(s): "
                f"{type(last_exc).__name__}: {last_exc}"
            ) from last_exc

        if not isinstance(payload, list) or len(payload) != len(texts):
            raise TranslationError(
                f"Azure Translator returned an invalid {route} response shape"
            )
        return payload

    def _detect(
        self, texts: Sequence[str]
    ) -> dict[str, tuple[str, float | None, bool]]:
        """Detect languages in batches with an inter-chunk delay to avoid burst 429s.

        ``initial_delay_seconds`` is applied before the very first chunk to let
        Azure's sliding-window rate limiter reset after any preceding rapid work
        (e.g. network/community stage cache hits that complete in quick succession).
        Subsequent chunks are separated by ``inter_chunk_delay_seconds``.
        """
        detected: dict[str, tuple[str, float | None, bool]] = {}
        chunks = list(
            _chunk_texts(
                texts, max_items=100, max_total_chars=25_000, max_item_chars=10_000
            )
        )
        for chunk_index, chunk in enumerate(chunks):
            if chunk_index == 0 and self.initial_delay_seconds > 0:
                _LOGGER.debug(
                    "azure_translator_initial_delay seconds=%.1f route=/detect",
                    self.initial_delay_seconds,
                )
                time.sleep(self.initial_delay_seconds)
            elif chunk_index > 0 and self.inter_chunk_delay_seconds > 0:
                time.sleep(self.inter_chunk_delay_seconds)
            payload = self._post("/detect", params={"api-version": "3.0"}, texts=chunk)
            for text, item in zip(chunk, payload):
                if not isinstance(item, Mapping) or not item.get("language"):
                    raise TranslationError(
                        "Azure Translator detection response is missing language"
                    )
                score = item.get("score")
                detected[text] = (
                    str(item["language"]).lower(),
                    None if score is None else float(score),
                    bool(item.get("isTranslationSupported", True)),
                )
        return detected

    def _translate_group(
        self, texts: Sequence[str], *, source_language: str, target_language: str
    ) -> dict[str, str]:
        """Translate a language group in batches with inter-chunk delay to avoid burst 429s."""
        translated: dict[str, str] = {}
        chunks = list(
            _chunk_texts(
                texts, max_items=25, max_total_chars=5_000, max_item_chars=5_000
            )
        )
        for chunk_index, chunk in enumerate(chunks):
            if chunk_index > 0 and self.inter_chunk_delay_seconds > 0:
                time.sleep(self.inter_chunk_delay_seconds)
            payload = self._post(
                "/translate",
                params={
                    "api-version": "3.0",
                    "from": source_language,
                    "to": target_language,
                },
                texts=chunk,
            )
            for text, item in zip(chunk, payload):
                translations = (
                    item.get("translations") if isinstance(item, Mapping) else None
                )
                if not isinstance(translations, list) or not translations:
                    raise TranslationError(
                        "Azure Translator response is missing translated text"
                    )
                translated_text = translations[0].get("text")
                if not isinstance(translated_text, str):
                    raise TranslationError(
                        "Azure Translator response contains a non-string translation"
                    )
                translated[text] = translated_text
        return translated

    def _translate_auto_detect_group(
        self, texts: Sequence[str], *, target_language: str
    ) -> dict[str, tuple[str, str, float | None]]:
        """Translate texts with Azure source-language auto-detection enabled.

        This path is reserved for messages whose prior ``/detect`` result reports
        ``isTranslationSupported=false``. Omitting ``from`` lets ``/translate``
        perform its own source-language detection and use a translatable source
        mapping when Azure can resolve one.
        """
        translated: dict[str, tuple[str, str, float | None]] = {}
        chunks = list(
            _chunk_texts(
                texts,
                max_items=25,
                max_total_chars=5_000,
                max_item_chars=5_000,
            )
        )
        for chunk_index, chunk in enumerate(chunks):
            if chunk_index > 0 and self.inter_chunk_delay_seconds > 0:
                time.sleep(self.inter_chunk_delay_seconds)
            payload = self._post(
                "/translate",
                params={"api-version": "3.0", "to": target_language},
                texts=chunk,
            )
            for text, item in zip(chunk, payload):
                translations = (
                    item.get("translations") if isinstance(item, Mapping) else None
                )
                if not isinstance(translations, list) or not translations:
                    raise TranslationError(
                        "Azure Translator auto-detect response is missing translated text"
                    )
                translated_text = translations[0].get("text")
                if not isinstance(translated_text, str):
                    raise TranslationError(
                        "Azure Translator auto-detect response contains a non-string translation"
                    )
                detected = item.get("detectedLanguage")
                if not isinstance(detected, Mapping) or not detected.get("language"):
                    raise TranslationError(
                        "Azure Translator auto-detect response is missing detectedLanguage"
                    )
                score = detected.get("score")
                translated[text] = (
                    translated_text,
                    str(detected["language"]).lower(),
                    None if score is None else float(score),
                )
        return translated

    def detect_many(self, texts: Sequence[str]) -> list[LanguageDetectionRecord]:
        if not texts:
            return []
        detected = self._detect(texts)
        created_at = datetime.now(timezone.utc).isoformat()
        return [
            LanguageDetectionRecord(
                source_text=text,
                source_hash=source_text_hash(text),
                detected_language=detected[text][0],
                language_confidence=detected[text][1],
                translation_supported=detected[text][2],
                provider=self.name,
                contract_version=TRANSLATION_CONTRACT_VERSION,
                created_at=created_at,
            )
            for text in texts
        ]

    def translate_detected_many(
        self,
        detections: Sequence[LanguageDetectionRecord],
        *,
        target_language: str,
    ) -> list[TranslationRecord]:
        if not detections:
            return []

        non_target = [
            record
            for record in detections
            if record.detected_language != target_language
        ]
        oversized = [record for record in non_target if len(record.source_text) > 5_000]
        if oversized:
            record = oversized[0]
            raise TranslationError(
                "Azure Translator input exceeds 5,000-character request limit: "
                f"source_hash={record.source_hash[:12]} characters={len(record.source_text)}"
            )

        groups: dict[str, list[str]] = defaultdict(list)
        auto_detect_fallback: list[str] = []
        translated: dict[str, str] = {}
        fallback_texts: set[str] = set()
        detection_by_text = {record.source_text: record for record in detections}

        for record in detections:
            if record.detected_language == target_language:
                translated[record.source_text] = record.source_text
            elif record.translation_supported:
                groups[record.detected_language].append(record.source_text)
            else:
                auto_detect_fallback.append(record.source_text)
                fallback_texts.add(record.source_text)

        for language, group in groups.items():
            translated.update(
                self._translate_group(
                    group,
                    source_language=language,
                    target_language=target_language,
                )
            )

        if auto_detect_fallback:
            fallback_results = self._translate_auto_detect_group(
                auto_detect_fallback, target_language=target_language
            )
            for text, (
                translated_text,
                resolved_language,
                resolved_score,
            ) in fallback_results.items():
                translated[text] = translated_text
                original = detection_by_text[text]
                _LOGGER.info(
                    "azure_translation_auto_detect_fallback source_hash=%s "
                    "initial_language=%s initial_confidence=%s resolved_language=%s "
                    "resolved_confidence=%s",
                    original.source_hash[:12],
                    original.detected_language,
                    original.language_confidence,
                    resolved_language,
                    resolved_score,
                )

        created_at = datetime.now(timezone.utc).isoformat()
        records: list[TranslationRecord] = []
        for text in [record.source_text for record in detections]:
            detection = detection_by_text[text]
            translated_text = translated.get(text)
            if translated_text is None:
                raise TranslationError(
                    "Azure Translator did not return a translation for "
                    f"source_hash={source_text_hash(text)[:12]}"
                )
            records.append(
                TranslationRecord(
                    source_text=text,
                    source_hash=source_text_hash(text),
                    detected_language=detection.detected_language,
                    language_confidence=detection.language_confidence,
                    translated_text=translated_text,
                    translation_applied=detection.detected_language != target_language,
                    provider=self.name,
                    target_language=target_language,
                    contract_version=TRANSLATION_CONTRACT_VERSION,
                    created_at=created_at,
                    status=(
                        "success_auto_detect_fallback"
                        if text in fallback_texts
                        else "success"
                    ),
                )
            )
        return records

    def translate_many(
        self, texts: Sequence[str], *, target_language: str
    ) -> list[TranslationRecord]:
        detections = self.detect_many(texts)
        return self.translate_detected_many(detections, target_language=target_language)


class AwsTranslationProvider:
    name = "aws"

    def __init__(
        self,
        *,
        region_name: str | None = None,
        comprehend_client: Any | None = None,
        translate_client: Any | None = None,
    ):
        if comprehend_client is None or translate_client is None:
            try:
                import boto3
            except ModuleNotFoundError as exc:
                raise TranslationError(
                    "AWS translation requires boto3; install boto3 in the runtime environment"
                ) from exc
            comprehend_client = comprehend_client or boto3.client(
                "comprehend", region_name=region_name
            )
            translate_client = translate_client or boto3.client(
                "translate", region_name=region_name
            )
        self.comprehend_client = comprehend_client
        self.translate_client = translate_client

    def _detect(self, texts: Sequence[str]) -> dict[str, tuple[str, float | None]]:
        detected: dict[str, tuple[str, float | None]] = {}
        for offset in range(0, len(texts), 25):
            chunk = list(texts[offset : offset + 25])
            try:
                payload = self.comprehend_client.batch_detect_dominant_language(
                    TextList=chunk
                )
            except Exception as exc:
                raise TranslationError(
                    f"AWS Comprehend language detection failed: {type(exc).__name__}: {exc}"
                ) from exc
            errors = payload.get("ErrorList", [])
            if errors:
                raise TranslationError(
                    "AWS Comprehend language detection returned errors: "
                    + ", ".join(str(item) for item in errors)
                )
            by_index = {
                int(item["Index"]): item
                for item in payload.get("ResultList", [])
                if isinstance(item, Mapping) and "Index" in item
            }
            for index, text in enumerate(chunk):
                item = by_index.get(index)
                languages = item.get("Languages", []) if item else []
                if not languages:
                    raise TranslationError(
                        "AWS Comprehend did not detect a language for "
                        f"source_hash={source_text_hash(text)[:12]}"
                    )
                best = max(languages, key=lambda row: float(row.get("Score", 0.0)))
                language = str(best.get("LanguageCode", "")).lower()
                if not language:
                    raise TranslationError(
                        "AWS Comprehend returned an empty language code"
                    )
                score = best.get("Score")
                detected[text] = (
                    language,
                    None if score is None else float(score),
                )
        return detected

    def detect_many(self, texts: Sequence[str]) -> list[LanguageDetectionRecord]:
        if not texts:
            return []
        detected = self._detect(texts)
        created_at = datetime.now(timezone.utc).isoformat()
        return [
            LanguageDetectionRecord(
                source_text=text,
                source_hash=source_text_hash(text),
                detected_language=detected[text][0],
                language_confidence=detected[text][1],
                translation_supported=True,
                provider=self.name,
                contract_version=TRANSLATION_CONTRACT_VERSION,
                created_at=created_at,
            )
            for text in texts
        ]

    def translate_detected_many(
        self,
        detections: Sequence[LanguageDetectionRecord],
        *,
        target_language: str,
    ) -> list[TranslationRecord]:
        if not detections:
            return []
        created_at = datetime.now(timezone.utc).isoformat()
        records: list[TranslationRecord] = []
        for detection in detections:
            text = detection.source_text
            language = detection.detected_language
            translated_text = text
            applied = language != target_language
            if applied:
                if len(text.encode("utf-8")) > 10_000:
                    raise TranslationError(
                        "AWS Translate input exceeds 10,000-byte limit: "
                        f"source_hash={source_text_hash(text)[:12]}"
                    )
                try:
                    payload = self.translate_client.translate_text(
                        Text=text,
                        SourceLanguageCode=language,
                        TargetLanguageCode=target_language,
                    )
                except Exception as exc:
                    raise TranslationError(
                        f"AWS Translate request failed: {type(exc).__name__}: {exc}"
                    ) from exc
                translated_text = payload.get("TranslatedText")
                if not isinstance(translated_text, str):
                    raise TranslationError(
                        "AWS Translate response is missing TranslatedText"
                    )
            records.append(
                TranslationRecord(
                    source_text=text,
                    source_hash=source_text_hash(text),
                    detected_language=language,
                    language_confidence=detection.language_confidence,
                    translated_text=translated_text,
                    translation_applied=applied,
                    provider=self.name,
                    target_language=target_language,
                    contract_version=TRANSLATION_CONTRACT_VERSION,
                    created_at=created_at,
                )
            )
        return records

    def translate_many(
        self, texts: Sequence[str], *, target_language: str
    ) -> list[TranslationRecord]:
        detections = self.detect_many(texts)
        return self.translate_detected_many(detections, target_language=target_language)


def build_translation_provider(options: TranslationOptions) -> TranslationProvider:
    if options.provider == "azure":
        from src.config.settings import get_azure_translator_settings

        settings = get_azure_translator_settings()
        key = settings.key.get_secret_value() if settings.key is not None else ""
        return AzureTranslationProvider(
            api_key=key,
            endpoint=str(settings.endpoint),
            region=settings.region,
            timeout_seconds=options.timeout_seconds,
            initial_delay_seconds=options.initial_delay_seconds,
            inter_chunk_delay_seconds=options.inter_chunk_delay_seconds,
            max_retries=options.max_retries,
        )
    if options.provider == "aws":
        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or None
        return AwsTranslationProvider(region_name=region)
    raise TranslationError(f"unsupported translation provider: {options.provider!r}")


def _with_contract_version(
    records: Sequence[TranslationRecord], contract_version: str
) -> list[TranslationRecord]:
    return [replace(record, contract_version=contract_version) for record in records]


def _detections_with_contract_version(
    records: Sequence[LanguageDetectionRecord], contract_version: str
) -> list[LanguageDetectionRecord]:
    return [replace(record, contract_version=contract_version) for record in records]


def _detection_from_translation(record: TranslationRecord) -> LanguageDetectionRecord:
    return LanguageDetectionRecord(
        source_text=record.source_text,
        source_hash=record.source_hash,
        detected_language=record.detected_language,
        language_confidence=record.language_confidence,
        translation_supported=True,
        provider=record.provider,
        contract_version=record.contract_version,
        created_at=record.created_at,
        cache_hit=True,
    )


def _unique_source_texts(texts: Sequence[str]) -> list[str]:
    return sorted(
        {text for text in texts if isinstance(text, str) and text.strip()},
        key=lambda value: (source_text_hash(value), value),
    )


def _cached_translation_records(
    unique_texts: Sequence[str], *, options: TranslationOptions
) -> dict[str, TranslationRecord]:
    # A dry run against an empty cache must remain side-effect free: do not create
    # the SQLite file simply to report zero hits.
    cache_path = Path(options.cache_path).expanduser()
    if not cache_path.is_file():
        return {}
    cache = SQLiteTranslationCache(cache_path)
    return cache.get_many(
        unique_texts,
        provider=options.provider,
        target_language=options.target_language,
        contract_version=options.contract_version,
    )


def _cached_detection_records(
    unique_texts: Sequence[str], *, options: TranslationOptions
) -> dict[str, LanguageDetectionRecord]:
    cache_path = Path(options.cache_path).expanduser()
    if not cache_path.is_file():
        return {}
    cache = SQLiteTranslationCache(cache_path)
    return cache.get_detections(
        unique_texts,
        provider=options.provider,
        contract_version=options.contract_version,
    )


def detect_texts_with_cache(
    texts: Sequence[str],
    *,
    options: TranslationOptions,
    provider_factory: Callable[
        [TranslationOptions], TranslationProvider
    ] = build_translation_provider,
) -> TranslationDetectionPlan:
    """Detect languages only, persist detections, and report exact translation work."""
    if not options.enabled:
        raise TranslationError(
            "language detection requested while translation is disabled"
        )

    unique_texts = _unique_source_texts(texts)
    non_empty_occurrences = sum(
        1 for text in texts if isinstance(text, str) and text.strip()
    )
    if not unique_texts:
        return TranslationDetectionPlan(
            provider=options.provider,
            target_language=options.target_language,
            contract_version=options.contract_version,
            total_message_occurrences=0,
            unique_message_count=0,
            translation_cache_hit_count=0,
            detection_cache_hit_count=0,
            newly_detected_count=0,
            language_detection_request_count=0,
            target_language_count=0,
            translation_candidate_count=0,
            translation_candidate_character_count=0,
            exact_translation_request_count=0,
            unsupported_translation_count=0,
            potential_item_limit_count=0,
            language_counts={},
        )

    cache = SQLiteTranslationCache(options.cache_path)
    translated_cached = cache.get_many(
        unique_texts,
        provider=options.provider,
        target_language=options.target_language,
        contract_version=options.contract_version,
    )
    unresolved = [text for text in unique_texts if text not in translated_cached]
    detection_cached = cache.get_detections(
        unresolved,
        provider=options.provider,
        contract_version=options.contract_version,
    )
    detection_missing = [text for text in unresolved if text not in detection_cached]
    if options.provider == "azure":
        detection_request_count = len(
            list(
                _chunk_texts(
                    detection_missing,
                    max_items=100,
                    max_total_chars=25_000,
                    max_item_chars=10_000,
                )
            )
        )
    elif options.provider == "aws":
        detection_request_count = (len(detection_missing) + 24) // 25
    else:
        raise TranslationError(
            f"unsupported translation provider: {options.provider!r}"
        )

    generated: list[LanguageDetectionRecord] = []
    if detection_missing:
        provider = provider_factory(options)
        if provider.name != options.provider:
            raise TranslationError(
                "translation provider factory returned the wrong provider: "
                f"expected={options.provider!r} actual={provider.name!r}"
            )
        generated = provider.detect_many(detection_missing)
        generated = _detections_with_contract_version(
            generated, options.contract_version
        )
        generated_by_text = {record.source_text: record for record in generated}
        if set(generated_by_text) != set(detection_missing):
            raise TranslationError(
                "language detection provider returned an incomplete or duplicate result set"
            )
        for record in generated:
            if record.provider != options.provider:
                raise TranslationError("language detection result has wrong provider")
        cache.put_detections(generated)

    unresolved_detections = dict(detection_cached)
    unresolved_detections.update({record.source_text: record for record in generated})

    # A target-language detection is already a complete analysis-text result. Persist
    # it in the full translation cache without making a translation request.
    target_records = [
        TranslationRecord(
            source_text=record.source_text,
            source_hash=record.source_hash,
            detected_language=record.detected_language,
            language_confidence=record.language_confidence,
            translated_text=record.source_text,
            translation_applied=False,
            provider=options.provider,
            target_language=options.target_language,
            contract_version=options.contract_version,
            created_at=record.created_at,
        )
        for record in unresolved_detections.values()
        if record.detected_language == options.target_language
    ]
    cache.put_many(target_records)

    all_detections = [
        (
            _detection_from_translation(translated_cached[text])
            if text in translated_cached
            else unresolved_detections[text]
        )
        for text in unique_texts
    ]
    non_target_candidates = [
        record
        for record in unresolved_detections.values()
        if record.detected_language != options.target_language
    ]
    unsupported_candidates = [
        record for record in non_target_candidates if not record.translation_supported
    ]
    unsupported_count = len(unsupported_candidates)
    auto_detect_fallback_count = 0
    auto_detect_fallback_requests = 0

    if options.provider == "azure":
        # Azure /detect can identify languages/scripts that it marks as unsupported
        # for explicit-source translation. The full run handles those messages by
        # calling /translate without ``from`` so Azure performs translation-time
        # auto-detection. Oversized messages remain blocking because the v3 translate
        # request contract caps the complete request at 5,000 characters.
        translation_candidates = list(non_target_candidates)
        supported_candidates = [
            record for record in translation_candidates if record.translation_supported
        ]
        fallback_candidates = [
            record
            for record in unsupported_candidates
            if len(record.source_text) <= 5_000
        ]
        groups: dict[str, list[str]] = defaultdict(list)
        for record in supported_candidates:
            if len(record.source_text) <= 5_000:
                groups[record.detected_language].append(record.source_text)
        explicit_requests = sum(
            len(
                list(
                    _chunk_texts(
                        group,
                        max_items=25,
                        max_total_chars=5_000,
                        max_item_chars=5_000,
                    )
                )
            )
            for group in groups.values()
        )
        fallback_texts = [record.source_text for record in fallback_candidates]
        auto_detect_fallback_count = len(fallback_candidates)
        auto_detect_fallback_requests = len(
            list(
                _chunk_texts(
                    fallback_texts,
                    max_items=25,
                    max_total_chars=5_000,
                    max_item_chars=5_000,
                )
            )
        )
        exact_requests = explicit_requests + auto_detect_fallback_requests
        item_limit_count = sum(
            len(record.source_text) > 5_000 for record in translation_candidates
        )
    elif options.provider == "aws":
        translation_candidates = [
            record for record in non_target_candidates if record.translation_supported
        ]
        exact_requests = len(translation_candidates)
        item_limit_count = sum(
            len(record.source_text.encode("utf-8")) > 10_000
            for record in translation_candidates
        )
    else:
        raise TranslationError(
            f"unsupported translation provider: {options.provider!r}"
        )

    issues: list[TranslationDetectionIssue] = []
    for record in non_target_candidates:
        if options.provider == "azure":
            oversized = len(record.source_text) > 5_000
        else:
            oversized = len(record.source_text.encode("utf-8")) > 10_000
        if oversized:
            issues.append(
                TranslationDetectionIssue(
                    source_text=record.source_text,
                    source_hash=record.source_hash,
                    detected_language=record.detected_language,
                    language_confidence=record.language_confidence,
                    character_count=len(record.source_text),
                    reason="provider_item_limit",
                    fallback_strategy="none",
                    blocks_full_run=True,
                )
            )
        elif not record.translation_supported:
            fallback_strategy = (
                "azure_translate_auto_detect" if options.provider == "azure" else "none"
            )
            issues.append(
                TranslationDetectionIssue(
                    source_text=record.source_text,
                    source_hash=record.source_hash,
                    detected_language=record.detected_language,
                    language_confidence=record.language_confidence,
                    character_count=len(record.source_text),
                    reason="detected_language_not_translation_supported",
                    fallback_strategy=fallback_strategy,
                    blocks_full_run=options.provider != "azure",
                )
            )

    language_counts: dict[str, int] = defaultdict(int)
    for record in all_detections:
        language_counts[record.detected_language] += 1

    return TranslationDetectionPlan(
        provider=options.provider,
        target_language=options.target_language,
        contract_version=options.contract_version,
        total_message_occurrences=non_empty_occurrences,
        unique_message_count=len(unique_texts),
        translation_cache_hit_count=len(translated_cached),
        detection_cache_hit_count=len(detection_cached),
        newly_detected_count=len(generated),
        language_detection_request_count=detection_request_count,
        target_language_count=sum(
            record.detected_language == options.target_language
            for record in unresolved_detections.values()
        ),
        translation_candidate_count=len(translation_candidates),
        translation_candidate_character_count=sum(
            len(record.source_text) for record in translation_candidates
        ),
        exact_translation_request_count=exact_requests,
        unsupported_translation_count=unsupported_count,
        potential_item_limit_count=item_limit_count,
        language_counts=dict(sorted(language_counts.items())),
        azure_auto_detect_fallback_count=auto_detect_fallback_count,
        azure_auto_detect_fallback_request_count=auto_detect_fallback_requests,
        issues=tuple(
            sorted(
                issues,
                key=lambda item: (
                    item.reason,
                    item.detected_language,
                    item.source_hash,
                ),
            )
        ),
    )


def write_translation_detection_issue_audit(
    plan: TranslationDetectionPlan, path: str | Path
) -> Path:
    """Persist exact message-level preflight issues as JSONL for operator review."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for issue in plan.issues:
            handle.write(
                json.dumps(
                    {
                        "source_hash": issue.source_hash,
                        "original_text": issue.source_text,
                        "detected_language": issue.detected_language,
                        "language_confidence": issue.language_confidence,
                        "character_count": issue.character_count,
                        "reason": issue.reason,
                        "fallback_strategy": issue.fallback_strategy,
                        "blocks_full_run": issue.blocks_full_run,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
    temporary.replace(target)
    return target


def _workload_plan_from_cache_state(
    texts: Sequence[str],
    unique_texts: Sequence[str],
    cached: Mapping[str, TranslationRecord],
    *,
    options: TranslationOptions,
) -> TranslationWorkloadPlan:
    missing = [text for text in unique_texts if text not in cached]
    detection_cached = _cached_detection_records(missing, options=options)
    detection_missing = [text for text in missing if text not in detection_cached]
    non_empty_occurrences = sum(
        1 for text in texts if isinstance(text, str) and text.strip()
    )

    if options.provider == "azure":
        # This exactly matches AzureTranslationProvider._detect batching. No HTTP
        # request is made. Translation calls cannot be known until detection says
        # which cache misses are already English and groups the remainder by source
        # language, so expose a safe 0..N request range instead.
        detection_requests = len(
            list(
                _chunk_texts(
                    detection_missing,
                    max_items=100,
                    max_total_chars=25_000,
                    max_item_chars=10_000,
                )
            )
        )
        potential_item_limit_count = sum(len(text) > 5_000 for text in missing)
    elif options.provider == "aws":
        detection_requests = (len(detection_missing) + 24) // 25
        potential_item_limit_count = sum(
            len(text.encode("utf-8")) > 10_000 for text in missing
        )
    else:
        raise TranslationError(
            f"unsupported translation provider: {options.provider!r}"
        )

    return TranslationWorkloadPlan(
        provider=options.provider,
        target_language=options.target_language,
        contract_version=options.contract_version,
        total_message_occurrences=non_empty_occurrences,
        unique_message_count=len(unique_texts),
        cache_hit_count=len(cached),
        cache_miss_count=len(missing),
        cache_miss_character_count=sum(len(text) for text in missing),
        language_detection_request_count=detection_requests,
        translation_request_min_count=0,
        translation_request_max_count=len(missing),
        potential_item_limit_count=potential_item_limit_count,
    )


def plan_translation_workload(
    texts: Sequence[str], *, options: TranslationOptions
) -> TranslationWorkloadPlan:
    """Inspect persistent cache and estimate provider work without cloud calls."""
    if not options.enabled:
        raise TranslationError(
            "translation workload requested while translation is disabled"
        )
    unique_texts = _unique_source_texts(texts)
    cached = _cached_translation_records(unique_texts, options=options)
    return _workload_plan_from_cache_state(texts, unique_texts, cached, options=options)


def translate_texts_with_cache(
    texts: Sequence[str],
    *,
    options: TranslationOptions,
    provider_factory: Callable[
        [TranslationOptions], TranslationProvider
    ] = build_translation_provider,
) -> list[TranslationRecord]:
    """Translate each unique non-empty source text once and persist the result."""
    if not options.enabled:
        raise TranslationError(
            "translation cache requested while translation is disabled"
        )

    unique_texts = _unique_source_texts(texts)
    if not unique_texts:
        return []

    cache = SQLiteTranslationCache(options.cache_path)
    cached = cache.get_many(
        unique_texts,
        provider=options.provider,
        target_language=options.target_language,
        contract_version=options.contract_version,
    )
    missing = [text for text in unique_texts if text not in cached]
    workload = _workload_plan_from_cache_state(
        texts, unique_texts, cached, options=options
    )
    _LOGGER.info(
        "topic_translation_workload provider=%s unique_messages=%d cache_hits=%d "
        "cache_misses=%d cache_miss_characters=%d detection_requests=%d "
        "translation_requests_min=%d translation_requests_max=%d "
        "potential_item_limit=%d",
        workload.provider,
        workload.unique_message_count,
        workload.cache_hit_count,
        workload.cache_miss_count,
        workload.cache_miss_character_count,
        workload.language_detection_request_count,
        workload.translation_request_min_count,
        workload.translation_request_max_count,
        workload.potential_item_limit_count,
    )

    generated: list[TranslationRecord] = []
    if missing:
        detection_cached = cache.get_detections(
            missing,
            provider=options.provider,
            contract_version=options.contract_version,
        )
        detection_missing = [text for text in missing if text not in detection_cached]

        provider: TranslationProvider | None = None
        generated_detections: list[LanguageDetectionRecord] = []
        if detection_missing:
            provider = provider_factory(options)
            if provider.name != options.provider:
                raise TranslationError(
                    "translation provider factory returned the wrong provider: "
                    f"expected={options.provider!r} actual={provider.name!r}"
                )
            generated_detections = provider.detect_many(detection_missing)
            generated_detections = _detections_with_contract_version(
                generated_detections, options.contract_version
            )
            generated_detection_by_text = {
                record.source_text: record for record in generated_detections
            }
            if set(generated_detection_by_text) != set(detection_missing):
                raise TranslationError(
                    "language detection provider returned an incomplete or duplicate result set"
                )
            for record in generated_detections:
                if record.provider != options.provider:
                    raise TranslationError(
                        "language detection result has wrong provider"
                    )
            cache.put_detections(generated_detections)

        detections = dict(detection_cached)
        detections.update(
            {record.source_text: record for record in generated_detections}
        )
        if set(detections) != set(missing):
            raise TranslationError("language detection cache/result set is incomplete")

        no_translation_records = [
            TranslationRecord(
                source_text=record.source_text,
                source_hash=record.source_hash,
                detected_language=record.detected_language,
                language_confidence=record.language_confidence,
                translated_text=record.source_text,
                translation_applied=False,
                provider=options.provider,
                target_language=options.target_language,
                contract_version=options.contract_version,
                created_at=record.created_at,
            )
            for record in detections.values()
            if record.detected_language == options.target_language
        ]
        generated.extend(no_translation_records)

        to_translate = [
            record
            for record in detections.values()
            if record.detected_language != options.target_language
        ]
        if to_translate:
            if provider is None:
                provider = provider_factory(options)
                if provider.name != options.provider:
                    raise TranslationError(
                        "translation provider factory returned the wrong provider: "
                        f"expected={options.provider!r} actual={provider.name!r}"
                    )
            translated = provider.translate_detected_many(
                to_translate, target_language=options.target_language
            )
            translated = _with_contract_version(translated, options.contract_version)
            translated_by_text = {record.source_text: record for record in translated}
            if set(translated_by_text) != {
                record.source_text for record in to_translate
            }:
                raise TranslationError(
                    "translation provider returned an incomplete or duplicate result set"
                )
            generated.extend(translated)

        generated_by_text = {record.source_text: record for record in generated}
        if set(generated_by_text) != set(missing):
            raise TranslationError(
                "translation provider/cache returned an incomplete or duplicate result set"
            )
        for record in generated:
            if record.provider != options.provider:
                raise TranslationError("translation provider result has wrong provider")
            if record.target_language != options.target_language:
                raise TranslationError(
                    "translation provider result has wrong target language"
                )
            if not isinstance(record.translated_text, str):
                raise TranslationError("translation provider returned non-string text")
        cache.put_many(generated)

    combined = dict(cached)
    combined.update({record.source_text: record for record in generated})
    return [combined[text] for text in unique_texts]


def _message_texts(frame: pd.DataFrame) -> list[str]:
    if "messages" not in frame.columns:
        raise TranslationError(
            "community message dataframe is missing column: messages"
        )
    texts: list[str] = []
    for value in frame["messages"]:
        if isinstance(value, (str, bytes)) or value is None:
            continue
        try:
            iterator = iter(value)
        except TypeError:
            continue
        for message in iterator:
            if isinstance(message, str) and message.strip():
                texts.append(message)
    return texts


def collect_topic_message_texts(
    absolute_community_messages: pd.DataFrame,
    weighted_community_messages: pd.DataFrame,
) -> list[str]:
    """Return the exact non-empty message occurrences that can reach LDA."""
    texts = _message_texts(absolute_community_messages)
    texts.extend(_message_texts(weighted_community_messages))
    return texts


def _replace_message_texts(
    frame: pd.DataFrame, translated_by_source: Mapping[str, str]
) -> pd.DataFrame:
    result = frame.copy()

    def replace_messages(value: Any):
        if isinstance(value, (str, bytes)) or value is None:
            return value
        try:
            items = list(value)
        except TypeError:
            return value
        return [
            translated_by_source.get(item, item) if isinstance(item, str) else item
            for item in items
        ]

    result["messages"] = result["messages"].map(replace_messages)
    return result


def _provenance_frame(records: Sequence[TranslationRecord]) -> pd.DataFrame:
    rows = [
        {
            "source_hash": record.source_hash,
            "original_text": record.source_text,
            "detected_language": record.detected_language,
            "language_confidence": record.language_confidence,
            "target_language": record.target_language,
            "translated_text_en": record.translated_text,
            "translation_applied": bool(record.translation_applied),
            "provider": record.provider,
            "translation_contract_version": record.contract_version,
            "cache_hit": bool(record.cache_hit),
            "status": record.status,
            "created_at": record.created_at,
        }
        for record in sorted(
            records, key=lambda item: (item.source_hash, item.source_text)
        )
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "source_hash",
            "original_text",
            "detected_language",
            "language_confidence",
            "target_language",
            "translated_text_en",
            "translation_applied",
            "provider",
            "translation_contract_version",
            "cache_hit",
            "status",
            "created_at",
        ],
    )


def prepare_translated_topic_messages(
    absolute_community_messages: pd.DataFrame,
    weighted_community_messages: pd.DataFrame,
    *,
    translation_config: Mapping[str, Any],
    output_dir: str | Path,
    data_type: str,
    content_type: str,
    year: str,
    month: str,
    provider_factory: Callable[
        [TranslationOptions], TranslationProvider
    ] = build_translation_provider,
) -> TranslationPreparationResult:
    """Create translated copies for LDA while leaving saved source artifacts untouched."""
    options = TranslationOptions.from_mapping(translation_config)
    if not options.enabled:
        raise TranslationError(
            "prepare_translated_topic_messages called while disabled"
        )

    texts = collect_topic_message_texts(
        absolute_community_messages, weighted_community_messages
    )
    records = translate_texts_with_cache(
        texts,
        options=options,
        provider_factory=provider_factory,
    )
    translated_by_source = {
        record.source_text: record.translated_text for record in records
    }
    abs_translated = _replace_message_texts(
        absolute_community_messages, translated_by_source
    )
    weighted_translated = _replace_message_texts(
        weighted_community_messages, translated_by_source
    )

    path = translation_provenance_path(
        output_dir,
        data_type=data_type,
        content_type=content_type,
        year=year,
        month=month,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    provenance = _provenance_frame(records)
    provenance.to_parquet(path, index=False)

    cache_hits = sum(1 for record in records if record.cache_hit)
    translated_count = sum(1 for record in records if record.translation_applied)
    _LOGGER.info(
        "topic_translation_completed provider=%s month=%s unique_messages=%d "
        "cache_hits=%d translated=%d provenance=%s",
        options.provider,
        month,
        len(records),
        cache_hits,
        translated_count,
        path,
    )
    return TranslationPreparationResult(
        absolute_community_messages=abs_translated,
        weighted_community_messages=weighted_translated,
        provenance_path=path,
        unique_message_count=len(records),
        cache_hit_count=cache_hits,
        translated_count=translated_count,
    )
