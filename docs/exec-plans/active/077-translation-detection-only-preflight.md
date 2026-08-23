# Plan 077 — Translation Detection-Only Preflight

## 1. Objective
Add an incremental cloud detection-only step after Plan 076 so an operator can call Azure Translator `/detect` (or AWS Comprehend when that provider is selected), persist reusable language detections, and report the exact translation workload before authorizing the full translated LDA run.

## 2. Source Boundary
This plan is incremental to Plans 075 and 076. It assumes cached multilingual translation and the provider-free translation workload preflight are already applied.

## 3. Behavior
- `make translation-detect CONFIG=...` prepares/reuses the same network/community inputs as `translation-preflight`.
- It performs language detection only: Azure uses `/detect`; AWS uses Comprehend dominant-language detection.
- It never calls Azure `/translate` or AWS Translate.
- Language detections are cached persistently in the existing translation SQLite cache file and are reused by the subsequent full topic run, so the full run does not repeat detection for already-detected texts.
- Already-complete translation-cache entries are reused and skipped.
- Target-language detections may be promoted to complete no-translation cache records because their analysis text is exactly the original source text.
- After detection the command reports exact source-language counts, non-target texts/characters, unsupported-language count, and the exact translation request count under the configured provider batching contract.
- `DATASET_ID=<month>` remains supported.

## 4. Protected Contracts
No changes to IF/WIF metrics, graph thresholds, Louvain, LDA defaults/phrase behavior, community/evolution semantics, original source artifacts, translation output semantics, GPT themes, embeddings/clustering, database behavior, or frontend behavior.

## 5. Validation
- Unit tests cover Azure detection-only behavior, persistent detection reuse by the later translation run, exact post-detection Azure request counts, and CLI no-translation behavior.
- Existing Plan 075/076 translation, config, hashing, cache, and protected-default tests remain green.
- No automated test performs a live cloud request.

## 6. Progress Log
- 2026-08-21: Read required repository contracts and Plans 074–076 before editing.
- 2026-08-21: Baseline translation/preflight/config/hash/default selection passed (one existing Parquet test skipped because `pyarrow` is absent).
- 2026-08-21: Implemented persistent `language_detections` cache rows in the existing SQLite translation cache, provider-neutral `detect_many`/`translate_detected_many` adapters, and detection reuse in the normal translation path.
- 2026-08-21: Added `translation-detect` CLI/Make target. Azure uses `/detect`; AWS uses Comprehend. The command never calls a translation endpoint and reports exact post-detection translation requests plus language distribution.
- 2026-08-21: Target-language detections are promoted to complete no-translation cache records; provider-free Plan 076 workload planning now recognizes cached detections when estimating remaining detection calls.
- 2026-08-21: Focused translation/preflight/config/hash/cache/default/tracking tests passed (one existing Parquet test skipped because `pyarrow` is absent); protected graph/Louvain/theme/transition/provider tests passed; `compileall`, config validation, CLI help, and Make target dry-run passed. No live cloud calls were made.
