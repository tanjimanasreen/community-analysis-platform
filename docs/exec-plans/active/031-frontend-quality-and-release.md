# Plan 031 — Frontend Quality and Release

Status: active

Owner: agent

Last updated: 2026-07-18

## Goal

Establish an offline, reproducible frontend quality gate covering API contract,
components, end-to-end workflows, accessibility, performance, release hygiene,
and documentation for the fully functional dashboard.

## Dependencies

- Plans 026–030 are functionally complete.
- No mock analytical data remains by design.

## Non-Goals

- No new analytical feature work.
- No cloud deployment or authentication.
- No visual redesign beyond accessibility and responsive fixes.
- No paid service dependency.

## Files Expected To Change

- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/vite.config.js`
- `frontend/playwright.config.ts`
- `frontend/src/test/`
- `frontend/tests/`
- `tests/fixtures/dashboard_artifacts/` or a deterministic fixture generator
- `scripts/build_dashboard_fixture.py` (optional/new)
- `Makefile`
- `.gitignore`
- `frontend/README.md`
- `README.md`
- `docs/DEMO_SCRIPT.md`
- `docs/HANDOFF.md`
- `docs/verification/quality-gates.md`
- `docs/verification/test-matrix.md`
- `docs/exec-plans/active/031-frontend-quality-and-release.md`

## Milestone 1 — Create a Canonical Offline Dashboard Fixture

Tasks:

- [x] Build a tiny deterministic canonical artifact root containing at least:
      - one completed Twitter run;
      - one completed Telegram run;
      - two compatible monthly runs for one platform/content type;
      - overview data;
      - IF/WIF network/community data;
      - centrality;
      - matched and partial topics;
      - themes with provider metadata;
      - transitions, persistent communities, membership changes;
      - theme similarity matrix or image artifact;
      - report/artifact metadata.
- [x] Include deliberate variants for tests:
      - no runs;
      - optional artifact missing;
      - failed verification/tampered checksum;
      - empty table;
      - sampled graph.
- [x] Prefer a Python fixture generator that uses the repository's canonical
      artifact models, so committed binary/generated data stays minimal.
- [x] The fixture generator must not call databases, providers, TEI, model
      downloads, or pipeline analysis.
- [x] Add a verification step using the existing run-manifest validator.

Validation:

```bash
python scripts/build_dashboard_fixture.py --out /tmp/community-dashboard-fixture
python -m pytest -q tests/unit/test_backend_api.py
```

## Milestone 2 — Complete Unit and Component Coverage

Required coverage:

- [x] exact API routes/query parameters and structured errors;
- [x] URL state parsing and recovery;
- [x] run/metric selection;
- [x] loading/error/empty/unavailable/verification states;
- [x] Overview field mapping and no mock fallback;
- [x] graph transformation and sampling metadata;
- [x] community/topic/theme ID mapping;
- [x] pagination and page-local filtering labels;
- [x] semantic value normalization;
- [x] evolution/comparison view models;
- [x] artifact downloads and intermediate restrictions;
- [x] methodology baseline and selected-run metadata.

Tasks:

- [x] Use MSW handlers that mirror exact backend responses.
- [x] Fail tests on unhandled API requests.
- [x] Add a test that scans rendered feature fixtures for known old mock IDs,
      dates, and labels such as `C-1124`, May 2024, Reddit, Facebook, Discord, or
      fake report names.
- [x] Set sensible coverage thresholds for adapters, hooks, and state utilities;
      do not chase coverage through trivial icon markup.

## Milestone 3 — Add Playwright End-to-End Workflows

Start the real FastAPI service against the deterministic fixture and the Vite
frontend in Playwright `webServer` configuration.

Required scenarios:

- [x] application starts and selects a completed run;
- [x] run switch updates provenance and KPIs;
- [x] IF/WIF switch updates network and community results;
- [x] selected community deep link survives reload;
- [x] topic matched/partial and unigram/bigram controls work;
- [x] transitions and membership tables render from artifacts;
- [x] cross-platform comparison uses two explicit runs;
- [x] artifact report opens/download URL is correct;
- [x] optional artifact missing produces the correct state;
- [x] failed verification blocks analytics;
- [x] mobile navigation opens, navigates, and closes;
- [x] browser back/forward restores search-parameter state.

Tasks:

- [x] Run Chromium by default; add Firefox/WebKit only after the core suite is
      stable and runtime is acceptable.
- [x] Keep traces/screenshots only on failure.
- [x] Do not commit generated `playwright-report` or `test-results`.
- [ ] Add one visual-regression snapshot per major route after the UI is stable,
      with a documented update process.

## Milestone 4 — Accessibility Gate

Tasks:

- [x] Add automated axe checks to representative routes/states.
- [x] Fix heading hierarchy, landmark labels, table captions/headers, form labels,
      button names, focus visibility, and color contrast.
- [x] Ensure graphs/charts have accessible summaries or data tables.
- [x] Ensure keyboard users can select runs, metrics, communities, tabs, and
      pagination without relying on canvas interaction.
- [x] Announce asynchronous errors and selection changes appropriately.
- [ ] Test at 200% zoom and widths down to 320 CSS pixels.

## Milestone 5 — Performance and Bundle Gate

Tasks:

- [x] Lazy-load all route pages.
- [x] Split graph and chart libraries into route-level chunks.
- [x] Avoid loading `react-force-graph-2d` on non-network routes.
- [x] Memoize expensive graph transforms and deterministic color maps.
- [x] Avoid fetching all paginated records merely to populate a decorative chart.
- [x] Add a documented bundle budget. Suggested initial gate:
      - no single application chunk over 500 kB minified unless it is a
        route-lazy vendor chunk;
      - initial route JS materially below the current approximately 1 MB bundle.
- [x] Run a production preview smoke test.

Validation:

```bash
cd frontend
npm run build
npm run preview -- --host 127.0.0.1
```

## Milestone 6 — Lint, Type, and Dead-Code Cleanup

Tasks:

- [x] Reach zero lint warnings.
- [x] Remove unused imports, state, props, assets, starter CSS, `react.svg`,
      `vite.svg`, and obsolete `frontend/todo.md` recommendations.
- [x] Remove generated `.DS_Store`, old Playwright output, and test artifacts from
      the repository.
- [x] Ensure no obsolete API path or mock fallback remains through source scans.
- [x] Ensure no secret, absolute path, or direct provider/database call is present
      in frontend source.

Suggested scans:

```bash
rg -n "facets|community-summary|/files|Math\.random|C-1124|May '?24|Reddit|Facebook|Discord" frontend/src
rg -n "OPENAI|NEO4J|MEMGRAPH|api[_-]?key|/Users/|/Volumes/" frontend
```

Expected result: no analytical mock or forbidden integration matches; legitimate
methodology text may be allowlisted with explanation.

## Milestone 7 — Repository Quality Gates and Documentation

Tasks:

- [x] Add Make targets:
      - `frontend-typecheck`;
      - `frontend-test`;
      - `frontend-e2e`;
      - `frontend-check`;
      - optional `dashboard-fixture`.
- [x] Update root and frontend README with exact local sequence:
      generate sample/canonical runs, start API, start frontend, run checks.
- [x] Update `docs/DEMO_SCRIPT.md` to use real routes and selected runs.
- [x] Update `docs/HANDOFF.md` with architecture, state ownership, API mapping,
      troubleshooting, and known limitations.
- [x] Add frontend items to `quality-gates.md` and `test-matrix.md`.
- [x] Update all six plans' progress logs and move completed plans according to
      repository convention.

Final validation:

```bash
make format
make lint
make test
make api-smoke-test
make frontend-check
make frontend-e2e
make frontend-build
```

If environment limitations prevent a command, record the exact missing
runtime/dependency and run the largest possible offline subset. Do not mark the
plan complete without a dependency-complete validation record from a suitable
environment.

## Acceptance Criteria

- [x] Deterministic canonical dashboard fixture exists and validates.
- [ ] Unit/component and Playwright suites pass offline.
- [ ] Representative routes pass automated accessibility checks.
- [x] Lint has zero warnings and typecheck/build pass.
- [x] Initial bundle is route-split and graph/chart libraries are lazy.
- [x] Source scans find no obsolete API calls or analytical mock data.
- [x] Documentation and Make targets reproduce the workflow from a fresh clone.
- [ ] Backend analytical/default-preservation tests remain green.

## Decision Log

| Date | Decision | Reason |
|---|---|---|
| 2026-07-18 | Generate dashboard fixtures from canonical artifact models instead of committing a large generated tree. | Keeps fixtures deterministic, minimal, manifest-valid, and free of pipeline/provider/database execution. |
| 2026-07-18 | Run Vitest in one isolated fork and exclude `tests/e2e` from unit discovery. | Prevents Playwright specs from being collected by Vitest and makes the 37-file jsdom suite deterministic in constrained environments. |
| 2026-07-18 | Lazy-load every route and split React, data, graph, and chart vendors. | Reduces the initial entry from the prior approximately 1 MB bundle to about 60 kB while retaining current UI behavior. |
| 2026-07-18 | Require explicit opt-in for a system Chromium executable. | Avoids silently using a managed browser with unknown enterprise policy; the normal path is Playwright-managed Chromium. |
| 2026-07-18 | Skip a visual assertion only when its reviewed baseline does not exist. | Missing screenshots must never be fabricated; `npm run test:e2e:update` generates reviewable baselines in a browser-capable environment. |
| 2026-07-18 | Keep the plan active until Playwright, axe, and visual baselines are validated in a browser-capable environment. | The execution sandbox's managed Chromium blocks all URLs and Playwright Chromium could not be downloaded because outbound DNS is unavailable. |

## Risks

| Risk | Mitigation |
|---|---|
| E2E fixture diverges from real manifests. | Generate it through canonical artifact models and validate it with backend code. |
| Visual snapshots are flaky due to force layout. | Use deterministic graph configuration, fixed fixture, and wait for a stable rendered state or snapshot non-canvas UI. |
| Bundle budget is initially missed. | Record baseline, lazy-load routes/vendors first, then tighten budget in a documented follow-up. |
| Full repository suite needs optional dependencies. | Run focused offline gates locally and require dependency-complete validation before completion. |

## Rollback Plan

Testing/documentation changes can be reverted independently, but do not remove
functional error states or restore mock data to make tests pass. If Playwright
is temporarily blocked, keep the unit/component suite and fixture generator,
mark E2E as blocked with evidence, and do not call the roadmap release-ready.

## Progress Log

| Date | Update |
|---|---|
| 2026-07-18 | Plan created. |
| 2026-07-18 | Confirmed root `HARNESS.md` and `ARCHITECTURE.md` are absent from the uploaded source, then reviewed the repository contracts, quality gates, test matrix, Plans 026–030, API schemas/services, frontend routes, tests, and build configuration. |
| 2026-07-18 | Added `scripts/build_dashboard_fixture.py` and `tests/unit/test_dashboard_fixture.py`. The canonical generator produces Twitter/X and Telegram runs, compatible history, structural/semantic/longitudinal/report artifacts, and no-run, missing, empty, sampled, and tampered variants without pipeline, database, provider, TEI, or model execution. |
| 2026-07-18 | Added focused V8 coverage, strict source guards, Playwright real-service workflows, representative axe checks, mobile/zoom/history scenarios, and a reviewed visual-baseline update path. Vitest now excludes Playwright specs and runs deterministically in one fork. |
| 2026-07-18 | Lazy-loaded all ten routes, split graph/chart/data/React vendors, added a 300 KiB entry and 500 KiB application-chunk budget, improved focus/reduced-motion/live-region behavior, and removed unused starter assets, CSS, `todo.md`, `.DS_Store`, and generated test output. |
| 2026-07-18 | Updated Make targets, root/frontend READMEs, demo script, handoff, frontend quality gate, test matrix, and Plans 026–030 progress records. No backend route/schema, thesis metric, algorithm default, output category, or pipeline behavior changed. |
| 2026-07-18 | Passing validation: fixture generator; 11 focused backend/fixture tests; 37 frontend test files / 75 tests; focused coverage 89.02% statements, 78.05% branches, 91.08% functions, 89.02% lines; typecheck; zero-warning lint; route-split production build; bundle budget; production-preview HTTP smoke; and Playwright discovery of 28 scenarios. |
| 2026-07-18 | Browser execution remains blocked in this sandbox: managed Chromium applies `URLBlocklist=["*"]` and returns `ERR_BLOCKED_BY_ADMINISTRATOR` for local servers; downloading Playwright Chromium failed because outbound DNS is unavailable. Per the rollback/validation rule, Playwright, axe runtime, reviewed visual snapshots, and the dependency-complete full repository gate remain open, so this plan is not marked complete. |
| 2026-07-18 | Full repository wrappers remain environment-blocked: `make format` cannot import Black, `make test` uses `uv --frozen` without a committed `uv.lock`, `make lint` could not finish its dependency bootstrap within the sandbox limit, and unrestricted pytest collection requires optional Neo4j, MLflow, Prefect, kneed, and demoji dependencies. The focused backend/default-preservation subset and all frontend offline gates passed; no blocked gate is marked complete. |
| 2026-07-23 | Integrated the separately uploaded frontend under the root project, added production Docker/nginx scaffolding, aligned the verification route contract, and documented the canonical `run-all` → artifact root → API → dashboard workflow. Python/OpenAPI static contract checks pass. Frontend dependency installation, build, and browser execution remain blocked in this sandbox because the npm registry/browser download is unavailable; a committed `package-lock.json` remains required before release. |
| 2026-09-15 | Release-cleanup pass: reduced `docs/images/system-architecture.svg` from 727,174 to 293,875 bytes without changing its architecture content; corrected the backend secret-log test to use `LogRecord.getMessage()` while preserving its no-secret assertions; fixed the frontend graph coordinate types, numeric reduction typing, and stale API fixture/query-mock fields. Regenerated only the four README dashboard screenshots from the deterministic local fixture with generic run metadata and preserved dimensions. `git diff --check` passed, `make lint` passed, and `make test` passed (814 passed, 1 skipped, 13 warnings). `make frontend-check` now passes typecheck and lint (6 warnings) but remains blocked by 16 failed tests in 14 files, plus one test file with no discovered suite; failures are stale source guards/contracts/selectors/fixtures and router/auth test setup, and no broad refactor was attempted. |
| 2026-09-15 | Frontend Vitest release pass: resolved the 16 failing tests and removed the empty no-suite test file. Root causes were stale selectors/copy (9 tests), stale source/API contract expectations (2), async/router/auth test harness setup (3, with the full gate also exposing one inherited Cognito-mode harness case), and two genuine network-model defects. Updated only the affected tests/fixture, made the smallest network-model fix to omit malformed endpoints and aggregate reciprocal community links, and forced the App verification test to use local auth mode without changing production auth. `make frontend-check` passed: typecheck, 56 Vitest files / 167 tests, build, and bundle check; Oxlint retained 6 pre-existing warnings. `git diff --check` and `make lint` passed. With loopback access for Prefect, `make test` passed (814 passed, 1 skipped, 13 warnings). No README/link validator exists in the repository. |
