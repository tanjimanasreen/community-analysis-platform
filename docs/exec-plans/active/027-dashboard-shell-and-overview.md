# Plan 027 — Dashboard Shell and Overview

Status: complete

Owner: agent

Last updated: 2026-07-18

## Goal

Make the persistent dashboard shell and Overview route fully functional using
validated run-scoped API data while preserving the current layout and dark
visual identity.

## Dependencies

- Plan 026 is complete.
- `GET /health`, `/runs`, `/runs/{run_id}`, `/verification`, `/overview`,
  `/network`, `/communities`, `/themes`, and optional `/transitions` clients are
  available and tested.

## Non-Goals

- No full network exploration; that belongs to Plan 028.
- No cross-platform comparison chart on the Overview unless the user explicitly
  selects two compatible runs; that belongs to Plan 030.
- No backend-calculated trend percentages or narrative generation.
- No fake notifications, profile records, or report creation.

## Files Expected To Change

- `frontend/src/App.jsx` or migrated `App.tsx`
- `frontend/src/components/Sidebar.jsx`
- `frontend/src/components/Topbar.jsx`
- `frontend/src/components/KPICards.jsx`
- `frontend/src/components/DataTable.jsx`
- `frontend/src/components/RightSidebar.jsx`
- `frontend/src/components/charts/NetworkGraph.jsx`
- `frontend/src/components/charts/EvolutionChart.jsx`
- `frontend/src/components/charts/PlatformComparison.jsx`
- `frontend/src/components/charts/TransitionsSankey.jsx`
- `frontend/src/pages/Overview.jsx`
- `frontend/src/features/runs/` (new)
- `frontend/src/features/overview/` (new)
- `frontend/src/components/MetricCard.tsx` (new/shared)
- `frontend/src/components/ArtifactStatusBadge.tsx` (new/shared)
- relevant tests
- `docs/exec-plans/active/027-dashboard-shell-and-overview.md`

## Milestone 1 — Convert the Top Bar into a Real Run Selector

Tasks:

- [x] Replace the fake month selector with a labelled analysis-run selector.
      Each option should display platform, content type, date range, and concise
      run ID, while the value remains `run_id`.
- [x] Optionally keep compact platform/content/date selectors in the same visual
      position, but they must filter the available runs and ultimately select a
      concrete run. They must not create an impossible synthetic combination.
- [x] Add the real IF/WIF selector with values `if` and `wif`. Use labels such as
      “Interaction Frequency (IF)” and “Weighted Interaction Frequency (WIF)”.
- [x] Remove or defer controls that the selected route cannot support:
      minimum size, weekly transition window, report type, topic granularity,
      fake platform “Both”, and unimplemented search/sort controls.
- [x] Replace the fixed month fallback values with a no-runs or loading state.
- [x] Show API health and run verification as compact status badges. A failed
      verification must block analytical panels and explain why.
- [x] Remove the fake notification dot and inert help button, or connect Help to
      the Methodology route.
- [x] Replace “Create Report” with no action. Reports are read-only artifacts.
- [x] Make icon-only buttons accessible with visible or `aria-label` names.
- [x] Keep mobile sidebar behavior and the current top-bar visual structure.

Validation:

```bash
cd frontend
npm run test -- --run Topbar
npm run typecheck
npm run lint
```

## Milestone 2 — Make Sidebar Navigation Honest and Complete

Tasks:

- [x] Preserve existing routes and active-route highlighting.
- [x] Ensure Methodology is reachable through the same navigation system.
- [x] Remove Settings until a real settings page exists.
- [x] Remove hard-coded researcher identity/avatar information. A neutral product
      footer or version label is acceptable.
- [x] Add text/tooltips for collapsed navigation icons.
- [x] Ensure focus order, keyboard activation, and mobile overlay dismissal work.
- [x] Add a skip link to the main content.

## Milestone 3 — Implement Overview Queries and Data Mapping

Use these sources:

- `overview`: primary KPI and top-theme data;
- `network`: bounded graph preview for selected metric;
- `communities`: top communities by `total_weight`, `node_count`, or
  `edge_count`;
- `themes`: optional enrichment of community rows;
- `transitions`: optional only for a run containing longitudinal artifacts.

Tasks:

- [x] Create an Overview feature hook that queries only when a valid, verified
      run is selected.
- [x] Use query keys containing run ID and metric.
- [x] Map API fields without renaming their meaning:
      - total users;
      - total messages;
      - total interactions;
      - IF/WIF community count according to selected metric;
      - matched community count and percentage;
      - persistent community count when available.
- [x] Choose four to six KPI cards based on supported values. Do not show a trend
      arrow unless a real comparison period has been selected and calculated.
- [x] Render `null` values as “Unavailable for this run,” not zero.
- [x] Add source/formula tooltips that identify the API field and selected metric.
- [x] Render top themes directly from `overview.top_themes` and show provider/model
      metadata separately; do not imply GPT generated the analytical topics.

## Milestone 4 — Replace Mock Overview Visuals

### Network preview

- [x] Pass `NetworkResponse` into the graph component.
- [x] Remove random node/edge generation.
- [x] Use node IDs and edges from the response.
- [x] Color nodes deterministically by community ID.
- [x] Size nodes by degree within the returned bounded graph, labelled as a
      presentation encoding rather than a thesis metric.
- [x] Display `returned_nodes/available_nodes`,
      `returned_edges/available_edges`, and a “sampled” badge when applicable.
- [x] Show an empty state for no edges/nodes.

### Evolution panel

- [x] The current fixed time-series data cannot be shown for a single monthly run.
      Replace the panel with one of these, in order:
      1. a run-history chart derived from compatible runs in the catalog;
      2. a compact run summary/configuration panel when fewer than two compatible
         runs exist.
- [x] Do not render fixed 2024 values.
- [x] Label run-derived time series as separate completed runs, not a continuous
      dynamic model.

### Platform comparison panel

- [x] Remove it from the Overview or replace it with a run provenance/config card.
      A true Twitter-vs-Telegram comparison requires explicit run selection and
      belongs on the Comparative route.

### Transition panel

- [x] Query transitions only when the selected run lists the required artifact.
- [x] If present, render a small real transition summary or Sankey.
- [x] If absent, render `ArtifactUnavailableState` with a link to the Evolution or
      Methodology explanation.
- [x] Remove the hand-drawn fixed SVG ribbons and percentages.

## Milestone 5 — Replace the Mock Community Table

Tasks:

- [x] Map `CommunitiesResponse.communities` to table rows using only:
      `community_id`, `node_count`, `edge_count`, and `total_weight`.
- [x] Optionally enrich rows with a theme only when a theme record can be matched
      unambiguously to the same metric/community ID.
- [x] Remove fake platform, messages, persistence, trend, diversity, and starred
      values.
- [x] Add sorting for supported columns and a “View in Network” link that sets the
      selected community in URL state and navigates to `/network`.
- [x] Add pagination when more than the first page is needed.
- [x] Show the metric in the table heading or column labels.

## Milestone 6 — Generate Deterministic, Traceable Insights

Tasks:

- [x] Replace `RightSidebar` hard-coded prose with deterministic rules based on
      visible data, for example:
      - IF/WIF matched percentage above/below a documented threshold;
      - network response is sampled;
      - a top theme dominates a large fraction of returned theme counts;
      - no persistent-community artifact exists.
- [x] Each insight must include the supporting value and use neutral language.
- [x] Do not call an LLM from the frontend or backend for dashboard prose.
- [x] If there are no meaningful rules triggered, show run provenance and
      configuration instead of filler text.

## Milestone 7 — Implement Real Export Behavior

Tasks:

- [x] Rename the top action according to actual behavior:
      - “Export visible communities” for client-generated CSV; or
      - “Download artifact” for manifest-backed downloads.
- [x] For visible-table export, use exactly the currently filtered/sorted real
      records and selected metric. Include run ID and date in the filename.
- [x] For artifact download, present available records from `/artifacts` and use
      `/downloads/{artifact_key}`.
- [x] Remove fields that do not exist in the response.
- [x] Revoke generated object URLs after download.

## Tests

Add component/integration tests for:

- [x] initial loading and no-runs state;
- [x] default completed-run selection;
- [x] URL-selected run restoration;
- [x] switching run invalidates Overview data;
- [x] IF/WIF switch changes query and labels;
- [x] failed verification blocks panels;
- [x] `null` overview values show unavailable;
- [x] sampled graph badge;
- [x] optional transitions missing;
- [x] export contains only real visible fields;
- [x] no mock fallback appears when API records are empty.

## Acceptance Criteria

- [x] Overview displays only canonical API data or explicit states.
- [x] Run and metric controls visibly change requests and content.
- [x] No fixed month, random graph, fake trend, fake platform comparison, or
      mock community row remains on the Overview.
- [x] All primary cards have traceable source fields.
- [x] Export produces a real CSV or downloads a manifest-listed artifact.
- [x] Navigation is keyboard accessible and free of inert visible controls.
- [x] Relevant tests, typecheck, lint, and build pass.

## Risks

| Risk | Mitigation |
|---|---|
| Overview becomes visually sparse for a one-month run. | Use provenance, configuration, verification, top themes, and explicit unavailable states rather than fabricated charts. |
| Community-to-theme IDs do not align. | Enrich only when matching is unambiguous; otherwise display structural fields only. |
| Large graph preview impacts performance. | Request conservative caps and lazy-load the graph component. |

## Rollback Plan

Revert the feature branch. Do not restore mock values. If a visual cannot be
functionalized, replace it with an explicit unavailable card until its later
feature plan rather than reintroducing fabricated data.

## Progress Log

| Date | Update |
|---|---|
| 2026-07-18 | Plan created. |
| 2026-07-18 | Baseline recorded: frontend lint passed with 20 warnings, typecheck and 12 tests passed, and production build passed with the existing large-chunk warning. |
| 2026-07-18 | Replaced the shell's mock controls with run/metric selectors, verification and health badges, query-preserving navigation, a skip link, and a neutral read-only footer. |
| 2026-07-18 | Added run-scoped Overview queries, canonical KPI mapping, deterministic network rendering, compatible-run history, provenance, top themes, optional transition handling, real community pagination/sorting/export, and traceable insights. |
| 2026-07-18 | Added 15 new frontend tests covering shell states, verification gating, selectors, query keys, graph sampling, empty states, theme mapping, CSV export, and navigation. Final frontend result: 27 tests passed; typecheck, lint, and build passed. Backend API result: 10 tests passed. |
| 2026-07-18 | Plan 031 quality integration added canonical fixture coverage, strict source guards, route-level lazy loading, zero-warning lint, focused coverage, bundle budgets, real-service Playwright/axe workflow definitions, and release documentation. Browser execution remains pending in a browser-capable environment. |


## Implementation Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-07-18 | Render a compact transition-link summary instead of a full Sankey on Overview. | It uses the canonical transition rows without duplicating the full transition explorer reserved for the dedicated route. |
| 2026-07-18 | Place “Export visible communities” in the community table header rather than the persistent top bar. | The table owns the current sorted/paginated records, which prevents exporting stale or fabricated cross-route data. |
| 2026-07-18 | Build run history from at most 12 completed runs sharing platform and content type. | Keeps the Overview query bounded and labels the points as independent completed runs. |
| 2026-07-18 | Do not add backend routes or fields. | The existing read-only API contract contains every value required by this plan. |

## Validation Record

```text
python -m pytest -q tests/unit/test_backend_api.py     10 passed
cd frontend && npm run typecheck                       passed
cd frontend && npm run test -- --run                   27 passed
cd frontend && npm run lint                            0 errors, 11 pre-existing warnings
cd frontend && npm run build                           passed; existing >500 kB chunk warning remains
```
