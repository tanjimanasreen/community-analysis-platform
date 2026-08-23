# Plan 074 — Cross-Run Stage Artifact Reuse

## 1. Objective
Make repeated Telegram and Twitter analytical runs reuse prior deterministic stage outputs when the effective inputs, relevant configuration, implementation code, and stage contract are unchanged. A new pipeline run must retain its own run ID and self-contained run bundle, but run identity must not force network/community, topic/LDA, or theme/evolution recomputation.

This plan is orchestration-only. It does not add multilingual translation; translation/provider work will be a separate plan that can later use the same cache contract.

## 2. Source Snapshot
- Archive: `community-analysis-full-review-20260820-2222.zip`
- SHA-256: `f94990bdbbb8d3dbec28c8cdfa541d02bdbcdd4b648acb56cc7094b7b1d42d7a`
- Branch: `feature/frontend-ui-upgrade`
- HEAD: `5b60f1f645b0ac47385fbefcb571c7dfc8124efe`
- Working tree in supplied snapshot: clean.

## 3. Current Problem
The stage-specific Prefect cache-key helpers currently append `PipelineRunContext.pipeline_run_id`. Because every execution receives a new UUID, equivalent runs cannot reuse stage results across runs. The task decorators also hard-code a 30-day Prefect result-cache lifetime while YAML exposes `orchestration.cache_expiration_days`, so the visible configuration is not authoritative.

Simply removing the run ID from Prefect result keys is unsafe: cached task results contain `ArtifactReference` paths inside an older run directory. A later run would receive stale-path references before artifact existence/integrity can be checked, and downstream stage validation requires current-run-contained inputs.

## 4. Approved Design
Introduce an explicit content-addressed stage artifact cache under the configured output root:

```text
<output_base_path>/.stage_cache/v1/<stage>/<stage_cache_key>/
```

Each cache entry contains immutable copied stage files plus a small manifest with relative run paths, SHA-256, byte size, media type, row count, and asset key. Reuse restores validated bytes into the new run directory before returning `ArtifactReference` values, so downstream validation and final run-manifest publication continue to operate on the current run only.

The cache key is:

```text
stage
+ stage semantic/cache-contract version
+ input artifact/dataset hashes
+ relevant configuration subset
+ stage code fingerprint
```

`pipeline_run_id`, Prefect flow-run ID, output paths, tracking metadata, and unrelated settings are excluded from computational identity.

## 5. Code-Change Invalidation
A deterministic stage code fingerprint hashes the code/resources that can affect that stage. Stage dependency scopes are intentionally conservative:

- network/community: network/community/ingestion implementation plus the network/community pipeline boundary;
- topic/LDA: topic implementation/resources plus the topic pipeline boundary;
- theme/evolution: theme/provider/visualization implementation and prompt/resources plus the theme pipeline boundary.

A changed dependency therefore produces a new cache key. Unrelated frontend/docs changes do not invalidate analytical stage entries. Shared analytical modules may conservatively invalidate more than one stage rather than risk stale reuse.

Explicit stage semantic versions remain in the cache key as an auditable manual contract boundary in addition to automatic code fingerprints.

## 6. Runtime Behavior
For each stage:

1. Build the deterministic stage key.
2. If `orchestration.artifact_reuse` is true (default), validate the matching cache entry.
3. On a valid hit, restore all stage files into the current run root and skip domain execution.
4. On a missing/invalid entry, execute the unchanged domain stage, collect its artifacts, and atomically snapshot them into the cache.
5. Complete the current run bundle normally; every run still owns a distinct immutable manifest and canonical artifact copies.

Corrupt/incomplete cache entries are treated as misses and recomputed. Cache bytes never bypass checksum validation.

Prefect task-result caching is no longer used as the cross-run artifact reuse mechanism; task results remain persisted for orchestration observability. This avoids cached references to deleted/older run directories.

## 7. Protected Contracts
Do not change:
- `shared_post`, `total_post`, or `weighted_post` definitions;
- graph thresholds (`min_total_post=10`, `min_shared_post=5`);
- Louvain defaults (`resolution=1`, `seed=123`);
- approved LDA implementation/defaults or unigram/bigram behavior;
- Telegram/Twitter input normalization, relationship mapping, or date-column semantics;
- community matching, transition, path, or membership semantics;
- theme Prompt V3/index contract, provider safety behavior, fallback routing, embeddings, HDBSCAN, or analytical output schemas;
- Memgraph/database behavior;
- frontend behavior.

## 8. Files Expected To Change
Production:
- `src/orchestration/hashing.py`
- `src/orchestration/stage_cache.py` (new)
- `src/orchestration/tasks.py`
- `src/orchestration/composition_flow.py` (semantic-version metadata only)
- `src/config/loader.py`
- canonical Telegram/Twitter evolution YAMLs

Tests:
- `tests/unit/test_orchestration_hashing.py`
- `tests/unit/test_orchestration_topic_tasks.py`
- `tests/unit/test_stage_artifact_cache.py` (new)
- config/default tests as required

Docs:
- architecture/pipeline/output/cache verification contracts
- this plan; Plan 067 receives a historical supersession note if needed.

## 9. Validation
Focused offline tests first:

```bash
python -m pytest -q \
  tests/unit/test_orchestration_hashing.py \
  tests/unit/test_stage_artifact_cache.py \
  tests/unit/test_current_defaults.py \
  tests/unit/test_graph_thresholds.py \
  tests/unit/test_louvain_defaults.py
```

Where Prefect/Parquet dependencies are available:

```bash
python -m pytest -q \
  tests/unit/test_orchestration_tasks.py \
  tests/unit/test_orchestration_topic_tasks.py \
  tests/unit/test_orchestration_theme_tasks.py \
  tests/unit/test_orchestration_monthly_flow.py \
  tests/integration/test_orchestration_smoke.py
```

Repository gates:

```bash
python -m compileall -q src tests
make validate-config PYTHON=python
make format PYTHON=python
make lint
make test
```

Environment/dependency blockers are recorded and must not be bypassed by altering production behavior.

## 10. Acceptance Criteria
- Equivalent runs with different run IDs produce identical stage keys.
- Relevant input/config/code changes produce different stage keys.
- A valid cached stage is restored into the new run root without domain recomputation.
- A tampered/incomplete cache entry is rejected and treated as a miss.
- Final run artifacts remain current-run-contained and compatible with existing manifest validation.
- Telegram and both Twitter evolution configs use the same reuse mechanism.
- Cache retention is content/version driven rather than an ineffective hard-coded 30-day Prefect TTL.
- Protected analytical defaults/metrics are byte/behavior unchanged.
- No test performs live provider calls.

## 11. Progress Log
- 2026-08-20: Verified the supplied source snapshot metadata and clean-tree manifest.
- 2026-08-20: Read mandatory repository contracts, output-artifact contract, Plan 067, and relevant lineage/cache plans before editing.
- 2026-08-20: Reproduced the current cache-key behavior in source: all network/topic/theme keys append `pipeline_run_id`; task decorators hard-code 30-day Prefect cache expiration while YAML exposes the unused `cache_expiration_days` setting.
- 2026-08-20: Baseline hashing/protected-default selection passed before implementation.
- 2026-08-20: Implemented stage-scoped code/runtime fingerprints and run-independent network/topic/theme computation keys; `pipeline_run_id` is no longer part of cache identity.
- 2026-08-20: Added the internal `.stage_cache/v1` store with atomic publication, checksum/size validation, corruption-as-miss behavior, and restore into the current run root.
- 2026-08-20: Integrated cache restore/store around the unchanged network/community, topic, and theme/evolution domain stages; Prefect result persistence remains enabled without cross-run Prefect cache keys.
- 2026-08-20: Replaced the unused/hard-coded 30-day cache setting with `orchestration.artifact_reuse` (default `true`) in the canonical Telegram forwarded-message, Twitter retweet/quote, and Twitter reply evolution configs.
- 2026-08-20: Added regression coverage for run-ID independence, dependency/code fingerprints, immutable restore, tamper rejection, and configuration validation; focused hashing/cache/config/default tests passed.
- 2026-08-20: Hardened cache identity so topic input roles and theme period→artifact mappings cannot collide; topic routing fields participate because they determine run-relative output paths. Selected provider generation settings and embedding model revisions participate in the theme key, while operational provider throttling/timeout settings do not.
- 2026-08-20: Focused/protected offline selection passed: 84 tests across orchestration hashing/cache/config, IF/WIF metrics, protected defaults, theme safety recovery, provider factory, and transitions. `python -m compileall -q src tests`, `make validate-config PYTHON=python`, and all three canonical Telegram/Twitter evolution config validations passed.
- 2026-08-20: Review-only Prefect stub outside the repository verified the topic task has no Prefect cross-run cache key, topic/theme bundle flatten→restore helpers round-trip, and a network cache hit restores current-run bytes while skipping a missing input/domain execution path.
- 2026-08-20: Stage-code fingerprint probe verified a topic-code change invalidates the topic fingerprint while leaving the network fingerprint unchanged.
- 2026-08-20: Optional orchestration integration collection is environment-blocked by missing Prefect; `make run-evolution-pipeline-test PYTHON=python` is blocked by missing `pyarrow`/`fastparquet`; `make format` is blocked by missing Black; `make lint` and `make test` are blocked by offline dependency resolution. Production behavior was not changed to bypass these environment limitations.
- 2026-08-20: Fresh-extraction verification passed: the task-only patch applied cleanly to the exact supplied ZIP; all 21 affected files byte-matched the implementation workspace; the same 84 focused/protected tests, `compileall`, and config validation passed on the independently patch-applied copy.
- 2026-08-21: Plan 075 reused the stage-cache contract: translation analytical identity now participates in the topic key, and translation provenance is restored/published with topic artifacts. Plan 074 network/theme semantics remain unchanged.
