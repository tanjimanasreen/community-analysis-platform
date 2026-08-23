# Plan 076 — Translation Workload Preflight / Dry Run

## 1. Objective
Add a provider-free dry run that reports the exact persistent-cache misses and cloud language-detection workload at the LDA translation boundary before any Azure/AWS detection or translation request is made.

## 2. Source Boundary
This plan is incremental to Plan 075 and assumes the Plan 075 cached multilingual translation patch is already applied.

## 3. Behavior
- `make translation-preflight CONFIG=...` runs or reuses only the network/community preparation needed to obtain the exact messages that can reach LDA.
- Plan 074 network-stage cache is reused when valid; a cold preflight warms that cache for the subsequent full run.
- Topic/LDA, theme generation, language-detection, and translation providers are not executed.
- Candidate texts are deduplicated across all selected months before persistent translation-cache lookup.
- The report includes message occurrences, unique messages, translation cache hits/misses, miss characters, exact language-detection request count under the configured provider batching contract, and a safe translation-request range. Exact translation calls are unknowable before language detection because target-language messages require no translation request.
- `DATASET_ID=<month>` may be supplied to inspect one longitudinal month.
- Normal translated topic runs also log the same workload immediately before provider construction.

## 4. Safety / Methodology
No IF/WIF metrics, graph thresholds, Louvain behavior, LDA behavior/defaults, phrase behavior, community matching/evolution semantics, translation output semantics, GPT theme behavior, or original source messages change.

## 5. Validation
- Unit tests cover provider-free cache planning, side-effect-free empty-cache inspection, Azure detection batching/item-limit warning, and AWS detection batching.
- Existing translation/config/cache/default tests remain protected.
- `python -m compileall -q src tests` and `make validate-config PYTHON=python` remain required offline checks.

## 6. Progress Log
- 2026-08-21: Read mandatory repository contracts and Plan 075 before editing.
- 2026-08-21: Added provider-free translation workload planner and automatic pre-provider workload log.
- 2026-08-21: Added `translation-preflight` CLI/Make target that prepares exact LDA-bound community messages via network-only cached runs and makes no cloud translation/detection requests.
- 2026-08-21: Added offline unit coverage for cache reuse and provider request estimates.
- 2026-08-21: Plan 077 adds the optional `translation-detect` second step that spends only on language detection, caches results, and reports exact remaining translation requests.
