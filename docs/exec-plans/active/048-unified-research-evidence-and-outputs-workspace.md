# Plan 048 — Unified Research Evidence & Outputs Workspace

Status: implementation in progress

Owner: agent

Last updated: 2026-08-10

## Goal

Replace the separate **Data Explorer** and **Reports** frontend pages with one canonical `/evidence` workspace titled **Research Evidence & Outputs**. The workspace keeps the existing read-only artifact/API boundary while organizing persisted records around the thesis dimensions:

- Structural · RQ1
- Semantic · RQ2
- Temporal · RQ3 / RQ4
- Run Outputs · provenance and published artifacts

The page is an evidence/provenance browser, not another analytical dashboard.

## Source of truth

- `community-analysis-full-review-20260810-0256.zip`
- Archive SHA-256: `704ad94a0801c87b835c452f4ca6b00b9f9025f0ce0e36cf992a2ac1f64a5ac4`
- HEAD recorded by the archive: `a7622c39291b50c36d78bbc1877d239cca630685`
- The archive includes active Plans 045–047 working-tree changes; those are baseline state, not Plan 048 changes.

## Analytical non-goals

- No `shared_post` / IF or `weighted_post` / WIF changes.
- No graph-threshold, Louvain, centrality, LDA, topic matching, HDBSCAN, theme, embedding, provider, or Community Evolution methodology changes.
- No request-time analytical recomputation.
- No backend/API/artifact schema changes.
- No new report-generation logic.
- No OpenAI calls.

## Required behavior

1. `/evidence` is the canonical evidence/provenance route; `/data` and `/reports` remain query-preserving compatibility redirects.
2. The evidence view is URL-backed through `view=` and defaults to `communities`.
3. Evidence navigation is grouped by thesis dimension rather than API/table implementation names.
4. Month-local evidence resolves canonical periods from the Overview read model and writes the latest valid month to URL state when needed.
5. Communities are scoped by `(run, period, metric)`; community deep links preserve `(run, period, metric, community_id)`.
6. Centrality uses the existing period/metric-aware centrality-leaders read model rather than the generic raw centrality artifact table.
7. Matched LDA, partial-match LDA, and generated themes are explicitly period-scoped; Exact Community ID remains a server-side filter.
8. Transitions remain longitudinal and do not acquire a single-month or affinity filter.
9. The global Topbar affinity selector is hidden on `/evidence`; a local Affinity control appears only for Communities and Centrality.
10. The current Reports manifest filtering, verified inline-report link, manifest-key downloads, and intermediate-download suppression move into the **Artifacts & Reports** evidence view.
11. Analytical evidence retains a full safe normalized-record inspector while summary tables favor constructive research-facing columns.
12. Contextual links route evidence to Communities, Thematic Analysis, Community Evolution, Overview, or Run History without duplicating those dashboards.
13. Existing report artifacts remain already-produced outputs; Plan 048 does not claim or construct a thesis report.

## Implementation scope

Expected frontend-only changes:

- add `/evidence` page and `features/evidence/` feature boundary;
- replace Data Explorer/Reports primary navigation with Evidence;
- preserve `/data` and `/reports` compatibility redirects;
- add period-aware evidence queries and truthful affinity scoping;
- reuse the existing manifest artifact-library helpers;
- retire obsolete Data Explorer/Reports page-only code after reference scanning;
- update Methodology artifact-library link and route documentation;
- add focused frontend unit/E2E/docs coverage.

Backend `src/`, configs, dependency files, analytical contracts, and artifact schemas must remain unchanged.

## Tests

- evidence-view parsing/grouping and constructive columns;
- latest-period/default URL resolution;
- communities/centrality request scope includes period + metric;
- matched/partial LDA/themes request scope includes period and optional exact community ID;
- transitions/outputs do not acquire inappropriate period/metric query parameters;
- local Affinity control exists only for applicable views;
- month-local community deep links preserve period and metric;
- report URL and manifest-key download behavior remain unchanged;
- intermediate artifacts remain visible but non-downloadable;
- `/data` and `/reports` redirect to `/evidence` with query state preserved;
- Sidebar/Topbar/Methodology links use the unified route;
- accessibility/visual routes use Evidence instead of separate Data Explorer and Reports pages.

## Validation plan

Focused checks:

- `git diff --check`
- focused evidence model/hook/page/artifact-library tests
- route/reference scans for retired pages and legacy links
- TypeScript/JSX parser validation
- protected-scope byte comparison

Repository gates to attempt:

- `make format`
- `make lint`
- `make test`
- `make frontend-check`
- focused Vitest/Playwright checks

Environment blockers are reported exactly and are never represented as passing.

## Progress log

### 2026-08-10 — Plan / inspect

- Verified the 02:56 source ZIP SHA-256 matches the supplied manifest.
- Read the required harness, architecture, feature/product/data/database/metric/pipeline/theme contracts, quality gates, test matrix, and the relevant artifact/API/Data Explorer/Reports/Communities/Methodology execution plans before editing.
- Confirmed Data Explorer currently omits `period` for communities, matched/partial LDA, and themes despite month-local community identity.
- Confirmed its global metric copy is misleading for modes that expose paired IF/WIF or longitudinal/run-level evidence.
- Confirmed Reports and Data Explorer artifact modes duplicate manifest browsing/download responsibilities.
- Confirmed the existing `/centrality-leaders` endpoint provides a more constructive period/metric-aware centrality evidence read model without request-time recomputation.

### 2026-08-10 — Protect / implement

- Added the canonical `/evidence` route and query-preserving `/data` → `view=communities` and `/reports` → `view=outputs` compatibility redirects.
- Replaced the two primary sidebar destinations with one **Evidence** destination and hid the global Topbar affinity selector on the unified evidence surface.
- Added a thesis-oriented evidence feature boundary with Structural (RQ1), Semantic (RQ2), Temporal (RQ3/RQ4), and Run Outputs navigation.
- Made Communities and Centrality period/metric-aware; Centrality now consumes the existing persisted `/centrality-leaders` read model rather than the generic raw centrality table.
- Made matched LDA, partial-match LDA, and generated-theme reads period-aware with the existing exact community filter, without adding a false single-affinity parameter.
- Kept transitions longitudinal and outputs run-scoped.
- Merged Reports behavior into **Artifacts & Reports**, preserving manifest filters, verification state, inline report access, manifest-key downloads, and intermediate-artifact suppression.
- Preserved the safe full-record inspector and added context-preserving links back to Communities, Overview, Thematic Analysis, Community Evolution, and Run History.
- Removed superseded Data Explorer / Reports page-only code after reference scanning confirmed no remaining callers.
- Updated current route, handoff, demo, product-spec, test-matrix, baseline, and Methodology output-link documentation without changing historical analytical plans.

### 2026-08-10 — Validation

- `git diff --cached --check`: passed.
- TypeScript `transpileModule` parser check over all changed/new JS/JSX/TS/TSX files: passed (22 files, 0 syntax errors).
- Isolated TypeScript compile/runtime assertions for `evidenceModel.ts`, `communityIds.ts`, and API types: passed.
- Retired-reference scan for `DataExplorer`, `ReportsPage`, `useExplorerData`, `explorerModel`, and `useArtifactLibrary`: passed with no remaining frontend callers.
- Protected-scope byte comparison for `src/`, `configs/`, `pyproject.toml`, `uv.lock`, `Makefile`, and `.env.example`: passed; all are unchanged from the 02:56 source snapshot.
- Changed-line secret/local-machine-path scan: passed.
- `make frontend-typecheck`: blocked because the source archive intentionally excludes `node_modules`; TypeScript cannot resolve `@testing-library/jest-dom`, `vite/client`, or `vitest/globals`.
- `make frontend-lint`: blocked because `oxlint` is not installed.
- `make frontend-test`: blocked because `vitest` is not installed.
- `make frontend-check`: blocked at the same missing frontend type definitions.
- `npm ci --ignore-scripts --no-audit --no-fund`: attempted to restore frontend dependencies, but the configured internal npm registry returns HTTP 404 for `yargs-parser@21.1.1`.
- `make format`: blocked because the environment-created `.venv` does not contain `black`.
- `make lint`: blocked during `uv` dependency resolution because the configured package registry does not provide `mlflow-skinny==3.14.0`.
- `make test`: blocked during build-system resolution because the configured package registry does not provide `setuptools>=61.0`.

Final patch applicability and clean-snapshot byte comparison are recorded in the external validation report produced with the patch.
### 2026-08-10 — Post-apply layout hardening

- Investigated the applied `/evidence` workspace against the 05:15 source snapshot and the supplied desktop screenshot.
- Confirmed analytical/query behavior remains correct; the visible misalignment came from Evidence-only side panels using `top-24` sticky offsets while the shared dashboard scroll viewport already sits below the Topbar.
- Aligned the navigator and record-details panels to the shared in-content sticky convention (`top-4`) and bounded the populated details panel to the available dynamic viewport height.
- Removed duplicated Run History and Run Outputs chrome from the outputs body because the Evidence context header already owns the destination and section identity.
- Reduced common-width artifact-table pressure by showing category/media-type columns only at 2XL; their complete values remain available in the artifact metadata inspector.
- Kept Evidence naming unchanged pending product naming alignment; this hardening pass is layout/presentation only.

### 2026-08-10 — Post-apply horizontal evidence navigation

- Replaced the permanent left Evidence navigator with a full-width, two-level horizontal control: thesis dimension first, evidence type second.
- Kept the existing URL-backed `view=` contract unchanged; choosing a dimension resolves to that dimension's first evidence view, while the second row exposes only the active dimension's evidence types.
- Moved Exact Community ID filtering into the same horizontal navigation surface for the LDA/theme views where the server-side filter actually applies.
- Reclaimed the former navigator width for the evidence table and reduced the body to a two-column records/details layout on wide screens.
- Preserved all period, affinity, artifact, report, and normalized-record behavior; this refinement is presentation/navigation only.
- Updated unit/E2E expectations to protect the two-level navigation semantics and active-view behavior.

### 2026-08-10 — Horizontal navigation validation

- `git diff --check`: passed.
- TypeScript `transpileModule` syntax checks passed for the changed Evidence component/page/unit/E2E sources.
- Static layout assertions confirmed the navigator is full-width, the body is records/details only at `xl`, and the old three-column sidebar layout is absent.
- Protected analytical/configuration scope scan passed; no `src/`, `configs/`, dependency, Makefile, or environment-example files changed.
- `make frontend-typecheck`, `make frontend-lint`, `make frontend-test`, and `make frontend-check` remain environment-blocked because the archive excludes frontend dependencies (`vite/client`, `vitest/globals`, `@testing-library/jest-dom`, `oxlint`, and `vitest` are unavailable).
- `make lint` remains blocked by the configured registry not providing `mlflow-skinny==3.14.0`; `make test` remains blocked by the configured registry not providing `setuptools>=61.0`.

### 2026-08-10 — Plan 051 naming/route refinement

- The user-facing workspace is renamed **Research Data & Reports** with **Data & Reports** in primary navigation.
- `/data-reports` becomes the canonical route; `/evidence`, `/data`, and `/reports` remain query-preserving compatibility redirects.
- The internal `features/evidence/` boundary and evidence-domain terminology remain intact to avoid mechanical source churn; only generic workspace copy changes to data/report terminology.
- Analytical query scope, `view=` semantics, downloads, report access, and artifact behavior are unchanged.
