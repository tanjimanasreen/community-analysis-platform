# Plan 033 — Period-aware Overview dashboard

## Goal

Correct the Overview page's mixed monthly/run-level presentation, add URL-backed
monthly navigation, render one canonical community graph per selected month,
and make run configuration and provenance readable and responsive. This plan is
limited to read models, Overview presentation, focused tests, and documentation.
It does not change analytical metrics, pipeline outputs, algorithm defaults, or
artifact categories.

## Source of truth

- `community-analysis-frontend-review-20260728-0840.zip`
- `dashboard-reproduction-739866ba-8f59-4784-a083-d64888b24ffd.tar.gz.part-000`
- Completed run `739866ba-8f59-4784-a083-d64888b24ffd`
- Run manifest with 93 canonical artifacts and monthly snapshots for
  January–April 2017.

## Current behavior and defects

- The Overview response exposed latest-month users, messages, and communities
  beside a whole-run network-row total without identifying the different scopes.
- The Overview graph merged monthly graph samples, although community IDs are
  month-local and should not imply longitudinal identity.
- Month selection was unavailable and could not be restored from a URL.
- Run Configuration and Run Provenance were weakly structured and wrapped long
  identifiers poorly.
- The Overview feature still loaded compatible-run history that was no longer
  displayed, producing unnecessary API requests.

## Tasklist

### 1. Protect and document current scope

- [x] Verify the reproduction run's monthly artifact-key conventions.
- [x] Add tests for canonical period discovery and exact artifact selection.
- [x] Add tests proving monthly values remain separate from whole-run values.
- [x] Preserve backward-compatible scalar Overview fields for other routes.

### 2. Add period-aware API read models

- [x] Add canonical `YYYY-MM` period parsing and discovery.
- [x] Add `available_periods`, monthly `periods`, and `run_summary` to Overview.
- [x] Read exact monthly count, match-summary, and network-row metadata.
- [x] Return `null` for missing optional monthly values instead of fabricating zero.
- [x] Expose only allowlisted analytical configuration metadata.
- [x] Infer the run date window from available periods when manifest dates are absent.

### 3. Add exact monthly network selection

- [x] Add optional validated `period` parameters to network and community routes.
- [x] Select exact sample, summary, node-index, and graph artifacts for IF/WIF.
- [x] Reject unknown periods with `INVALID_FILTER` and available-period guidance.
- [x] Retain no-period behavior for backward compatibility.
- [x] Reject ambiguous unsuffixed artifacts for multi-month period requests.

### 4. Rebuild Overview period and metric presentation

- [x] Add URL-backed month selection with latest-month default.
- [x] Add previous, next, direct selection, and opt-in autoplay.
- [x] Pause autoplay for graph interaction, hidden tabs, and reduced motion.
- [x] Replace oversized cards with four compact monthly cards and mini trends.
- [x] Add an explicit longitudinal summary strip.
- [x] Add a monthly trends chart with an exact-value table.
- [x] Remove unused compatible-run Overview fan-out requests.

### 5. Make the graph and metadata panels period-aware

- [x] Query and remount the graph by run, metric, and selected period.
- [x] Prefetch adjacent monthly graph responses.
- [x] Label community IDs and colors as month-local.
- [x] Group safe configuration by analysis stage.
- [x] Group provenance by identity, execution, code, and dataset lineage.
- [x] Add readable UTC timestamps, durations, shortened hashes, and copy controls.

### 6. Responsive behavior and validation

- [x] Add desktop, tablet, and mobile layouts for cards, month controls, summaries,
      configuration, and provenance.
- [x] Add focused backend service and frontend component tests.
- [x] Update the Overview Playwright shell assertions for period-aware rendering.
- [x] Compile all Python files and syntactically transpile frontend source.
- [ ] Run the full Python suite in a dependency-complete environment with PyArrow.
- [ ] Run frontend typecheck, lint, tests, build, and bundle checks after a successful
      frozen npm install.
- [ ] Run the Overview Playwright workflow in a browser-capable environment.

## Acceptance criteria

- Monthly and run-level metrics are visually and structurally separate.
- The latest available month is selected by default and stored in `period`.
- KPI cards, trends, community table, themes, and graph follow the selected month.
- The graph reads only the requested month's canonical artifacts for IF or WIF.
- Invalid periods fail explicitly; missing optional metrics remain unavailable.
- Community colors are documented as month-local.
- Configuration and provenance are responsive, readable, and redact unsafe paths.
- No `shared_post`, `weighted_post`, graph threshold, Louvain, or LDA behavior changes.

## Validation log

| Date | Command/check | Result |
|---|---|---|
| 2026-07-28 | `python -m pytest -q tests/unit/test_api_periods.py tests/unit/test_overview_monthly_services.py` | Passed: 6 tests. |
| 2026-07-28 | `python -m compileall -q src tests` | Passed. |
| 2026-07-28 | TypeScript `transpileModule` syntax pass across `frontend/src` and `frontend/tests/e2e` | Passed for 133 source files. |
| 2026-07-28 | `python -m pytest -q tests/unit/test_backend_api.py` | Blocked: 14 Parquet-backed tests could not create fixtures because PyArrow/FastParquet is absent; 2 non-Parquet tests passed. |
| 2026-07-28 | `npm ci --ignore-scripts --no-audit --no-fund` | Blocked: internal npm package gateway repeatedly returned HTTP 503, leaving dependencies incomplete. |
| 2026-07-28 | `npm run typecheck` | Blocked by the incomplete npm install; Vite/Vitest/testing-library type packages were unavailable. |
| 2026-07-28 | `python -m pytest -q tests/unit/test_network_dashboard_sample.py tests/unit/test_network_guard.py` | Passed: 7 existing network regression tests. |
| 2026-07-28 | Reproduction manifest period/artifact mapping and network-row total check | Passed: January–April mappings and 5,165,736 run interaction records verified. |
| 2026-07-28 | `git diff --check` | Passed. |
| 2026-09-09 | `python -m pytest tests/unit/test_overview_monthly_services.py` | Passed: 11 tests (including slice usage and empty artifact regressions). |

## Progress log

| Date | Update |
|---|---|
| 2026-07-28 | Read the required architecture, product, data, metric, pipeline, theme, quality, test, and active-plan documentation before editing. |
| 2026-07-28 | Confirmed the mixed-scope defect and the January–April artifact mapping in the supplied completed run. |
| 2026-07-28 | Added period-aware Overview/network read models, responsive monthly controls/cards/trends, month-specific graph queries, grouped configuration/provenance, and focused regression tests. |
| 2026-07-28 | Kept legacy Overview scalar fields for existing comparison/evolution routes while making the new monthly/run-level contract explicit. |
| 2026-09-09 | Replaced full Parquet reads (`read_parquet_record`) in `_period_counts` and `_period_community_counts` with single-row slice reads (`read_parquet_record_slice` with `offset=rows - 1, limit=1`) via private helper `_final_row`, eliminating full S3 Parquet scans per month while preserving exact values, normalization, and empty artifact handling. |

## Rollback

Revert this plan's patch as one unit. The analytical run artifacts require no
rollback because they are read-only and unchanged. Do not restore cross-month
graph merging on the Overview page or relabel run-level values as monthly values.
