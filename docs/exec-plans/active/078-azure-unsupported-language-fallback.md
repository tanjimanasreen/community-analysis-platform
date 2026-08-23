# Plan 078 — Azure Unsupported-Language Translation Fallback

## 1. Objective
Resolve Azure `/detect` results where `isTranslationSupported=false` without silently feeding untranslated foreign text into English LDA. Preserve detection-only planning/cache reuse and add an auditable, bounded fallback through Azure `/translate` source-language auto-detection.

## 2. Source Boundary
This plan is incremental to Plans 075–077 and the user-supplied translation updates containing the Azure 429/backoff hardening. Those rate-limit changes are preserved unchanged.

## 3. Behavior
- Azure `/detect` remains the detection-only planning endpoint.
- Target-language detections remain no-translation cache hits.
- Explicitly supported non-target detections continue to call `/translate` with `from=<detected_language>`.
- A non-target Azure detection with `isTranslationSupported=false` is retried during the full run through `/translate` with `from` omitted, allowing Azure translation-time source-language auto-detection.
- The original source text is never silently substituted for an unsupported foreign message.
- Messages above the Azure v3 5,000-character translate request limit remain explicit blocking errors rather than being passed through untranslated.
- Successful auto-detect fallback translations are persistently cached and marked `success_auto_detect_fallback` in translation provenance.
- Detection-only planning includes the fallback messages and requests in the exact translation workload and writes a message-level JSONL audit under `<output_base_path>/_preflight/`.

## 4. Protected Contracts
No changes to IF/WIF metrics, graph thresholds, Louvain, LDA defaults/phrase behavior, community/evolution semantics, original Telegram/Twitter source artifacts, theme contracts, embeddings/clustering, database behavior, or frontend behavior.

The translation contract remains `v1` because this change fixes the unresolved/unsafe edge-case path before any valid translated LDA result existed; existing cached language detections remain reusable.

## 5. Validation
- Unit tests use fake Azure HTTP sessions only.
- Regression tests verify unsupported detections call `/translate` without `from`, never pass original foreign text through, cache fallback translations, count fallback requests exactly, write the issue audit, and fail explicitly on oversized messages.
- No automated test performs a live Azure/AWS request.

## 6. Progress Log
- 2026-08-21: Read required repository contracts and Plans 074–077 before editing.
- 2026-08-21: Inspected the supplied translation update and preserved its 429 retry/backoff changes.
- 2026-08-21: Removed the unsafe unsupported/oversized original-text fallback from the Azure translation adapter.
- 2026-08-21: Added Azure `/translate` auto-detect fallback for `/detect`-unsupported messages, persistent cache reuse, provenance status, exact preflight accounting, and JSONL issue audit.
- 2026-08-21: Focused translation and translation-preflight CLI tests pass offline; one existing Parquet test remains skipped because `pyarrow` is absent. No live provider calls were made.
