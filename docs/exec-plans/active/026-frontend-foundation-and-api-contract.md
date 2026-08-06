# Plan 026 — Frontend Foundation and API Contract

Status: complete

Owner: agent

Last updated: 2026-07-18

## Goal

Create a reliable frontend foundation that matches the existing read-only
FastAPI contract exactly, supports typed request/response handling, centralizes
run and metric state, and renders reusable request states without changing the
current visual design.

## Context

Read before editing:

1. `AGENTS.md`
2. Confirm `HARNESS.md` and root `ARCHITECTURE.md` are absent in this zip.
3. `docs/design-docs/current-code-feature-inventory.md`
4. `docs/product-specs/project-spec.md`
5. `docs/design-docs/data-contract.md`
6. `docs/design-docs/database-contract.md`
7. `docs/design-docs/metric-contract.md`
8. `docs/design-docs/pipeline-contract.md`
9. `docs/design-docs/theme-intelligence-contract.md`
10. `docs/verification/quality-gates.md`
11. `docs/verification/test-matrix.md`
12. `docs/exec-plans/active/012-frontend-dashboard-integration.md`
13. `docs/exec-plans/active/025-dashboard-data-api.md`
14. `src/api/app.py`, `src/api/routers/`, and `src/api/schemas/`
15. `frontend/src/api.js` and `frontend/src/App.jsx`

The current frontend's API layer contains calls to endpoints that the current
backend does not expose. Its top-level state also suppresses most request
failures and allows downstream pages to render fabricated fallback values.

## Non-Goals

- No page-level analytical redesign in this plan.
- No backend route or schema changes.
- No replacement of Recharts or `react-force-graph-2d`.
- No pipeline execution from the browser.
- No full conversion of every JSX component to TypeScript in one change.
- No new analytical metrics.

## Files Expected To Change

Existing:

- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/vite.config.js`
- `frontend/src/main.jsx` or `frontend/src/main.tsx`
- `frontend/src/App.jsx`
- `frontend/src/api.js` (remove after migration)
- `frontend/src/index.css`
- `frontend/README.md`
- `Makefile`
- `.gitignore`
- `docs/exec-plans/active/026-frontend-foundation-and-api-contract.md`

New, exact names may vary slightly but keep the separation:

- `frontend/tsconfig.json`
- `frontend/src/api/client.ts`
- `frontend/src/api/runs.ts`
- `frontend/src/api/overview.ts`
- `frontend/src/api/networks.ts`
- `frontend/src/api/topics.ts`
- `frontend/src/api/evolution.ts`
- `frontend/src/api/reports.ts`
- `frontend/src/api/errors.ts`
- `frontend/src/types/api.ts`
- `frontend/src/app/queryClient.ts`
- `frontend/src/app/DashboardProvider.tsx`
- `frontend/src/app/dashboardSearchParams.ts`
- `frontend/src/hooks/useDashboardContext.ts`
- `frontend/src/components/states/LoadingState.tsx`
- `frontend/src/components/states/ErrorState.tsx`
- `frontend/src/components/states/EmptyState.tsx`
- `frontend/src/components/states/ArtifactUnavailableState.tsx`
- `frontend/src/components/states/VerificationFailureState.tsx`
- `frontend/src/test/setup.ts`
- `frontend/src/api/__tests__/contract.test.ts`
- `frontend/src/app/__tests__/dashboardSearchParams.test.ts`

## Milestone 1 — Freeze the Current Frontend Baseline

Tasks:

- [x] Record the current route list and route-to-component mapping.
- [x] Search `frontend/src` for mock/random/fixed analytical data and add a
      checklist to this plan's progress log. Include at least:
      - `Math.random` usage;
      - hard-coded community arrays;
      - hard-coded reports;
      - fixed 2024 dates;
      - fake persistence/trend/diversity values;
      - unsupported platforms;
      - inert controls and buttons.
- [x] Capture baseline screenshots for all routes at desktop and mobile widths.
      Store them under `frontend/tests/baseline/` only if project policy allows
      binary fixtures; otherwise record a reproducible capture command and keep
      screenshots outside version control.
- [x] Run and record current `npm run lint` and `npm run build` results before
      making changes.
- [x] Add generated Playwright output, `test-results`, `.DS_Store`, Vite build
      output, and test coverage output to `.gitignore`.
- [x] Do not delete the current visual components yet; later plans will replace
      their data sources incrementally.

Validation:

```bash
cd frontend
npm ci
npm run lint
npm run build
```

## Milestone 2 — Add the Minimum Frontend Engineering Tooling

Tasks:

- [x] Add TypeScript support while allowing `.jsx` and `.tsx` to coexist.
- [x] Add TanStack Query for request caching, cancellation, stale-state control,
      and consistent loading/error handling.
- [x] Add Vitest, React Testing Library, `@testing-library/jest-dom`, and MSW.
- [x] Add Playwright as a dev dependency, but defer full end-to-end scenarios to
      Plan 031.
- [x] Add scripts:
      - `typecheck`;
      - `test` for unit/component tests;
      - `test:watch`;
      - `test:e2e`;
      - `check` that runs typecheck, lint, unit tests, and build.
- [x] Configure Vite/Vitest so tests do not require a running backend or network
      access.
- [x] Keep `VITE_API_BASE_URL || "/api/v1"` as the default API base.
- [x] Do not place secrets or absolute local paths in frontend environment files.

Validation:

```bash
cd frontend
npm run typecheck
npm run test -- --run
npm run lint
npm run build
```

## Milestone 3 — Implement an Exact Typed API Client

Tasks:

- [x] Create TypeScript types matching the Pydantic schemas in
      `src/api/schemas/`. Do not add fields that are not in those schemas.
- [x] Create one Axios client with:
      - base URL from `VITE_API_BASE_URL`;
      - a bounded timeout;
      - JSON accept headers;
      - cancellation support through `AbortSignal`;
      - structured error normalization.
- [x] Model the API error envelope used by `src/api/errors.py` and preserve its
      error code/message/details for the UI.
- [x] Implement functions for every canonical endpoint used by the dashboard:
      health, runs, run detail, verification, artifacts, overview, network,
      centrality, communities, community detail, topics, themes, transitions,
      persistent communities, membership changes, theme similarity, report URL,
      and artifact download URL.
- [x] Ensure list functions accept the backend's exact query names and limits:
      `metric`, `type`, `community_id`, `month`, `limit`, `offset`, `max_nodes`,
      `max_edges`, and `min_weight`.
- [x] Remove calls to `/facets`, `/community-summary`, and `/files`.
- [x] Add contract tests that compare the client route strings and query names
      against a checked-in API route fixture generated from the backend OpenAPI
      document, or import the generated OpenAPI JSON during a repository-level
      test. The browser tests must remain offline.
- [x] Add URL builders for inline report display and manifest-key downloads. Do
      not fetch binary files through Axios unless the UI needs the bytes.

Validation:

```bash
python -m pytest -q tests/unit/test_backend_api.py
cd frontend
npm run test -- --run src/api/__tests__/contract.test.ts
npm run typecheck
```

## Milestone 4 — Centralize Run, Metric, and URL State

Tasks:

- [x] Add `QueryClientProvider` at the application root.
- [x] Replace the state-heavy data loading in `App.jsx` with a
      `DashboardProvider` that owns only global presentation state:
      - selected `run_id`;
      - selected metric, exactly `if` or `wif`;
      - API health;
      - run catalog;
      - selected run detail;
      - selected run verification.
- [x] Keep page-specific data in page-level queries rather than loading all
      dashboard data in the root layout.
- [x] Store the selected run and metric in URL search parameters, for example
      `?run=<run_id>&metric=if`.
- [x] Validate URL values against the current run catalog and supported metrics.
      Invalid values must fall back deterministically without throwing.
- [x] Default selection rule:
      1. use a valid `run` URL parameter;
      2. otherwise select the first `completed` run in the API's current order;
      3. otherwise select the first available run;
      4. otherwise render a no-runs state.
- [x] Do not invent month facets. Derive platform, content type, year, and month
      choices from `RunsResponse.runs`.
- [x] Export a typed `useDashboardContext` hook so pages do not use raw
      `useOutletContext` with undocumented object shapes.
- [x] Keep the existing sidebar collapse behavior, but isolate it from analytical
      state.

Validation:

```bash
cd frontend
npm run test -- --run src/app/__tests__/dashboardSearchParams.test.ts
npm run typecheck
npm run build
```

## Milestone 5 — Introduce Reusable Request and Integrity States

Tasks:

- [x] Implement reusable visual states that match the existing dark design:
      loading, generic error, empty result, optional artifact unavailable, and
      verification failure.
- [x] Differentiate these cases:
      - API cannot be reached;
      - no canonical runs exist;
      - selected run is failed/running;
      - selected run verification is invalid;
      - endpoint returns zero records;
      - optional artifact was not generated;
      - endpoint rejects a tampered/missing artifact.
- [x] Add retry buttons only for idempotent GET requests.
- [x] Preserve structured error codes in developer-visible details but use clear
      human-readable primary messages.
- [x] Add `aria-live` to asynchronous status text.
- [x] Ensure the app does not render previous-run data as if it belonged to the
      newly selected run while new queries are loading. Either clear it or show a
      clearly labelled retained-data state.
- [x] Remove `console.error` as the only user-facing failure handling.

Validation:

```bash
cd frontend
npm run test -- --run
npm run lint
npm run build
```

## Milestone 6 — Document and Log the Foundation

Tasks:

- [x] Update `frontend/README.md` with install, typecheck, test, build, API proxy,
      and environment instructions.
- [x] Add or update Make targets for frontend typecheck, test, and check.
- [x] Update this plan's progress and decision logs with actual files, commands,
      and deviations.
- [x] Document the API state ownership rule: global run/metric in provider;
      page-specific filters and queries within each feature.
- [x] Record that backend schema changes were not required, or list approved
      additive changes if the human explicitly authorized any.

## Acceptance Criteria

- [x] No obsolete API endpoint remains in `frontend/src`.
- [x] Typed client coverage exists for every current dashboard endpoint.
- [x] The selected run and metric survive reload and browser navigation.
- [x] The root layout no longer requests page-specific community/month data.
- [x] The application visibly handles API unavailable, no runs, invalid run,
      failed verification, empty records, and optional artifact missing.
- [x] Unit tests run without a backend or internet connection.
- [x] `npm run typecheck`, `npm run test -- --run`, `npm run lint`, and
      `npm run build` pass.
- [x] Backend API tests remain green.

## Decision Log

| Date | Decision | Reason |
|---|---|---|
| 2026-07-18 | Migrate incrementally to TypeScript rather than rewrite all JSX. | Reduces risk while making the API boundary reliable first. |
| 2026-07-18 | Use TanStack Query and keep Axios. | The current app already uses Axios; TanStack Query adds missing request lifecycle behavior without changing the backend. |
| 2026-07-18 | Derive facets from `/runs`. | The canonical API does not expose `/facets`; run summaries already contain platform, content type, year, and month. |
| 2026-07-18 | Check in a route/query fixture generated from the backend OpenAPI document. | Keeps frontend contract tests deterministic and offline while preserving an auditable link to the source schemas. |
| 2026-07-18 | Keep analytical page mocks in place during Plan 026. | This plan establishes the API/state foundation only; replacing page-level data belongs to Plans 027–031 and would exceed the surgical scope. |
| 2026-07-18 | Use MSW with unhandled requests treated as errors in unit tests. | Prevents tests from silently reaching a backend or the internet. |

## Risks

| Risk | Mitigation |
|---|---|
| Incremental JS/TS mixture becomes inconsistent. | Require all new API, state, hooks, and tests to be TypeScript; migrate feature components when touched. |
| Cached data from one run appears under another. | Include `run_id`, metric, pagination, and filters in every query key; cancel or invalidate on selection changes. |
| API schema drifts later. | Keep an offline OpenAPI/client contract test in the frontend check. |
| Tooling changes obscure functional progress. | Keep this plan limited to foundation and avoid page redesign. |

## Rollback Plan

Revert the plan as one branch. The backend and analytical artifacts are
unchanged. If the TypeScript migration blocks progress, retain the new exact API
client and query architecture in JavaScript with JSDoc types, but do not restore
obsolete endpoints or mock fallbacks.

## Progress Log

| Date | Update |
|---|---|
| 2026-07-18 | Plan created from the uploaded main-branch zip. |
| 2026-07-18 | Confirmed `HARNESS.md` and root `ARCHITECTURE.md` are absent, as anticipated by the plan; read all available contracts, verification docs, active Plans 012/025, API routers/schemas, and the current frontend entry points before editing. |
| 2026-07-18 | Baseline validation: `npm ci` passed with zero vulnerabilities; `npm run lint` passed with 31 existing warnings; `npm run build` passed with a 1,075.83 kB main bundle and the existing Vite large-chunk warning. |
| 2026-07-18 | Recorded the ten routes and a reproducible desktop/mobile Playwright capture command in `frontend/tests/baseline/README.md`; binary screenshots were not committed. |
| 2026-07-18 | Baseline mock checklist: random graph generation in `NetworkGraph`; hard-coded community rows and rankings; hard-coded report records; fixed 2024 dates in evolution/report views; fabricated persistence, trend, and diversity values; unsupported Reddit/Facebook/Discord options; and inert page controls. These are intentionally preserved for later page-integration plans. |
| 2026-07-18 | Added incremental TypeScript, TanStack Query, Vitest/RTL/MSW, and Playwright tooling; added `typecheck`, unit-test, E2E, and aggregate `check` scripts plus Make targets. |
| 2026-07-18 | Replaced `frontend/src/api.js` with an exact typed API boundary covering health, runs, run details, verification, artifacts, overview, network, centrality, communities, community detail, topics, themes, transitions, persistence, membership changes, theme similarity, report, and artifact-download URLs. Removed obsolete `/facets`, `/community-summary`, and `/files` usage. |
| 2026-07-18 | Added an offline OpenAPI route/query fixture and contract test, structured error normalization, AbortSignal support, bounded Axios timeout, and URL builders for report/download endpoints. |
| 2026-07-18 | Added `DashboardProvider` and typed context hook. Global state is now limited to API health, run catalog, selected run/detail/verification, and exact `if`/`wif` metric state persisted in URL search parameters. Page-specific analytical data is no longer loaded by the root layout. |
| 2026-07-18 | Added reusable loading, error, empty, optional-artifact, and verification-failure states with accessible live regions and retry behavior for GET requests; the root visibly handles API failure, no runs, incomplete/failed runs, metadata failure, and invalid verification. |
| 2026-07-18 | Updated the top bar surgically to select canonical runs and IF/WIF metrics while retaining the existing visual structure; sidebar behavior and page components remain otherwise unchanged. |
| 2026-07-18 | Updated `.gitignore`, frontend documentation, Make targets, and API state-ownership guidance. No backend routes, schemas, analytical metrics, or pipeline defaults changed. |
| 2026-07-18 | Final validation: backend API tests 10 passed; frontend typecheck passed; 12 frontend tests passed offline; lint passed with 20 pre-existing unused-code warnings (down from the 31-warning baseline); production build passed; Playwright command passed with no scenarios; `npm run check` passed. |
| 2026-07-18 | Plan 031 quality integration added canonical fixture coverage, strict source guards, route-level lazy loading, zero-warning lint, focused coverage, bundle budgets, real-service Playwright/axe workflow definitions, and release documentation. Browser execution remains pending in a browser-capable environment. |
| 2026-07-23 | Restored missing Vite/TypeScript/ESLint/Playwright build scaffolding in the uploaded split frontend, added configurable API timeout and same-origin Docker/nginx proxying, and updated the offline OpenAPI contract fixture for the additive `deep` verification query. The frontend now belongs under the repository root and consumes only manifest-backed `/api/v1` routes. |
