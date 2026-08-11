# Plan 046 — Unified Communities workspace

## Goal

Replace the separate **Community Network** and **Top Communities** frontend analytical pages with one period-aware **Communities** workspace. The workspace is a directory → selected-community master-detail flow keyed by `(run, period, metric, community_id)`. It preserves the current read-only analytical artifacts and does not move additional deep-dive content onto Overview.

## Source of truth

- `community-analysis-full-review-20260809-1812.zip`
- Archive SHA-256: `50f5ad245c7bf67a36b04b5a7efe27af55933133662ccbcd42be7ae30997bc36`
- HEAD recorded by the archive: `a7622c39291b50c36d78bbc1877d239cca630685`
- The archive includes the active Plan 045 working-tree changes; those are baseline state, not Plan 046 changes.

## Analytical non-goals

- No `shared_post` / IF or `weighted_post` / WIF changes.
- No graph-threshold, Louvain, centrality, LDA, HDBSCAN, canonical-theme, embedding, provider, or Community Evolution methodology changes.
- No request-time analytical recomputation.
- No API or artifact schema changes.
- No new per-community centrality metric.

## Required behavior

1. `/communities` is the canonical structural drill-down route.
2. `/network` and `/top-communities` redirect to `/communities` with query parameters preserved.
3. The canonical selected-community identity is `(run, period, metric, community_id)`; community IDs are explicitly month-local.
4. Direct `/communities` navigation resolves the latest canonical period and writes it to URL state.
5. Changing run, period, or IF/WIF clears a selected month-local community.
6. The first section is a paginated **Community Directory**, not a page-local “Top” ranking. Exact community ID selection works independently of the loaded page.
7. One selected community drives structural summary, published neighbor context, member interaction network, LDA evidence, downstream theme labels, and coverage/provenance.
8. `minWeight` filters only the selected member-network response and does not change the directory, community identity, LDA, or themes.
9. The old generic run-level centrality table is not carried into the workspace.
10. LDA evidence is presented before downstream generated themes.
11. Overview remains a concise monthly overview; structural deep links route into `/communities` with existing run/period/metric/community context.
12. The shared navigation rail follows Directory → Community Summary → Member Network → Topics & Themes → Provenance, with selection-dependent targets omitted until a community is selected.

## Implementation scope

Expected frontend changes are limited to:

- route and navigation consolidation;
- a new `Communities` page;
- a period-aware Communities read hook;
- a directory component;
- reuse of existing selected-community graph/enrichment helpers;
- removal of obsolete page-only Community Network / Top Communities components after reference scanning;
- structural deep-link updates;
- focused frontend tests/E2E/docs.

Backend `src/`, configs, dependency files, and analytical contracts must remain unchanged.

## Validation plan

Focused checks:

- Communities workspace hook request/query-key scope and partition reset.
- Communities page directory, selected-community master-detail, LDA-before-theme order, min-weight copy, and thematic deep link.
- Sidebar/Methodology/Overview/Data Explorer/Thematic structural links.
- Legacy route redirects and query-state preservation.
- Accessibility and visual route updates.
- `git diff --check`.

Repository gates to attempt:

- `make format`
- `make lint`
- `make test`
- `make frontend-check`
- focused Vitest/Playwright checks

Environment blockers are reported exactly and are never represented as passing.

## Progress log

### 2026-08-09 — Plan / inspect

- Verified the 18:12 archive manifest and treated the complete extracted working tree, including Plan 045 changes, as the patch baseline.
- Read the required harness, architecture, feature/product/data/database/metric/pipeline/theme/quality/test documentation and the relevant Overview/community/frontend execution plans before editing.
- Confirmed the legacy Community Network and Top Communities hooks omitted `period`, despite month-local community IDs and period-aware backend reads.
- Confirmed Overview already preserves `period`, `metric`, and `community` when deep-linking, while the legacy Network route ignored that period context.
- Confirmed the legacy Network page mixed whole-run network/centrality views with selected-community data and the Top Communities page offered page-local sorting under a global-sounding name.

### 2026-08-09 — Protect / implement

- Added a period-aware Communities workspace hook that scopes directory, selected-community detail/member graph, community-map context, matched LDA, and theme reads to the selected canonical month.
- Added latest-period URL resolution and partition-change clearing for month-local community identity.
- Replaced the two primary analytical routes with `/communities`; kept `/network` and `/top-communities` as query-preserving compatibility redirects.
- Added a paginated Community Directory with exact-ID navigation and removed page-local rank semantics.
- Added one selected-community master-detail flow: structural summary, strongest published neighbors, member graph, LDA-before-theme preview, and graph coverage/provenance.
- Kept `minWeight` scoped to the selected member-graph request only and documented that it does not alter Louvain/community membership or semantic artifacts.
- Removed obsolete page-only Community Network / Top Communities components, hooks, tables, and their superseded unit tests after reference scanning.
- Updated Overview inspector, Overview table, Thematic Analysis, Data Explorer, Methodology, Sidebar, Topbar, route baselines, and E2E route expectations to use the unified Communities destination.
- Confirmed no analytical/backend/API/config implementation change was required.

### 2026-08-09 — Validate

- Verified the source ZIP SHA-256 is `50f5ad245c7bf67a36b04b5a7efe27af55933133662ccbcd42be7ae30997bc36`.
- Parsed/transpiled all 21 changed frontend JS/TS/JSX/TSX files with TypeScript 5.8.3: no syntax/transpile diagnostics.
- Ran focused static contract assertions confirming every Communities directory/detail/community-map/topic/theme read is period-scoped, the selected detail is min-weight scoped, legacy routes redirect to `/communities`, no generic centrality read is used, and LDA evidence precedes downstream themes.
- Byte-compared protected analytical scope against the 18:12 baseline: `src/`, `configs/`, `pyproject.toml`, `uv.lock`, `Makefile`, and `.env.example` are unchanged.
- Changed-file scan found no `/Users/...` absolute paths, OpenAI-style secret strings, or populated `OPENAI_API_KEY` assignments.
- `git diff --check` passed on the task delta.
- `npm ci --ignore-scripts --no-audit --no-fund` was attempted but the configured package registry returned 404 for `yargs-parser-21.1.1.tgz`; frontend dependencies could not be installed.
- `make format` was attempted in an isolated validation copy and was blocked because `.venv/bin/python` is absent from the archive.
- `make lint` was attempted and blocked during `uv` dependency resolution because `mlflow-skinny==3.14.0` is unavailable from the configured registry.
- `make test` was attempted and blocked because `setuptools>=61.0` could not be resolved from the configured registry.
- `make frontend-check` was attempted and stopped at TypeScript startup because the intentionally omitted `node_modules` leaves `@testing-library/jest-dom`, `vite/client`, and `vitest/globals` type definitions unavailable.
- Final patch applicability is verified separately against a second pristine extraction of the exact 18:12 snapshot before handoff.
