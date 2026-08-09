# Plan 041 — Community Evolution Master–Detail UX

Status: implemented; environment acceptance gates pending

Owner: agent

Last updated: 2026-08-08

## Goal

Refine the Community Evolution page into a clear master-to-detail research workflow:

1. understand the run-level longitudinal scope;
2. see the complete persistent-path landscape;
3. select exactly one persisted path;
4. inspect that same path through structural continuity, member mobility, thematic similarity, and evidence.

The path selector is a drill-down control derived from the analysis results, not a global dashboard filter.

## Dependencies

- Plan 040 path/mobility/theme-similarity artifacts and read-only APIs remain authoritative.
- `community_paths.parquet` remains the source for the all-path landscape and selected-path context.
- Path selection remains URL-backed through `?path=<stable_path_id>`.

## Non-goals

- Do not change DFS path construction, Jaccard calculations, transition thresholds, or path ordering semantics.
- Do not change member mobility, including reappearing-member semantics.
- Do not change Community Evolution theme similarity or the pinned `paraphrase-MiniLM-L6-v2` model/revision.
- Do not change IF/shared_post, WIF/weighted_post, Louvain, LDA, Telegram, Memgraph, or Plan 039 thematic clustering.
- Do not add a charting library or backend/API/artifact work.

## Milestones

### 1. Protect current path-state behavior

- Preserve stable `path_id` selection.
- Preserve URL restoration, invalid-path fallback, and back/forward-compatible search parameters.
- Preserve the shared selected path across mobility, theme similarity, and evidence.
- Preserve the local General/IF/WIF theme perspective independently from path selection.

### 2. Make the page header run-level only

- Remove the persistent-path selector from the page header.
- Keep the narrow-screen jump-to-section control.
- Replace selected-path KPI cards with run-level cards:
  - persistent path count;
  - longest path;
  - average path Jaccard;
  - timeline coverage.

### 3. Make structural continuity the master view

- Show all persistent paths together before asking the user to drill down.
- Move the path selector beside the Community Similarity over Time heading.
- Keep path rows clickable and synchronize row selection with the selector.
- Strengthen the selected-row treatment with non-color state (`Selected` plus `aria-pressed`).

### 4. Add selected-path context

- Add a compact selected-path context strip below the all-path timeline.
- Show ordered community IDs, month labels, transition Jaccard values, duration, average Jaccard, and start/end membership.
- Keep the context component presentation-only and artifact-driven.

### 5. Keep downstream views visibly tied to the same path

- Add compact selected-path context labels to Member Mobility and Thematic Similarity headings.
- Do not add duplicate selectors to downstream sections.
- Keep evidence on the same selected path.

### 6. Compact methodology and preserve navigation

- Retain the methodology strip and resolved analytical contract.
- Reduce methodology vertical footprint so the path landscape appears sooner.
- Preserve the right sticky `PageNavigationRail` as navigation-only.
- Preserve the mobile native jump-to-section selector.

### 7. Tests, docs, and validation

- Expand page tests for all-path-first presentation, synchronized row/dropdown selection, URL persistence, invalid-path recovery, and theme-view independence.
- Extend Playwright longitudinal coverage for contextual path selection.
- Update the frontend quality matrix and project spec to document the master-detail workflow.
- Run focused frontend checks and repository gates available in the environment.

## Acceptance criteria

- The page header has no persistent-path selector.
- Top KPI cards contain only run-level longitudinal context.
- All persisted paths are visible together in Community Similarity over Time.
- The path selector lives beside the all-path structural view.
- Clicking a path row and using the selector are equivalent.
- Exactly one path drives mobility, thematic similarity, and evidence.
- Selected path remains encoded in the URL and restores on refresh/direct navigation.
- Invalid path IDs recover deterministically.
- Selected state uses `aria-pressed` and visible text, not color alone.
- Downstream sections identify the active path without adding duplicate selectors.
- The methodology strip remains available but more compact.
- The right sticky vertical rail remains navigation-only.
- No backend, artifact, API, algorithm, threshold, or model contract changes occur.

## Progress log

### 2026-08-08 — Source-of-truth inspection

- Unpacked `community-analysis-full-review-20260808-1850.zip` as the absolute source of truth.
- Reviewed the uploaded manifest/summary, then read the required harness, architecture, feature inventory, product/data/database/metric/pipeline/theme contracts, quality gates, test matrix, and active Plan 040 before editing.
- Confirmed the current page mixed run-level and selected-path KPIs and placed the path selector in the page header even though path selection is a result-level drill-down.
- Confirmed the existing path state is already URL-backed and the same selected path already scopes mobility and thematic similarity.

### 2026-08-08 — Implementation

- Removed the persistent-path selector from the page header and retained the mobile jump-to-section control.
- Replaced selected-path KPI cards with Longest Path and Timeline Coverage so the overview is run-level only.
- Moved the path selector into Community Similarity over Time and renamed it `Inspect persistent path`.
- Kept the all-path timeline as the master view and strengthened selected state with `Selected`, `aria-pressed`, stronger connectors, and synchronized dropdown state.
- Added `SelectedPathContext.tsx` with the selected community sequence, transition Jaccard labels, month range, duration, average Jaccard, and start/end membership.
- Added active-path context pills to Member Mobility and Thematic Similarity without introducing duplicate selectors.
- Compacted the methodology strip while preserving the resolved run contract and full-methodology link.
- Expanded Community Evolution unit coverage and longitudinal Playwright coverage for the master-detail interaction.
- Updated the project spec and frontend test matrix for the all-path-first, single-path-detail workflow.


### 2026-08-08 — Validation

Passed in the available sandbox:

- TypeScript `transpileModule` syntax parsing passed for all changed Community Evolution source, unit-test, and Playwright files.
- Source-of-truth scope comparison confirmed only Plan 041 frontend/tests/docs files changed.
- Protected analytical files/configuration remain byte-for-byte unchanged, including follower-followee metrics, Louvain, LDA, `configs/algorithms.yml`, the retweet/quote evolution config, DFS path construction, and community-transition serialization.

Environment-blocked gates:

- Focused `npm test -- --run src/pages/__tests__/CommunityEvolution.test.jsx` could not start because the source archive intentionally excludes `frontend/node_modules`; `vitest` is therefore unavailable.
- `make frontend-check` reached `tsc --noEmit` and stopped because the excluded frontend dependencies provide the missing `@testing-library/jest-dom`, `vite/client`, and `vitest/globals` type libraries.
- `make test` could not create the frozen environment because the sandbox package registry cannot resolve the existing build-system requirement `setuptools>=61.0`.
- Browser E2E was not run because the frontend dependency/server environment is unavailable in the archive sandbox.

Developer-environment acceptance gates remain: focused Community Evolution Vitest, `make frontend-check`, and `make frontend-e2e`.
