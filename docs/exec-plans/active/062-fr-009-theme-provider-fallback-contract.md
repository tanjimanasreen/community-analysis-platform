# Plan 062: FR-009 Theme Provider Fallback Contract

Status: complete

Owner: agent

Last updated: 2026-08-12

## Goal

Eliminate the remaining silent-ignore path for thesis-era/provider-routing settings
placed under `theme`. Current runtime routing already reads `theme_provider`; this
plan hardens validation so obsolete `theme.fallback` and `theme.fallback_chain`
keys fail clearly instead of appearing to work.

## Confirmed Baseline

- Checked-in production/evolution configs use `theme_provider.fallback`.
- Runtime provider construction reads `theme_provider.primary`, `fallback`, and
  `fallback_chain`.
- `validate_run_config` accepted `theme.fallback` / `theme.fallback_chain` even
  though runtime ignored them.
- One current evolution config retained a commented obsolete `theme:` fallback
  example.

## Non-Goals

- Do not change provider selection, fallback order, caching, retries, or models.
- Do not remove the analytical `theme` namespace.
- Do not make live provider calls in tests.
- Do not change LDA, IF/WIF, Louvain, evolution, database, or artifact behavior.

## Implementation

- [x] Add centralized run-config validation rejecting provider-routing keys under
  `theme` with a migration message pointing to `theme_provider`.
- [x] Preserve canonical `theme_provider` settings and analytical `theme` options.
- [x] Remove the stale commented fallback example from the retweet/quote evolution
  config.
- [x] Add focused config tests for canonical, stale, and analytical-theme cases.
- [x] Reuse existing mock-only provider factory coverage for fallback on/off behavior.
- [x] Update the current theme contract, feature inventory, quality gate, and test
  matrix.

## Validation

```bash
python -m pytest tests/unit/test_config.py -q
python -m pytest tests/unit/test_provider_factory.py -k "fallback_false or fallback_true" -q
python -m compileall -q src tests
git diff --check
```

Broader repository gates should also be attempted when the locked environment and
dependencies are available. Environment blockers must be reported separately.

## Acceptance Criteria

- `theme_provider.fallback` and `theme_provider.fallback_chain` remain valid.
- `theme.fallback` and `theme.fallback_chain` fail with a clear migration message.
- Existing analytical `theme` settings continue to validate.
- Provider factory behavior is unchanged and tested offline.
- Current live configs/comments no longer advertise the obsolete namespace.
- No analytical defaults or metrics change.

## Progress Log

| Date | Update |
|---|---|
| 2026-08-12 | Created Plan 062 and implemented the scoped FR-009 contract hardening. |
| 2026-08-12 | Focused validation passed: `tests/unit/test_config.py` (14), provider fallback on/off subset (3), protected defaults (5), IF/WIF/graph thresholds (4), all current evolution configs plus the sample config validated, compileall passed, and live config scan found no stale provider-routing keys under `theme`. |
| 2026-08-12 | Broader locked gates were attempted but dependency installation is blocked by sandbox DNS; `make format` is blocked because Black is absent from the partially created `.venv`. Full `test_provider_factory.py` retains the pre-existing `CachedProvider.cache_size` assertion failure, reproduced before FR-009 and outside this change. |
| 2026-08-12 | Follow-up: the pre-existing provider-factory cache assertion was reconciled separately by Plan 063 against the current `run_metrics` and ordered-keyword contracts; FR-009 provider-routing behavior remains unchanged. |
