# Plan 030 — Evolution, Comparison, Reports, and Methodology

Status: complete

Owner: agent

Last updated: 2026-07-18

## Goal

Functionalize the longitudinal, comparative, report, and methodology routes
using canonical run artifacts, explicit compatible-run selection, and resolved
run metadata. Remove report CRUD and all fixed narrative/diagram data.

## Dependencies

- Plans 026–029 are complete.
- Run catalog, overview, structural, semantic, and evolution clients are stable.
- Reusable table, state, metadata, and similarity components exist.

## Non-Goals

- No dynamic community detection or re-analysis in API requests.
- No report scheduling, generation, editing, deletion, or sharing backend.
- No LLM-generated dashboard insights.
- No comparison across incompatible definitions without a visible warning.
- No claims beyond the selected run artifacts.

## Files Expected To Change

- `frontend/src/pages/EvolutionOverTime.jsx`
- `frontend/src/pages/CommunityTransitions.jsx`
- `frontend/src/pages/ComparativeAnalysis.jsx`
- `frontend/src/pages/Reports.jsx`
- `frontend/src/pages/Methodology.jsx`
- `frontend/src/components/charts/EvolutionChart.jsx`
- `frontend/src/components/charts/PlatformComparison.jsx`
- `frontend/src/components/charts/TransitionsSankey.jsx`
- `frontend/src/features/evolution/` (new)
- `frontend/src/features/comparison/` (new)
- `frontend/src/features/reports/` (new)
- `frontend/src/features/methodology/` (new)
- relevant tests
- `docs/exec-plans/active/030-evolution-comparison-reports-methodology.md`

## Milestone 1 — Define Compatible Run Grouping

Tasks:

- [x] Build utilities that group completed runs by platform and content type,
      sorted by `date_start`.
- [x] For a time series, require at least two compatible runs with the same
      platform and content type. Surface differences in algorithm configuration
      from `overview.config_metadata` as warnings.
- [x] For cross-platform comparison, require explicit left and right run
      selections. Default candidates may be suggested, but never silently compare
      arbitrary first records.
- [x] Display date ranges, content types, status, and selected metric for both
      runs.
- [x] Define compatibility warnings for:
      - different content types;
      - different date windows;
      - different graph thresholds;
      - different Louvain or LDA settings;
      - missing artifact categories.
- [x] Warnings do not prohibit exploration unless the metrics are semantically
      incomparable; they prevent misleading conclusions.

## Milestone 2 — Implement Evolution Over Time from Run History

Tasks:

- [x] Query `/overview` for compatible runs with TanStack `useQueries` and a
      conservative concurrency strategy.
- [x] Build real time-series points for supported values such as total users,
      total messages, total interactions, IF/WIF community count, matched
      percentage, and persistent-community count.
- [x] Let the user select one metric at a time or a small compatible set. Do not
      plot quantities with incompatible units on the same axis.
- [x] Use actual run dates on the x-axis; remove all fixed May 2024 data and
      annotations.
- [x] Add a tabular fallback and accessible summary.
- [x] Explicitly label missing values and exclude them from misleading trend
      calculations.
- [x] Deterministic trend notes may state arithmetic changes between selected
      endpoints. Include both values and dates.

## Milestone 3 — Implement Community Transitions and Membership Change

Tasks:

- [x] Query transitions, persistent communities, membership changes, and theme
      similarity independently so one missing optional artifact does not fail the
      whole page.
- [x] Build Sankey nodes from `(month, community_id)` pairs and links from
      transition records. Use Jaccard score or common-member count as the link
      encoding and state which one is used.
- [x] If Recharts Sankey is sufficient, keep the current chart dependency. Add a
      new library only if the existing library cannot meet accessibility and data
      requirements.
- [x] Provide a transition table with start/end month, start/end community,
      Jaccard, and member counts.
- [x] Render persistent community cards/table with duration, transition count,
      and average Jaccard.
- [x] Render membership changes using retained, joined, exited, start, and end
      counts. Do not invent “reappearing” counts because the current API response
      does not expose them directly.
- [x] Use the similarity matrix/artifacts as defined in Plan 029.
- [x] Replace the current 400-line fixed transition visualization and all fixed
      percentages/narrative.
- [x] Export transition or membership tables as visible real CSV when requested.

## Milestone 4 — Build Honest Cross-Platform Comparison

Tasks:

- [x] Add explicit selectors for a Twitter run and a Telegram run. Limit options
      to those platforms and show content type/date range.
- [x] Compare only shared Overview fields:
      - total users;
      - total messages;
      - total interactions;
      - selected-metric community count;
      - matched community count/percentage;
      - persistent community count when present;
      - top theme labels/counts.
- [x] Remove the current fabricated persistence score and thematic-diversity bars.
- [x] Theme comparison may show top-theme sets and overlap of exact normalized
      names. Label this as label overlap, not message-volume overlap or semantic
      similarity.
- [x] Do not show a Venn diagram claiming shared message percentages because the
      API does not provide cross-platform message-level overlap.
- [x] Add configuration/compatibility panels so the analyst sees differences in
      graph, Louvain, LDA, provider, and similarity settings.
- [x] Generate deterministic findings from visible differences only, with values
      and no causal claims.

## Milestone 5 — Convert Reports into a Read-Only Artifact Library

Tasks:

- [x] Remove hard-coded report records, create/schedule buttons, progress states,
      authors, report-type CRUD, and fake pagination.
- [x] Query `/artifacts` for the selected run and group by category/stage/media
      type.
- [x] Show artifact key, path, category, schema version, rows, bytes, stage, and
      verification status.
- [x] Offer inline “Open report” only when `/report` is available.
- [x] Offer download only through `/downloads/{artifact_key}` and omit/disable
      intermediate artifacts.
- [x] Surface backend errors for missing/tampered artifacts.
- [x] Add filters that actually operate on artifact metadata.
- [x] Use browser-native links for files so content disposition and media type are
      handled by the backend.

## Milestone 6 — Make Methodology Run-Aware

Tasks:

- [x] Preserve the current methodology information architecture and thesis
      pipeline diagram.
- [x] Separate two sections:
      1. thesis baseline/default methodology;
      2. selected run's resolved configuration and provider/model metadata.
- [x] Baseline values must match repository contracts:
      graph thresholds, Louvain defaults, LDA defaults, IF/WIF definitions, and
      temporal similarity behavior.
- [x] Selected-run values must come from `/overview.config_metadata`,
      `/overview.model_metadata`, and `/runs/{run_id}`. Do not hard-code GPT-4.
- [x] Explain that themes are downstream of LDA keywords and that the dashboard
      is read-only over artifacts.
- [x] Show selected platform/content type/date range and available artifact
      categories.
- [x] Link methodology terms to the corresponding dashboard routes.
- [x] Add a note when selected-run metadata is absent rather than assuming
      defaults were used.

## Tests

- [x] compatible run grouping and date sorting;
- [x] missing run-history values;
- [x] configuration mismatch warnings;
- [x] Sankey view-model construction;
- [x] transitions, persistent communities, membership changes independently
      unavailable;
- [x] cross-platform selectors and supported metric comparison;
- [x] no unsupported Venn/message-overlap claim;
- [x] artifact category filtering and download URLs;
- [x] intermediate artifact download suppression;
- [x] methodology baseline values and selected-run overrides;
- [x] non-OpenAI provider/model rendering.

## Acceptance Criteria

- [x] Evolution and transitions contain no fixed dates, values, community IDs, or
      narratives.
- [x] Cross-platform comparison requires explicit runs and uses only comparable
      supported fields.
- [x] Reports is a real read-only artifact library.
- [x] Methodology accurately distinguishes thesis defaults from selected-run
      metadata.
- [x] Missing optional longitudinal artifacts degrade panel-by-panel.
- [x] Tests, typecheck, lint, and build pass.

## Decision Log

| Date | Decision | Reason |
|---|---|---|
| 2026-07-18 | Treat run history as a sequence of separate completed snapshots grouped by exact platform and content type. | This supports longitudinal inspection without implying a continuous dynamic model or combining incompatible interaction definitions. |
| 2026-07-18 | Cap overview history requests to the 12 most recent compatible runs and use run-aware TanStack Query keys. | The bounded catalog slice keeps request volume predictable while preserving enough snapshots for the dashboard view. |
| 2026-07-18 | Require explicit Twitter/X and Telegram run selections for comparison. | Arbitrary first-run comparison would be misleading; selected runs and compatibility warnings must remain visible. |
| 2026-07-18 | Encode transition Sankey links with saved Jaccard membership similarity and cap the rendered links at 60. | This uses a thesis-defined artifact field and keeps the visualization readable while retaining canonical rows and totals in the table. |
| 2026-07-18 | Keep Reports read-only and use browser-native report/download URLs. | The backend owns media type, content disposition, verification, and intermediate-artifact restrictions. |
| 2026-07-18 | Separate protected thesis defaults from selected-run metadata. | Missing metadata must be shown as unavailable rather than silently replaced by defaults or an assumed provider. |
| 2026-07-18 | Make no backend route, schema, analytical metric, algorithm-default, or pipeline changes. | Existing canonical API and artifact contracts were sufficient for Plan 030. |

## Risks

| Risk | Mitigation |
|---|---|
| Only one compatible run exists. | Show an explanatory state and selected-run summary rather than a fake time series. |
| Transition volume overwhelms Sankey. | Apply a documented display cap/top-link filter while preserving the full paginated table and total. |
| Cross-platform datasets differ materially. | Show compatibility warnings and avoid causal/statistical claims. |
| HTML report absent. | Keep artifact inventory functional and show report unavailable. |

## Rollback Plan

Revert this feature branch. Earlier functional routes remain. Any blocked
longitudinal visualization should be replaced with the real transition table and
an unavailable visualization state, not the old static diagram.

## Progress Log

| Date | Update |
|---|---|
| 2026-07-18 | Plan created. |
| 2026-07-18 | Confirmed `HARNESS.md` and root `ARCHITECTURE.md` are absent from the uploaded source, then reviewed repository contracts, Plans 026–029, API schemas/routes/services, and the existing longitudinal, comparison, report, and methodology routes. |
| 2026-07-18 | Added compatible-run grouping, bounded overview history queries, configuration warnings, real run-date series, accessible tables, deterministic endpoint comparisons, and explicit missing-value handling. |
| 2026-07-18 | Replaced fixed transition diagrams and narratives with canonical transition, persistence, membership-change, and theme-similarity panels that fail independently; added Jaccard Sankey construction and real CSV exports. |
| 2026-07-18 | Rebuilt cross-platform comparison around explicit Twitter/X and Telegram run selections, shared overview fields, exact normalized theme-label overlap, resolved configuration/model metadata, and non-causal arithmetic findings. |
| 2026-07-18 | Converted Reports to a filtered manifest-backed artifact library and made Methodology distinguish protected thesis defaults from selected-run configuration, provider/model metadata, and artifact categories. |
| 2026-07-18 | Added compatibility, history, Sankey, comparison, artifact-library, methodology, unavailable-panel, selector, and page integration tests. |
| 2026-07-18 | Validation: backend API tests 10 passed; frontend typecheck passed; lint completed with 0 warnings and 0 errors; 36 frontend test files / 74 tests passed; production build passed. The existing Vite main-chunk size warning remains deferred to the frontend quality/performance plan. |
| 2026-07-18 | Plan 031 quality integration added canonical fixture coverage, strict source guards, route-level lazy loading, zero-warning lint, focused coverage, bundle budgets, real-service Playwright/axe workflow definitions, and release documentation. Browser execution remains pending in a browser-capable environment. |
