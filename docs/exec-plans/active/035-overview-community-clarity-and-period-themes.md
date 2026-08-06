# Execution Plan 035 — Overview Community Clarity, Monthly Themes, and Continuity Timeline

Status: implemented — browser validation blocked by package gateway

Owner: agent

Last updated: 2026-08-01

## Goal

Improve the Overview page so that its three analytical summaries are truthful, readable, and period-aware without changing any thesis metric, algorithm default, source artifact, or downstream LDA-to-theme relationship.

This plan delivers:

1. a reliable **Community Landscape** for monthly community summaries;
2. a **Top Five Themes for the Selected Month** panel with explicit community counts and LDA keyword evidence;
3. a readable **Community Continuity Timeline** in place of the Overview Sankey.

## Source of Truth

Use the uploaded archive as the implementation baseline:

```text
community-analysis-latest-20260801-1629.zip
```

Do not reconstruct the work from commit `b07b1ec` alone. The archive contains later staged and unstaged project work and is the current source of truth.

Before editing, read the repository documentation in the required order:

1. `HARNESS.md`
2. `ARCHITECTURE.md`
3. `docs/design-docs/current-code-feature-inventory.md`
4. `docs/product-specs/project-spec.md`
5. `docs/design-docs/data-contract.md`
6. `docs/design-docs/database-contract.md`
7. `docs/design-docs/metric-contract.md`
8. `docs/design-docs/pipeline-contract.md`
9. `docs/design-docs/theme-intelligence-contract.md`
10. `docs/verification/quality-gates.md`
11. `docs/verification/test-matrix.md`
12. `docs/exec-plans/active/033-overview-monthly-dashboard.md`
13. `docs/exec-plans/active/034-overview-community-network-and-central-actors.md`
14. This plan.

## Existing Findings to Preserve

- The monthly community-summary API returns one node per prominent community and intentionally returns no cross-community edges.
- Canonical community graph artifacts contain induced within-community edges only. Inter-community links must not be inferred or fabricated.
- The current Community Structure Map sends disconnected community nodes into `react-force-graph-2d`; this is both visually fragile and semantically misleading as a network map.
- `OverviewResponse.top_themes` is a run-wide exact-label occurrence count. Other pages currently consume it, so its API behavior must remain backward compatible.
- The Overview already fetches the selected month’s theme records through `themesQuery`.
- Theme labels are downstream of LDA keywords and must remain presented as such.
- The current Sankey uses Jaccard as the link `value`, although Sankey width represents flow volume. This creates wide, visually similar bands and obscures community identities.
- Transition artifacts already contain community IDs, member totals, common members, and Jaccard scores.

## Locked Product Decisions

### Community summary

- Rename the Overview community visualization to **Community Landscape**.
- Render it as deterministic, responsive SVG/HTML rather than a force simulation.
- One visible bubble/tile represents one published prominent community.
- Relative area encodes member count.
- Color intensity encodes total IF/WIF internal weight.
- Border width encodes internal edge count.
- Every community has a visible `C<community_id>` label.
- Clicking a community opens the existing bounded user subgraph for that month and metric.
- The user-level graph continues to use `react-force-graph-2d`.

### Monthly theme summary

- Replace the Overview’s **Run-wide Top Themes** card with **Top Themes · <Selected Month>**.
- Display the top five exact general theme labels for the selected month.
- Count distinct matched IF/WIF community pairs associated with each label, not raw repeated label cells.
- Show `community_count / total_themed_community_pairs` and the corresponding percentage.
- Show up to three supporting LDA keywords aggregated from the records carrying that label.
- Do not silently merge synonymous or similar labels.
- If the selected-month response is incomplete because `response.total > response.records.length`, do not display a partial ranking. Show an explicit safe-cap message and link to Thematic Analysis.
- Keep `OverviewResponse.top_themes` unchanged for backward compatibility and comparison pages.
- Remove the large provider/model footer from this card; provider/model remains available in Run Configuration and Thematic Analysis.

### Community continuity

- Replace the Overview Sankey with **Community Continuity Timeline**.
- Group transitions into connected persistent paths using only canonical transition records.
- Horizontal position encodes month.
- Node size encodes the authoritative community member total.
- Link width encodes retained/common-member count when available.
- Link color or opacity encodes Jaccard membership similarity.
- Node labels show `C<id>` and member count.
- Link details show start/end community, retained count, start/end sizes, and Jaccard.
- Display at most five persistent paths on Overview, ranked by:
  1. number of distinct months, descending;
  2. total retained members, descending;
  3. stable earliest month/community key.
- Preserve configured transition thresholds. This is presentation only; do not recompute community similarity or alter the transition artifact.
- Load up to the existing API maximum of 1,000 transition records. If the server reports more records than were returned, show an explicit incomplete-summary state instead of ranking a partial graph.
- Keep the dedicated Community Transitions route unchanged in this plan except for any shared model/test fixes required to preserve compatibility.

## Non-Goals

- Do not publish or synthesize cross-community edges.
- Do not change `shared_post`, `weighted_post`, graph thresholds, Louvain defaults, LDA defaults, Jaccard thresholds, or theme-generation settings.
- Do not alter or regenerate canonical analytical artifacts.
- Do not merge theme labels using embeddings, fuzzy matching, GPT, or frontend heuristics.
- Do not make OpenAI, TEI, Memgraph, or any external service call during tests.
- Do not redesign the entire Network, Themes, or Community Transitions pages.
- Do not introduce a new charting dependency unless the current stack proves technically incapable; custom SVG is preferred.
- Do not remove the run-wide `top_themes` API field.

## Files Expected to Change

The exact list may be narrowed after inspection, but changes should remain close to these files.

### Community Landscape

- `frontend/src/components/charts/NetworkGraph.jsx`
- `frontend/src/components/charts/CommunityLandscape.tsx` — new
- `frontend/src/features/networks/communityLandscapeModel.ts` — new
- `frontend/src/components/charts/__tests__/NetworkGraph.test.jsx`
- `frontend/src/components/charts/__tests__/CommunityLandscape.test.tsx` — new
- frontend stylesheet containing Overview/chart component classes

### Selected-month themes

- `frontend/src/features/overview/TopThemesPanel.tsx`
- `frontend/src/features/themes/themeModel.ts`
- `frontend/src/features/themes/__tests__/themeModel.test.ts` or existing equivalent
- `frontend/src/features/overview/__tests__/OverviewPanels.test.tsx`
- `frontend/src/pages/Overview.jsx`

### Community Continuity Timeline

- `frontend/src/components/charts/CommunityContinuityTimeline.tsx` — new
- `frontend/src/features/evolution/continuityModel.ts` — new
- `frontend/src/features/evolution/__tests__/continuityModel.test.ts` — new
- `frontend/src/pages/Overview.jsx`
- `frontend/src/features/overview/useOverviewData.ts`
- `frontend/src/pages/__tests__/Overview.test.jsx`

### Documentation and verification

- `docs/exec-plans/active/035-overview-community-clarity-and-period-themes.md`
- `docs/verification/test-matrix.md`
- `docs/HANDOFF.md`
- API/OpenAPI fixtures only if an API contract must change; an API change is not expected for the preferred implementation.

## Milestones

### Milestone 1 — Protect and reproduce current behavior

Tasks:

- [x] Copy this plan into `docs/exec-plans/active/`.
- [x] Inspect the exact Overview component tree, query flow, response types, and existing tests before editing.
- [ ] Record a current screenshot or Playwright snapshot of the three target panels when the frontend can run.
- [x] Add/confirm a regression fixture for a community response with nodes and zero links.
- [x] Add/confirm fixtures for:
  - selected-month theme records with repeated labels;
  - multiple labels on one matched community pair;
  - missing general labels with IF/WIF fallback labels;
  - an incomplete paginated theme response;
  - transitions spanning two, three, and four months;
  - missing `common_members`;
  - an incomplete transition response.
- [x] Confirm that existing run-wide `OverviewResponse.top_themes` tests remain unchanged.

Validation:

```bash
python -m pytest -q tests/unit/test_overview_monthly_services.py tests/unit/test_backend_api.py
cd frontend
npm run test -- --run \
  src/components/charts/__tests__/NetworkGraph.test.jsx \
  src/features/overview/__tests__/OverviewPanels.test.tsx \
  src/features/evolution/__tests__/transitionModel.test.ts
```

### Milestone 2 — Replace the disconnected force graph with Community Landscape

Tasks:

- [x] Create a pure model function that converts community nodes into deterministic visual items.
- [x] Sort communities by member count descending, then stable community ID.
- [x] Use square-root scaling for relative area while enforcing readable minimum and maximum sizes.
- [x] Use a deterministic non-overlapping responsive grid or packed layout. Do not run a force simulation.
- [x] Normalize internal weight and internal edge count independently for color intensity and border width.
- [x] Render visible labels and keyboard-focusable community controls.
- [x] Add a tooltip/details panel with:
  - local community ID;
  - member count;
  - internal edge count;
  - total IF/WIF internal weight;
  - month and metric-local scope wording.
- [x] Preserve click-through to the existing user-level community drill-down.
- [x] Branch in `NetworkGraph`:
  - `view=communities` renders `CommunityLandscape`;
  - `view=users` lazy-loads and renders `react-force-graph-2d`.
- [x] Do not load the force-graph bundle for community view.
- [x] Preserve honest coverage metadata and the no-cross-community-link explanation.
- [x] Rename all visible Overview text from “Community Structure Map” to “Community Landscape.”

Validation:

```bash
cd frontend
npm run test -- --run \
  src/components/charts/__tests__/CommunityLandscape.test.tsx \
  src/components/charts/__tests__/NetworkGraph.test.jsx
npm run typecheck
```

Acceptance checks:

- A response containing one or more community nodes and zero edges always renders visible communities.
- Every community is reachable with keyboard navigation.
- Labels remain readable at common desktop widths and do not require a hover-only interaction.
- The user-level force graph still renders bounded user nodes and edges exactly as before.

### Milestone 3 — Add selected-month top-five theme summary

Tasks:

- [x] Add a pure `selectedMonthThemeSummary`/equivalent model helper using `ThemesResponse`.
- [x] Normalize theme records using the existing `adaptThemeRecord` logic.
- [x] Define the authoritative matched-pair key as normalized `absolute_community + weighted_community`.
- [x] Exclude rows that have neither community ID from the denominator; report the excluded count in model metadata for testing/debugging.
- [x] Deduplicate repeated labels within one matched pair before counting.
- [x] Count the number of distinct matched pairs carrying each exact general label.
- [x] Use general labels first; fall back to the deduplicated union of IF/WIF labels only when a general label is absent.
- [x] Compute percentage as:

```text
community pairs carrying the label / total themed matched community pairs
```

- [x] Aggregate and rank supporting keywords only from records carrying that exact label.
- [x] Normalize keyword case/whitespace for counting while retaining a stable display form.
- [x] Return the top five labels ordered by community count descending, then label ascending.
- [x] Update `TopThemesPanel` props to receive:
  - selected period;
  - selected-month `ThemesResponse`;
  - loading/error/artifact state.
- [x] Display each row with:
  - full theme label, wrapping to two lines rather than destructive truncation;
  - `N of M themed communities`;
  - percentage;
  - up to three LDA keyword chips;
  - accessible tooltip/title for the complete label.
- [x] Use the selected month in the heading.
- [x] Remove the oversized provider/model footer.
- [x] Keep the text “Theme labels remain downstream of LDA keywords.”
- [x] If the response is incomplete, render no frequency bars and explain that a partial ranking would be misleading.
- [x] Keep `overview.top_themes` untouched and keep comparison-page behavior passing.

Validation:

```bash
cd frontend
npm run test -- --run \
  src/features/themes/__tests__/themeModel.test.ts \
  src/features/overview/__tests__/OverviewPanels.test.tsx \
  src/pages/__tests__/Overview.test.jsx \
  src/features/comparison/__tests__/comparisonModel.test.ts
npm run typecheck
```

Acceptance checks:

- Changing the Overview month changes the theme ranking.
- The denominator is explicitly the number of themed matched community pairs.
- One community pair contributes at most once to a given theme.
- Multiple themes assigned to one community pair are allowed; percentages therefore need not sum to 100%, and the explanatory copy states this.
- No semantic label merging occurs.
- LDA evidence is visible for every ranked theme when keywords exist.

### Milestone 4 — Replace the Overview Sankey with Community Continuity Timeline

Tasks:

- [x] Increase the Overview transition query limit from 100 to 1,000, the current API maximum.
- [x] Add a pure continuity model that:
  - creates month/community nodes;
  - groups connected components using transition links;
  - validates member-count consistency for repeated nodes;
  - derives retained count only from canonical `common_members`;
  - never estimates retained count from Jaccard;
  - calculates component duration and total retained members;
  - ranks components according to the locked decision above.
- [x] Use canonical transition rows only. Do not call NetworkX and do not recompute Jaccard.
- [x] Create a responsive SVG timeline with month columns and one row per persistent path.
- [x] Show at most five paths on Overview.
- [x] Render nodes as labelled community markers with member totals.
- [x] Render link width from retained count when available; otherwise use a minimal neutral width and label it unavailable.
- [x] Render Jaccard through color/opacity and include a visible legend.
- [x] Add hover/focus details containing:
  - start and end month/community;
  - retained members;
  - start member total;
  - end member total;
  - Jaccard score.
- [x] Replace the Overview `TransitionsSankey` import/render with `CommunityContinuityTimeline`.
- [x] Keep “Open transitions” linking to the dedicated route.
- [x] Show `N of M persistent paths` rather than `N of M links`.
- [x] If `response.total > response.records.length`, do not rank a partial graph; show an explicit incomplete-summary state.
- [x] Keep the current dedicated Community Transitions page and its export behavior unchanged.

Validation:

```bash
cd frontend
npm run test -- --run \
  src/features/evolution/__tests__/continuityModel.test.ts \
  src/pages/__tests__/Overview.test.jsx \
  src/pages/__tests__/CommunityTransitionsPlan030.test.jsx \
  src/features/evolution/__tests__/transitionModel.test.ts
npm run typecheck
```

Acceptance checks:

- Month names are human-readable and ordered chronologically.
- Community IDs and member totals are visible without opening a tooltip.
- Wider links mean more retained members, not higher Jaccard.
- Stronger color/opacity means higher Jaccard.
- Persistent paths can be followed with the naked eye from left to right.
- A four-month path appears as one row rather than unrelated bands.
- The existing transition threshold and records are unchanged.

### Milestone 5 — Overview integration, accessibility, and responsive behavior

Tasks:

- [x] Rebalance the Overview card layout so the themes card no longer stretches to match a very tall transition chart.
- [ ] Ensure the three panels work at desktop, tablet, and narrow mobile widths.
- [x] Add visible legends and concise methodology copy without overcrowding the cards.
- [x] Ensure all SVG marks have accessible names or corresponding HTML summaries.
- [ ] Verify focus order, keyboard activation, contrast, and tooltip alternatives.
- [x] Ensure period playback stops when the user interacts with the community or transition visualization.
- [x] Preserve URL-backed month, metric, network view, sampling, and community state.
- [x] Avoid new network requests on ordinary hover/focus interactions.

Validation:

```bash
cd frontend
npm run lint
npm run typecheck
npm run test -- --run
npm run build
npm run bundle:check
npm run test:e2e
```

If `npm ci` or Playwright remains blocked by the package gateway, record the exact package/status in the plan validation log and still run every locally available static and unit check.

### Milestone 6 — Full validation, documentation, and patch

Tasks:

- [x] Run repository formatting/linting/tests that are available without external services.
- [x] Run focused backend tests to confirm no API/analytical regression.
- [x] Update `docs/verification/test-matrix.md` with the new model and component coverage.
- [x] Update `docs/HANDOFF.md` to explain:
  - Community Landscape encodings;
  - selected-month theme denominator;
  - continuity timeline encodings and limits.
- [x] Update this plan’s progress and decision logs.
- [x] Run `git diff --check`.
- [x] Produce one surgical patch from the uploaded archive baseline.
- [x] Provide a concise summary of changed files, validation results, and known blockers.

Validation:

```bash
make format
make lint
make test
cd frontend && npm run check
cd ..
git diff --check
```

Do not treat TEI, Memgraph, provider, or other external-service failures as frontend regressions. Report them separately and do not weaken those production contracts to make tests pass offline.

## Acceptance Criteria

- [x] Community view always renders published communities even when `edges=[]`.
- [x] Community view does not instantiate a force simulation or fabricate links.
- [x] Community area, internal weight, and internal edge encodings are documented and visible in a legend/tooltip.
- [x] Community click-through opens the existing month/metric-local bounded user graph.
- [x] Overview themes are selected-month top five, not run-wide top five.
- [x] Theme counts are distinct matched community-pair counts.
- [x] The total themed-community denominator is displayed.
- [x] Supporting LDA keywords are displayed downstream of the exact theme label.
- [x] Run-wide `OverviewResponse.top_themes` remains backward compatible.
- [x] The Overview transition visualization is a readable continuity timeline.
- [x] Timeline width represents retained-member count, while color/opacity represents Jaccard.
- [x] Month, community ID, and member total are directly visible.
- [x] Overview shows no ranking from incomplete theme or transition pages.
- [x] IF and WIF remain separate everywhere they are metric-specific.
- [x] No thesis metric, algorithm default, artifact schema, or provider behavior changes.
- [x] No paid or external provider calls occur in automated tests.
- [ ] Targeted frontend tests, typecheck, lint, and build pass when dependency installation is available.
- [x] The implementation is delivered as a surgical patch against the uploaded archive.

## Decision Log

| Date | Decision | Reason |
|---|---|---|
| 2026-08-01 | Use deterministic SVG/HTML for the community summary and retain force graph only for user edges. | Community artifacts contain no cross-community edges, so a force-directed network is neither necessary nor semantically accurate. |
| 2026-08-01 | Show top five exact labels for the selected month. | The Overview is period-aware; one top theme loses distributional context, while run-wide counts hide month-level change. |
| 2026-08-01 | Count distinct matched IF/WIF community pairs. | Theme artifacts are generated for matched community records, and raw label-cell counts can overstate community prevalence. |
| 2026-08-01 | Do not merge related labels. | Theme standardization would be a new semantic transformation and must not be introduced silently in the frontend. |
| 2026-08-01 | Use retained members for link width and Jaccard for color/opacity. | Retained members are a flow-like quantity; Jaccard is similarity and should not determine Sankey/timeline width. |
| 2026-08-01 | Keep the dedicated transition page out of scope. | The current request is an Overview improvement; limiting the change reduces regression risk. |

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Many community bubbles become crowded. | Use a deterministic non-overlapping grid/packed layout, visible labels, responsive scrolling, and a bounded minimum label size. |
| Visual minimum bubble size weakens exact area perception. | Label all member counts and describe area as relative rather than exact. |
| Theme labels are semantically fragmented. | Preserve exact labels and expose LDA keywords; defer explicit standardization to a separately approved analytical plan. |
| A month contains more than 500 theme records. | Refuse to show a partial ranking; display an explicit safe-cap state. A server-side aggregate endpoint can be proposed later if this occurs in real runs. |
| A run contains more than 1,000 transitions. | Refuse to rank a partial graph and report the limit; defer an additive server-side continuity-summary endpoint. |
| `common_members` is absent. | Do not infer retained counts. Use neutral minimum link width and state that retained count is unavailable. |
| Member totals conflict for the same month/community node. | Mark the node inconsistent and surface the conflict in tests/UI diagnostics rather than silently reconciling it. |
| Frontend dependency installation remains blocked. | Run syntax/type checks available in the environment, log the exact package-gateway failure, and do not claim browser validation passed. |

## Rollback Plan

Revert Plan 035 as one unit.

Rollback must restore:

- the current `NetworkGraph` community rendering branch;
- the run-wide Overview theme card;
- the Overview `TransitionsSankey` component;
- prior frontend tests and documentation.

Do not roll back Plans 033–034 period handling, user sampling, community API modes, or central-actor work. No analytical artifacts or database state require rollback because this plan is read-only and presentation-focused.

## Validation Log

| Date | Command | Result |
|---|---|---|
| 2026-08-01 | `python -m pytest -q tests/unit/test_overview_monthly_services.py` | Passed: 7 tests. |
| 2026-08-01 | `python -m pytest -q tests/unit/test_overview_monthly_services.py tests/unit/test_backend_api.py` | Partially blocked: the 7 monthly-service tests passed; 16 API tests could not create Parquet fixtures because neither `pyarrow` nor `fastparquet` is installed. |
| 2026-08-01 | `npm ci --ignore-scripts --no-audit --no-fund` | Blocked by package gateway: HTTP 404 for `yargs-parser@21.1.1`. Vitest, oxlint, Vite build, bundle, and Playwright commands could not run. |
| 2026-08-01 | Global TypeScript transpilation over `frontend/src` | Passed syntax transpilation for 138 source/test files. |
| 2026-08-01 | Focused `tsc --noEmit` for the three pure models | Passed. |
| 2026-08-01 | Focused `tsc --noEmit` for the new/changed chart components using temporary ambient dependency stubs | Passed. |
| 2026-08-01 | Compiled pure-model runtime assertions | Passed for deterministic community scaling, distinct-pair theme counts, connected continuity paths, retained counts, and month labels. |
| 2026-08-01 | `git diff --check` | Passed before patch generation. |
| 2026-08-01 | `git apply --check 035-overview-community-clarity-and-period-themes.patch` against a fresh extraction | Passed against the uploaded source-of-truth archive. |

## Progress Log

| Date | Update |
|---|---|
| 2026-08-01 | Plan created from the uploaded source-of-truth archive and the three approved Overview recommendations. |
| 2026-08-01 | Implemented the deterministic Community Landscape, preserving the existing user-level force graph and community drill-down without creating cross-community links. |
| 2026-08-01 | Implemented selected-month top-five theme summaries using distinct matched IF/WIF community pairs, exact labels, LDA keyword evidence, and incomplete-page refusal. |
| 2026-08-01 | Implemented the Community Continuity Timeline using canonical common-member counts for width, Jaccard for intensity, connected persistent paths, and a five-path Overview cap. |
| 2026-08-01 | Added focused model/component tests and updated the verification matrix and handoff documentation. Browser/unit/build execution remains blocked by the package gateway; responsive and visual checks remain explicitly open. |
