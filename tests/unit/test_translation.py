from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from src.text.translation import (
    AwsTranslationProvider,
    AzureTranslationProvider,
    LanguageDetectionRecord,
    TranslationError,
    TranslationOptions,
    TranslationRecord,
    detect_texts_with_cache,
    plan_translation_workload,
    prepare_translated_topic_messages,
    source_text_hash,
    translate_texts_with_cache,
    translation_cache_key,
    write_translation_detection_issue_audit,
)


class _FakeProvider:
    name = "azure"

    def __init__(self):
        self.detect_calls: list[tuple[str, ...]] = []
        self.translate_calls: list[tuple[tuple[str, ...], str]] = []

    def detect_many(self, texts):
        self.detect_calls.append(tuple(texts))
        return [
            LanguageDetectionRecord(
                source_text=text,
                source_hash=source_text_hash(text),
                detected_language="pt" if "governo" in text.lower() else "en",
                language_confidence=0.99,
                translation_supported=True,
                provider=self.name,
                contract_version="v1",
                created_at="2026-08-21T00:00:00+00:00",
            )
            for text in texts
        ]

    def translate_detected_many(self, detections, *, target_language):
        self.translate_calls.append(
            (tuple(record.source_text for record in detections), target_language)
        )
        return [
            TranslationRecord(
                source_text=record.source_text,
                source_hash=record.source_hash,
                detected_language=record.detected_language,
                language_confidence=record.language_confidence,
                translated_text=(
                    "The government announced a policy"
                    if "governo" in record.source_text.lower()
                    else record.source_text
                ),
                translation_applied=record.detected_language != target_language,
                provider=self.name,
                target_language=target_language,
                contract_version="v1",
                created_at="2026-08-21T00:00:00+00:00",
            )
            for record in detections
        ]

    def translate_many(self, texts, *, target_language):
        return self.translate_detected_many(
            self.detect_many(texts), target_language=target_language
        )


def _options(tmp_path: Path, **overrides) -> TranslationOptions:
    base = TranslationOptions(
        enabled=True,
        provider="azure",
        target_language="en",
        contract_version="v1",
        cache_path=str(tmp_path / "translation.sqlite3"),
        timeout_seconds=30.0,
    )
    return replace(base, **overrides)


def test_translation_cache_identity_changes_by_provider_and_contract():
    text = "olá mundo"
    azure_v1 = translation_cache_key(
        text, provider="azure", target_language="en", contract_version="v1"
    )
    aws_v1 = translation_cache_key(
        text, provider="aws", target_language="en", contract_version="v1"
    )
    azure_v2 = translation_cache_key(
        text, provider="azure", target_language="en", contract_version="v2"
    )
    assert azure_v1 != aws_v1
    assert azure_v1 != azure_v2


def test_complete_translation_cache_hit_does_not_construct_provider(tmp_path):
    provider = _FakeProvider()
    options = _options(tmp_path)

    first = translate_texts_with_cache(
        ["O governo anunciou uma política", "hello", "O governo anunciou uma política"],
        options=options,
        provider_factory=lambda _: provider,
    )
    assert len(first) == 2
    assert len(provider.detect_calls) == 1
    assert len(provider.translate_calls) == 1

    def should_not_construct(_):
        raise AssertionError("provider must not be constructed on a complete cache hit")

    second = translate_texts_with_cache(
        ["hello", "O governo anunciou uma política"],
        options=options,
        provider_factory=should_not_construct,
    )
    assert len(second) == 2
    assert all(record.cache_hit for record in second)


def test_prepare_translated_topic_messages_preserves_source_frames_and_deduplicates(
    tmp_path,
):
    pytest.importorskip("pyarrow")
    absolute = pd.DataFrame(
        {
            "community_number": [1],
            "messages": [["O governo anunciou uma política", "hello"]],
            "messages_ids": [["m1", "m2"]],
            "total_messages": [2],
        }
    )
    weighted = pd.DataFrame(
        {
            "community_number": [2],
            "messages": [["O governo anunciou uma política"]],
            "messages_ids": [["m1"]],
            "total_messages": [1],
        }
    )
    provider = _FakeProvider()
    options = _options(tmp_path)

    result = prepare_translated_topic_messages(
        absolute,
        weighted,
        translation_config={
            "enabled": True,
            "provider": "azure",
            "target_language": "en",
            "contract_version": "v1",
            "cache_path": options.cache_path,
        },
        output_dir=tmp_path / "run",
        data_type="telegram",
        content_type="forward",
        year="2019",
        month="02",
        provider_factory=lambda _: provider,
    )

    assert absolute.loc[0, "messages"][0] == "O governo anunciou uma política"
    assert weighted.loc[0, "messages"][0] == "O governo anunciou uma política"
    assert result.absolute_community_messages.loc[0, "messages"] == [
        "The government announced a policy",
        "hello",
    ]
    assert result.weighted_community_messages.loc[0, "messages"] == [
        "The government announced a policy"
    ]
    assert result.unique_message_count == 2
    assert len(provider.detect_calls) == 1
    assert len(provider.detect_calls[0]) == 2
    assert len(provider.translate_calls) == 1
    assert len(provider.translate_calls[0][0]) == 1

    provenance = pd.read_parquet(result.provenance_path)
    assert list(provenance.columns) == [
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
    ]
    assert len(provenance) == 2
    portuguese = provenance.loc[
        provenance["original_text"] == "O governo anunciou uma política"
    ].iloc[0]
    assert portuguese["detected_language"] == "pt"
    assert portuguese["translated_text_en"] == "The government announced a policy"
    assert bool(portuguese["translation_applied"]) is True


def test_azure_provider_detects_then_translates_only_non_target_language():
    class Response:
        def __init__(self, payload):
            self.payload = payload
            self.status_code = 200
            self.headers: dict = {}

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Session:
        def __init__(self):
            self.calls = []

        def post(self, url, *, params, headers, json, timeout):
            self.calls.append((url, params, json))
            if url.endswith("/detect"):
                return Response(
                    [
                        {
                            "language": "en",
                            "score": 1.0,
                            "isTranslationSupported": True,
                        },
                        {
                            "language": "pt",
                            "score": 0.98,
                            "isTranslationSupported": True,
                        },
                    ]
                )
            return Response([{"translations": [{"text": "governo"}]}])

    session = Session()
    provider = AzureTranslationProvider(api_key="secret", session=session)
    records = provider.translate_many(["government", "governo"], target_language="en")

    assert records[0].translated_text == "government"
    assert records[0].translation_applied is False
    assert records[1].translated_text == "governo"
    assert records[1].translation_applied is True
    assert len(session.calls) == 2
    assert session.calls[1][1]["from"] == "pt"


def test_aws_provider_uses_comprehend_detection_and_translate_for_non_english_only():
    class Comprehend:
        def batch_detect_dominant_language(self, *, TextList):
            assert TextList == ["hello", "olá"]
            return {
                "ResultList": [
                    {"Index": 0, "Languages": [{"LanguageCode": "en", "Score": 0.99}]},
                    {"Index": 1, "Languages": [{"LanguageCode": "pt", "Score": 0.97}]},
                ],
                "ErrorList": [],
            }

    class Translate:
        def __init__(self):
            self.calls = []

        def translate_text(self, **kwargs):
            self.calls.append(kwargs)
            return {"TranslatedText": "hello translated"}

    translate = Translate()
    provider = AwsTranslationProvider(
        comprehend_client=Comprehend(), translate_client=translate
    )
    records = provider.translate_many(["hello", "olá"], target_language="en")

    assert records[0].translation_applied is False
    assert records[0].translated_text == "hello"
    assert records[1].translation_applied is True
    assert records[1].translated_text == "hello translated"
    assert len(translate.calls) == 1
    assert translate.calls[0]["SourceLanguageCode"] == "pt"


def test_translation_workload_plan_is_cloud_free_and_does_not_create_empty_cache(
    tmp_path,
):
    cache_path = tmp_path / "missing-cache.sqlite3"
    options = _options(tmp_path, cache_path=str(cache_path))

    plan = plan_translation_workload(
        ["hello", "olá", "hello"],
        options=options,
    )

    assert plan.total_message_occurrences == 3
    assert plan.unique_message_count == 2
    assert plan.cache_hit_count == 0
    assert plan.cache_miss_count == 2
    assert plan.cache_miss_character_count == len("hello") + len("olá")
    assert plan.language_detection_request_count == 1
    assert plan.translation_request_min_count == 0
    assert plan.translation_request_max_count == 2
    assert cache_path.exists() is False


def test_translation_workload_plan_reuses_cache_and_matches_azure_detection_batching(
    tmp_path,
):
    provider = _FakeProvider()
    options = _options(tmp_path)
    translate_texts_with_cache(
        ["hello"],
        options=options,
        provider_factory=lambda _: provider,
    )

    missing = [f"message-{index}" for index in range(101)]
    plan = plan_translation_workload(
        ["hello", *missing, "message-0"],
        options=options,
    )

    assert plan.total_message_occurrences == 103
    assert plan.unique_message_count == 102
    assert plan.cache_hit_count == 1
    assert plan.cache_miss_count == 101
    assert plan.language_detection_request_count == 2
    assert plan.translation_request_min_count == 0
    assert plan.translation_request_max_count == 101


def test_azure_detection_planning_matches_25k_operational_chunking(tmp_path):
    options = _options(tmp_path)
    texts = ["a" * 9_000, "b" * 9_000, "c" * 9_000]

    plan = plan_translation_workload(texts, options=options)

    assert plan.language_detection_request_count == 2


def test_translation_workload_plan_flags_potential_azure_translate_item_limit(tmp_path):
    options = _options(tmp_path)
    text = "x" * 5_001

    plan = plan_translation_workload([text], options=options)

    assert plan.language_detection_request_count == 1
    assert plan.potential_item_limit_count == 1


def test_translation_workload_plan_aws_detection_batch_count(tmp_path):
    options = _options(tmp_path, provider="aws")
    texts = [f"message-{index}" for index in range(26)]

    plan = plan_translation_workload(texts, options=options)

    assert plan.language_detection_request_count == 2
    assert plan.translation_request_max_count == 26


def test_detection_only_caches_language_and_full_translation_reuses_it(tmp_path):
    provider = _FakeProvider()
    options = _options(tmp_path)

    plan = detect_texts_with_cache(
        ["hello", "O governo anunciou uma política"],
        options=options,
        provider_factory=lambda _: provider,
    )

    assert plan.newly_detected_count == 2
    assert plan.language_detection_request_count == 1
    assert plan.target_language_count == 1
    assert plan.translation_candidate_count == 1
    assert plan.exact_translation_request_count == 1
    assert provider.detect_calls
    assert provider.translate_calls == []

    records = translate_texts_with_cache(
        ["hello", "O governo anunciou uma política"],
        options=options,
        provider_factory=lambda _: provider,
    )

    assert len(provider.detect_calls) == 1
    assert len(provider.translate_calls) == 1
    assert provider.translate_calls[0][0] == ("O governo anunciou uma política",)
    assert {record.detected_language for record in records} == {"en", "pt"}


def test_detection_only_reports_exact_azure_translation_batches_by_language(tmp_path):
    class DetectorOnlyProvider:
        name = "azure"

        def __init__(self):
            self.detect_calls = 0

        def detect_many(self, texts):
            self.detect_calls += 1
            records = []
            for text in texts:
                if text.startswith("pt-"):
                    language = "pt"
                elif text.startswith("es-"):
                    language = "es"
                else:
                    language = "en"
                records.append(
                    LanguageDetectionRecord(
                        source_text=text,
                        source_hash=source_text_hash(text),
                        detected_language=language,
                        language_confidence=0.99,
                        translation_supported=True,
                        provider=self.name,
                        contract_version="v1",
                        created_at="2026-08-21T00:00:00+00:00",
                    )
                )
            return records

    provider = DetectorOnlyProvider()
    options = _options(tmp_path)
    texts = [
        *[f"pt-{index}" for index in range(30)],
        *[f"es-{index}" for index in range(30)],
        *[f"en-{index}" for index in range(10)],
    ]

    plan = detect_texts_with_cache(
        texts,
        options=options,
        provider_factory=lambda _: provider,
    )

    assert provider.detect_calls == 1
    assert plan.language_detection_request_count == 1
    assert plan.language_counts == {"en": 10, "es": 30, "pt": 30}
    assert plan.target_language_count == 10
    assert plan.translation_candidate_count == 60
    assert plan.exact_translation_request_count == 4
    assert plan.unsupported_translation_count == 0


def test_provider_free_preflight_sees_cached_detections_after_detection_only(tmp_path):
    provider = _FakeProvider()
    options = _options(tmp_path)
    texts = ["hello", "O governo anunciou uma política"]

    detect_texts_with_cache(
        texts,
        options=options,
        provider_factory=lambda _: provider,
    )
    plan = plan_translation_workload(texts, options=options)

    assert plan.cache_hit_count == 1
    assert plan.cache_miss_count == 1
    assert plan.language_detection_request_count == 0


def test_azure_detection_only_calls_detect_then_full_run_reuses_detection(tmp_path):
    class Response:
        def __init__(self, payload):
            self.payload = payload
            self.status_code = 200
            self.headers: dict = {}

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Session:
        def __init__(self):
            self.routes = []

        def post(self, url, *, params, headers, json, timeout):
            route = "/detect" if url.endswith("/detect") else "/translate"
            self.routes.append(route)
            if route == "/detect":
                return Response(
                    [
                        {
                            "language": "en",
                            "score": 1.0,
                            "isTranslationSupported": True,
                        },
                        {
                            "language": "pt",
                            "score": 0.98,
                            "isTranslationSupported": True,
                        },
                    ]
                )
            return Response([{"translations": [{"text": "government"}]}])

    session = Session()
    provider = AzureTranslationProvider(api_key="secret", session=session)
    options = _options(tmp_path)
    texts = ["government", "governo"]

    detect_texts_with_cache(
        texts,
        options=options,
        provider_factory=lambda _: provider,
    )
    assert session.routes == ["/detect"]

    translate_texts_with_cache(
        texts,
        options=options,
        provider_factory=lambda _: provider,
    )
    assert session.routes == ["/detect", "/translate"]


# ---------------------------------------------------------------------------
# Rate-limit / retry tests (all use fake sessions – no live Azure calls)
# ---------------------------------------------------------------------------


def test_azure_post_retries_on_429_with_retry_after_header(monkeypatch):
    """_post() must honour Retry-After and succeed on a subsequent attempt."""
    import src.text.translation as _mod

    slept: list[float] = []
    monkeypatch.setattr(_mod.time, "sleep", lambda s: slept.append(s))

    call_count = 0

    class Response:
        def __init__(self, status, payload=None):
            self.status_code = status
            self.headers = {"Retry-After": "2"} if status == 429 else {}
            self._payload = payload or []

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class Session:
        def post(self, url, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Response(429)
            return Response(
                200,
                [{"language": "en", "score": 1.0, "isTranslationSupported": True}],
            )

    provider = AzureTranslationProvider(
        api_key="key",
        session=Session(),
        max_retries=3,
        inter_chunk_delay_seconds=0.0,
        initial_delay_seconds=0.0,
    )
    detected = provider.detect_many(["hello"])
    assert len(detected) == 1
    assert detected[0].detected_language == "en"
    # Must have slept for Retry-After=2
    assert slept == [2.0]
    assert call_count == 2


def test_azure_post_retries_on_429_without_retry_after_uses_exponential_backoff(
    monkeypatch,
):
    """_post() must fall back to exponential backoff when Retry-After is absent."""
    import src.text.translation as _mod

    slept: list[float] = []
    monkeypatch.setattr(_mod.time, "sleep", lambda s: slept.append(s))

    call_count = 0

    class Response:
        def __init__(self, status, payload=None):
            self.status_code = status
            self.headers: dict = {}  # no Retry-After
            self._payload = payload or []

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class Session:
        def post(self, url, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return Response(429)
            return Response(
                200,
                [{"language": "en", "score": 1.0, "isTranslationSupported": True}],
            )

    provider = AzureTranslationProvider(
        api_key="key",
        session=Session(),
        max_retries=5,
        inter_chunk_delay_seconds=0.0,
        initial_delay_seconds=0.0,
    )
    detected = provider.detect_many(["hello"])
    assert detected[0].detected_language == "en"
    # Backoff: attempt 0 → 2^0=1s, attempt 1 → 2^1=2s
    assert slept == [1.0, 2.0]
    assert call_count == 3


def test_azure_post_raises_after_all_retries_exhausted(monkeypatch):
    """_post() must raise TranslationError when all retry attempts return 429."""
    import src.text.translation as _mod
    from src.text.translation import TranslationError

    monkeypatch.setattr(_mod.time, "sleep", lambda _s: None)

    class Response:
        status_code = 429
        headers: dict = {}

        def raise_for_status(self):
            return None

        def json(self):
            return []

    class Session:
        def post(self, *_a, **_kw):
            return Response()

    provider = AzureTranslationProvider(
        api_key="key",
        session=Session(),
        max_retries=3,
        inter_chunk_delay_seconds=0.0,
        initial_delay_seconds=0.0,
    )
    with pytest.raises(TranslationError, match="after 3 attempt"):
        provider.detect_many(["hello"])


def test_translation_options_from_mapping_reads_new_rate_limit_fields():
    """TranslationOptions.from_mapping must populate the new rate-limit fields."""
    opts = TranslationOptions.from_mapping(
        {
            "enabled": True,
            "provider": "azure",
            "target_language": "en",
            "contract_version": "v1",
            "initial_delay_seconds": 3.0,
            "inter_chunk_delay_seconds": 1.5,
            "max_retries": 7,
        }
    )
    assert opts.initial_delay_seconds == 3.0
    assert opts.inter_chunk_delay_seconds == 1.5
    assert opts.max_retries == 7


def test_translation_options_default_rate_limit_fields():
    """Default values must prevent burst 429s without explicit config."""
    opts = TranslationOptions(enabled=True)
    assert opts.initial_delay_seconds == 2.0
    assert opts.inter_chunk_delay_seconds == 0.5
    assert opts.max_retries == 8


# ---------------------------------------------------------------------------
# Azure unsupported-detection fallback (Plan 078)
# ---------------------------------------------------------------------------


def test_azure_unsupported_detection_uses_translate_auto_detection_not_original_text(
    monkeypatch,
):
    """A /detect-unsupported language must be translated, never silently passed to LDA."""
    import src.text.translation as _mod

    monkeypatch.setattr(_mod.time, "sleep", lambda _seconds: None)

    class Response:
        def __init__(self, payload):
            self.payload = payload
            self.status_code = 200
            self.headers: dict = {}

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Session:
        def __init__(self):
            self.calls = []

        def post(self, url, *, params, headers, json, timeout):
            self.calls.append((url, dict(params), list(json)))
            if url.endswith("/detect"):
                return Response(
                    [
                        {
                            "language": "bn-latn",
                            "score": 0.81,
                            "isTranslationSupported": False,
                        }
                    ]
                )
            return Response(
                [
                    {
                        "detectedLanguage": {"language": "bn", "score": 0.96},
                        "translations": [{"text": "This is translated English"}],
                    }
                ]
            )

    session = Session()
    provider = AzureTranslationProvider(
        api_key="secret",
        session=session,
        initial_delay_seconds=0.0,
        inter_chunk_delay_seconds=0.0,
    )

    records = provider.translate_many(["ami banglay likhi"], target_language="en")

    assert len(records) == 1
    assert records[0].translated_text == "This is translated English"
    assert records[0].translated_text != records[0].source_text
    assert records[0].translation_applied is True
    assert records[0].status == "success_auto_detect_fallback"
    assert len(session.calls) == 2
    translate_params = session.calls[1][1]
    assert translate_params == {"api-version": "3.0", "to": "en"}
    assert "from" not in translate_params


def test_detection_plan_counts_azure_auto_detect_fallback_and_writes_audit(tmp_path):
    class Detector:
        name = "azure"

        def detect_many(self, texts):
            records = []
            for text in texts:
                unsupported = text.startswith("romanized-")
                records.append(
                    LanguageDetectionRecord(
                        source_text=text,
                        source_hash=source_text_hash(text),
                        detected_language="bn-latn" if unsupported else "pt",
                        language_confidence=0.75 if unsupported else 0.99,
                        translation_supported=not unsupported,
                        provider=self.name,
                        contract_version="v1",
                        created_at="2026-08-21T00:00:00+00:00",
                    )
                )
            return records

    options = _options(tmp_path)
    texts = ["romanized-one", "romanized-two", "governo"]
    plan = detect_texts_with_cache(
        texts,
        options=options,
        provider_factory=lambda _: Detector(),
    )

    assert plan.translation_candidate_count == 3
    assert plan.unsupported_translation_count == 2
    assert plan.azure_auto_detect_fallback_count == 2
    assert plan.azure_auto_detect_fallback_request_count == 1
    # One explicit Portuguese request + one auto-detect fallback request.
    assert plan.exact_translation_request_count == 2
    assert plan.potential_item_limit_count == 0
    assert len(plan.issues) == 2
    assert all(
        issue.fallback_strategy == "azure_translate_auto_detect"
        for issue in plan.issues
    )
    assert all(issue.blocks_full_run is False for issue in plan.issues)

    audit = write_translation_detection_issue_audit(
        plan, tmp_path / "translation_detection_issues.jsonl"
    )
    rows = [__import__("json").loads(line) for line in audit.read_text().splitlines()]
    assert {row["original_text"] for row in rows} == {"romanized-one", "romanized-two"}
    assert {row["reason"] for row in rows} == {
        "detected_language_not_translation_supported"
    }


def test_azure_oversized_message_fails_instead_of_passing_original_text():
    provider = AzureTranslationProvider(
        api_key="secret",
        session=object(),
        initial_delay_seconds=0.0,
        inter_chunk_delay_seconds=0.0,
    )
    text = "x" * 5_001
    detection = LanguageDetectionRecord(
        source_text=text,
        source_hash=source_text_hash(text),
        detected_language="pt",
        language_confidence=0.99,
        translation_supported=True,
        provider="azure",
        contract_version="v1",
        created_at="2026-08-21T00:00:00+00:00",
    )

    with pytest.raises(TranslationError, match="5,000-character"):
        provider.translate_detected_many([detection], target_language="en")


def test_auto_detect_fallback_translation_is_cached_and_reused(tmp_path, monkeypatch):
    import src.text.translation as _mod

    monkeypatch.setattr(_mod.time, "sleep", lambda _seconds: None)

    class Response:
        def __init__(self, payload):
            self.payload = payload
            self.status_code = 200
            self.headers: dict = {}

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Session:
        def post(self, url, *, params, headers, json, timeout):
            if url.endswith("/detect"):
                return Response(
                    [
                        {
                            "language": "bn-latn",
                            "score": 0.8,
                            "isTranslationSupported": False,
                        }
                    ]
                )
            return Response(
                [
                    {
                        "detectedLanguage": {"language": "bn", "score": 0.95},
                        "translations": [{"text": "cached English"}],
                    }
                ]
            )

    options = _options(tmp_path)
    provider = AzureTranslationProvider(
        api_key="secret",
        session=Session(),
        initial_delay_seconds=0.0,
        inter_chunk_delay_seconds=0.0,
    )
    first = translate_texts_with_cache(
        ["romanized source"],
        options=options,
        provider_factory=lambda _: provider,
    )
    assert first[0].status == "success_auto_detect_fallback"

    def should_not_construct(_options):
        raise AssertionError(
            "provider should not be constructed on translation-cache hit"
        )

    second = translate_texts_with_cache(
        ["romanized source"],
        options=options,
        provider_factory=should_not_construct,
    )
    assert second[0].cache_hit is True
    assert second[0].translated_text == "cached English"
    assert second[0].status == "success_auto_detect_fallback"


def test_cached_unsupported_detection_reuses_detect_and_calls_only_auto_translate(
    tmp_path, monkeypatch
):
    import src.text.translation as _mod

    monkeypatch.setattr(_mod.time, "sleep", lambda _seconds: None)

    class Response:
        def __init__(self, payload):
            self.payload = payload
            self.status_code = 200
            self.headers: dict = {}

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Session:
        def __init__(self):
            self.calls = []

        def post(self, url, *, params, headers, json, timeout):
            self.calls.append((url, dict(params)))
            if url.endswith("/detect"):
                return Response(
                    [
                        {
                            "language": "bn-latn",
                            "score": 0.8,
                            "isTranslationSupported": False,
                        }
                    ]
                )
            return Response(
                [
                    {
                        "detectedLanguage": {"language": "bn", "score": 0.95},
                        "translations": [{"text": "English from cached detection"}],
                    }
                ]
            )

    session = Session()
    provider = AzureTranslationProvider(
        api_key="secret",
        session=session,
        initial_delay_seconds=0.0,
        inter_chunk_delay_seconds=0.0,
    )
    options = _options(tmp_path)
    text = "romanized cached source"

    detect_texts_with_cache(
        [text], options=options, provider_factory=lambda _: provider
    )
    assert [call[0].rsplit("/", 1)[-1] for call in session.calls] == ["detect"]

    records = translate_texts_with_cache(
        [text], options=options, provider_factory=lambda _: provider
    )
    assert [call[0].rsplit("/", 1)[-1] for call in session.calls] == [
        "detect",
        "translate",
    ]
    assert "from" not in session.calls[-1][1]
    assert records[0].translated_text == "English from cached detection"
    assert records[0].status == "success_auto_detect_fallback"
