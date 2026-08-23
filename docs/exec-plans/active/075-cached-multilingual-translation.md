# Plan 075 — Cached Multilingual Translation Before LDA

## 1. Objective
Add an additive, provider-configurable multilingual preparation boundary immediately before topic preprocessing/LDA. Azure AI Translator is the canonical Telegram default; AWS Comprehend + Translate is an alternate provider selected by configuration. Original community-message artifacts remain unchanged.

## 2. Source Snapshot
- Archive: `community-analysis-full-review-20260821-0003.zip`
- SHA-256: `ba4110a2739f4751448dd1ff6c70ec7ecd7136ac3dedbc745a0fd9815edad22a`
- Branch: `feature/frontend-ui-upgrade`
- HEAD: `5b60f1f645b0ac47385fbefcb571c7dfc8124efe`
- Snapshot includes the uncommitted Plan 074 cross-run stage-cache implementation and is the source of truth for this plan.

## 3. Design
The topic boundary is:

```text
saved community messages (original text)
  -> topic stage cache lookup
  -> if topic cache miss and translation enabled:
       per-message translation cache lookup
       -> cached result: reuse
       -> missing result: provider language detection + English translation
  -> translated in-memory copies
  -> unchanged thesis text preprocessing
  -> unchanged unigram / phrase LDA
```

Translation cache identity is:

```text
source text SHA-256 + provider + target language + translation contract version
```

Operational values such as cache path and timeout do not change analytical identity. Azure↔AWS or translation-contract changes invalidate the topic stage. A complete per-message cache hit never constructs a cloud provider client.

## 4. Provider Contract
- `azure` (default): Azure Translator `/detect` followed by `/translate` only for non-English texts. Credentials/endpoints are environment-only (`AZURE_TRANSLATOR_*`).
- `aws`: Amazon Comprehend dominant-language detection plus Amazon Translate. boto3 is imported lazily and uses the standard AWS credential chain/IAM role.
- No test performs live cloud requests.
- Provider failures fail the topic stage explicitly; untranslated foreign text is never silently substituted.

## 5. Artifact Contract
When translation is enabled, the topic stage emits one Parquet provenance row per unique non-empty source message with:
- source hash and exact original text;
- detected language/confidence;
- exact English analysis text;
- translation-applied flag;
- provider, target language, contract version;
- per-message cache-hit flag/status/timestamp.

The provenance artifact participates in Plan 074 topic-stage snapshot/restore and the final run manifest.

## 6. Configuration
Defaults are safe/additive:

```yaml
translation:
  enabled: false
  provider: azure
  target_language: en
  contract_version: v1
  cache_path: .cache/translation_cache.sqlite3
  timeout_seconds: 30
```

Canonical Telegram forwarded-message evolution explicitly enables Azure. Canonical Twitter reply and retweet/quote remain disabled/opt-in.

## 7. Protected Contracts
Do not change IF/WIF metrics, graph thresholds, Louvain defaults, LDA implementation/defaults, phrase behavior, community matching/evolution semantics, raw Telegram/Twitter normalization, GPT theme evidence/prompt safety contracts, embedding/clustering behavior, database behavior, or frontend behavior.

## 8. Validation
Focused offline validation:

```bash
python -m pytest -q \
  tests/unit/test_translation.py \
  tests/unit/test_config.py \
  tests/unit/test_orchestration_hashing.py \
  tests/unit/test_stage_artifact_cache.py \
  tests/unit/test_current_defaults.py \
  tests/unit/test_tracking_summaries.py
python -m compileall -q src tests
make validate-config PYTHON=python
```

Provider tests use fake HTTP/AWS clients only.

## 9. Progress Log
- 2026-08-21: Read required repository contracts and Plan 074 before editing.
- 2026-08-21: Added provider-neutral translation contract, persistent SQLite per-message cache, Azure provider, AWS provider, and translation provenance.
- 2026-08-21: Integrated translated in-memory message copies immediately before unchanged topic preprocessing/LDA; original saved community-message artifacts remain untouched.
- 2026-08-21: Integrated translation identity into Plan 074 topic cache and added provenance to topic stage restore/publication.
- 2026-08-21: Canonical Telegram enables Azure; canonical Twitter configs remain opt-in.
- 2026-08-21: Added environment-only Azure credentials and preflight coverage; AWS uses the normal SDK/IAM credential chain.
- 2026-08-21: Focused translation/config/hash/cache/default tests passed offline; Parquet-specific translation provenance test is skipped in the review interpreter because `pyarrow` is absent. No live Azure/AWS calls were made.
- 2026-08-21: Documented the translation-derived topic-input data contract; AWS adapter remains a lazy optional runtime dependency (`boto3`) when selected.
- 2026-08-21: Plan 076 adds a provider-free translation workload preflight/dry-run and pre-provider workload logging; translation semantics and cache identity remain unchanged.
- 2026-08-21: Plan 077 adds persistent language-detection cache reuse so a detection-only planning pass avoids repeating cloud detection during the later full translation/topic run.
- 2026-08-21: **429 root-cause fix** — `make translation-detect` burst-fired up to 20 rapid sequential `/detect` HTTP calls with zero inter-request delay and no retry logic, triggering Azure's sliding-window rate limiter. Root causes: (1) `_post()` had no retry/backoff on 429, (2) `_detect()` and `_translate_group()` looped through chunks with no delay. Fix: added `inter_chunk_delay_seconds` (default 0.5 s) and `max_retries` (default 5) to `TranslationOptions` and `AzureTranslationProvider`; `_post()` now reads the `Retry-After` header and falls back to exponential backoff (2^attempt s, capped 60 s); `_detect()` and `_translate_group()` sleep `inter_chunk_delay_seconds` between chunks. Both fields are configurable in YAML. Five new offline tests verify retry-with-Retry-After, retry-with-backoff, exhausted-retries error, and options wiring. All 18 translation tests pass.
- 2026-08-21: Plan 078 resolves Azure `/detect` results with `isTranslationSupported=false` by using `/translate` source auto-detection during the full run; unsupported text is never silently passed through to LDA, and detection preflight emits a message-level audit.
