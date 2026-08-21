# Plan 063 — Provider Factory Cache Contract Test Reconciliation

Status: complete

Owner: agent

Last updated: 2026-08-12

## Goal

Remove the remaining stale provider-factory test dependency on the retired
`CachedProvider.cache_size` attribute and exercise the current ordered-keyword and
cache-metrics contracts without changing production caching behavior.

## Confirmed Baseline

- `tests/unit/test_provider_factory.py` reproduced one failure because
  `CachedProvider` no longer exposes `cache_size`.
- `CachedProvider.generate_theme()` accepts `list[str]`, while three factory tests
  still passed scalar strings from an older provider interface.
- The current observable cache contract is `CachedProvider.run_metrics`, including
  `cache_hits`, `cache_misses`, `cache_writes`, and `cache_errors`.
- `tests/unit/test_theme_cache.py` already covers deeper cache semantics including
  keyword-order sensitivity, SQLite reuse, model invalidation, and invalid-response
  handling.

## Non-Goals

- Do not add a `cache_size` compatibility property.
- Do not change memory, SQLite, or disabled cache backends.
- Do not change cache-key construction, provider routing, retries, models, or theme
  generation behavior.
- Do not make live provider calls in tests.
- Do not change analytical metrics, thresholds, LDA, Louvain, evolution, database,
  or artifact behavior.

## Implementation

- [x] Replace the stale `cache_size` assertion with assertions on current cache
      hit/miss/write metrics.
- [x] Update provider-factory theme-generation calls to the current ordered
      `list[str]` API.
- [x] Preserve the dedicated cache tests as the detailed cache-behavior authority.
- [x] Run focused provider/cache validation and available broader gates.
- [x] Generate and verify a task-only patch against a second pristine extraction.

## Validation

```bash
python -m pytest tests/unit/test_provider_factory.py tests/unit/test_theme_cache.py -q
python -m pytest tests/unit/test_theme_pipeline.py tests/unit/test_release_hygiene.py -q
python -m compileall -q src tests
git diff --check
```

Repository gates should also be attempted where the locked environment permits:

```bash
make test-unit
make test
make lint
make format
```

Environment/dependency blockers are reported separately rather than hidden by
restoring obsolete cache behavior.

## Acceptance Criteria

- `tests/unit/test_provider_factory.py` does not reference `cache_size`.
- Factory tests pass ordered keyword lists to `generate_theme()`.
- Two identical ordered keyword requests produce one miss, one write, and one hit.
- Production provider/cache source remains unchanged.
- Dedicated cache tests remain green and no live provider calls occur.

## Progress Log

| Date | Update |
|---|---|
| 2026-08-12 | Verified the 14:04 source archive checksum against the supplied manifest, read the required contracts and active plans, and reproduced the baseline provider-factory failure: 6 tests passed and only the stale `CachedProvider.cache_size` assertion failed. Dedicated cache tests were already 4/4 green. |
| 2026-08-12 | Reconciled the provider-factory tests with the current ordered-keyword API and `run_metrics` cache observability contract. No production source was changed. |
| 2026-08-12 | Focused provider/cache validation passed 11/11 (`test_provider_factory.py` + `test_theme_cache.py`); release hygiene and protected-default checks passed 13/13; `python -m compileall -q src tests` passed. The related theme-pipeline selection has one environment blocker because this review interpreter lacks `pyarrow`/`fastparquet`, both outside this test-only change and with `pyarrow` already declared in `pyproject.toml`. |
| 2026-08-12 | Locked gates were attempted: `make test-unit` was blocked by sandbox DNS while downloading `matplotlib`; `make test` was blocked resolving `setuptools`; `make lint` was blocked downloading `pytz`; `make format` could not run because the partially created `.venv` lacked Black. No blocked gate is claimed as passed. |
