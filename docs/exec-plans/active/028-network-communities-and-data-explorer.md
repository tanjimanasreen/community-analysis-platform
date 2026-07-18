# Plan 028 — Network, Communities, and Data Explorer

Status: completed

Owner: agent

Last updated: 2026-07-18

## Goal

Functionalize the Community Network, Top Communities, and Data Explorer routes
using the bounded network, community, centrality, topic, theme, transition, and
artifact endpoints while preserving the existing three-panel and detail-rail UI
concepts.

## Dependencies

- Plans 026 and 027 are complete.
- Global selected run and metric are URL-backed.
- Shared loading/error/empty/unavailable states exist.

## Non-Goals

- No graph-database queries from the browser.
- No unbounded full-network downloads through the graph endpoint.
- No invented persistence, platform mix, message volume, linked-community
  similarity, or influence score.
- No mutation, starring, tagging, or saved searches unless those states remain
  clearly local and non-analytical; prefer removing them.

## Files Expected To Change

- `frontend/src/pages/CommunityNetwork.jsx`
- `frontend/src/pages/TopCommunities.jsx`
- `frontend/src/pages/DataExplorer.jsx`
- `frontend/src/components/charts/NetworkGraph.jsx`
- `frontend/src/components/NotableCommunitiesTable.jsx`
- `frontend/src/components/DataTable.jsx`
- `frontend/src/features/networks/` (new)
- `frontend/src/features/communities/` (new)
- `frontend/src/features/explorer/` (new)
- `frontend/src/utils/communityIds.ts` (new)
- `frontend/src/utils/pagination.ts` (new)
- relevant tests
- `docs/exec-plans/active/028-network-communities-and-data-explorer.md`

## Milestone 1 — Build the Network Feature Model

Tasks:

- [x] Define page state in URL parameters:
      - `metric=if|wif` (global);
      - `community=<community_id>`;
      - `minWeight=<number>`;
      - optional bounded `maxNodes` and `maxEdges` only if exposed in an
        advanced control.
- [x] Validate numeric parameters against backend constraints and project-safe
      UI limits. Never allow the client to request above server hard caps.
- [x] Create query hooks for full bounded graph, community list, selected
      community detail, and centrality page.
- [x] Include all filters in query keys.
- [x] Debounce `min_weight` changes or apply only after an explicit “Apply”
      action so sliders do not flood the API.
- [x] Use the server's `sampled` and available/returned counts exactly.

## Milestone 2 — Render the Real Interactive Graph

Tasks:

- [x] Transform `NetworkResponse.nodes` and `.edges` to the input expected by
      `react-force-graph-2d`.
- [x] Preserve string IDs without numeric coercion.
- [x] Compute returned-subgraph in-degree, out-degree, and total degree solely for
      visual sizing/tooltips. Label these as “within returned graph.”
- [x] Color by a deterministic hash of the first or selected community ID. Keep a
      stable neutral color for unassigned nodes.
- [x] Use edge width/opacity based on response `weight`; add a legend that states
      IF or WIF.
- [x] Add node hover tooltip with node ID, returned degree, and community IDs.
- [x] Node click should select a community unambiguously:
      - when one community ID exists, select it;
      - when several exist, show a small chooser;
      - when none exist, show node details without inventing a community.
- [x] Add functional controls: zoom to fit, reset selection, toggle labels, and
      adjust minimum weight.
- [x] Avoid fixed graph data and `Math.random`.
- [x] Lazy-load the graph library and show a skeleton while loading.
- [x] Test graph transformation as a pure function without canvas rendering.

## Milestone 3 — Replace Network KPI and Detail Rail Values

Tasks:

- [x] Replace fixed cards with supported values:
      - available nodes;
      - available edges;
      - returned nodes/edges;
      - selected metric;
      - number of communities from `/communities`.
- [x] Remove or relabel “Average Degree” unless calculated from the returned graph
      and explicitly named “Average degree in returned graph.”
- [x] Populate selected community detail from `CommunityDetail`:
      - community ID;
      - node count;
      - edge count;
      - total weight;
      - returned community subgraph counts and sampling state.
- [x] Enrich with theme/topic records only when community matching is reliable.
      Keep enrichment in separate labelled sections.
- [x] Remove unsupported platform mix, persistence score, total message share,
      top-linked communities, and fake trend values.
- [x] The close button must clear the `community` URL parameter.

## Milestone 4 — Implement Centrality and Community Tables

Tasks:

- [x] Inspect actual centrality artifact columns through the sample API fixture.
      Render dynamic columns only from an allowlisted schema documented in a
      frontend adapter.
- [x] Do not assume names that are not guaranteed by the generic `TablePage`.
- [x] Implement stable server pagination (`limit`, `offset`) and display total
      count.
- [x] Implement client-side sorting only for the currently loaded page, or request
      an additive backend sort feature after approval; label page-local sorting
      honestly.
- [x] Community rankings may sort by `total_weight`, `node_count`, or
      `edge_count`. Default to total weight for the selected metric.
- [x] Community-row selection should update the URL and graph/detail panel.
- [x] Ensure empty and out-of-range pages recover gracefully.

## Milestone 5 — Rebuild Top Communities Around Supported Metrics

Tasks:

- [x] Remove the hard-coded community array and fake selected ID.
- [x] Use `/communities` with real pagination.
- [x] Provide supported sort choices only.
- [x] Display metric-aware total weight, node count, and edge count.
- [x] Add optional theme and topic badges through separate queries for selected
      community, not by inventing fields on every row.
- [x] Replace star/favorite behavior with no control unless explicitly framed as
      local UI preference. Do not imply persisted backend state.
- [x] Make “View Network” navigate to `/network` with the selected community.
- [x] The details drawer must be populated from community detail and optional
      theme/topic responses.

## Milestone 6 — Turn Data Explorer into a Real Artifact Explorer

Keep the existing three-pane concept, but replace mock records.

Tasks:

- [x] Add tabs/data modes for:
      - communities;
      - centrality;
      - matched topics;
      - partial topics;
      - themes;
      - transitions;
      - artifacts.
- [x] Each mode must have its own query hook, pagination, empty state, and column
      adapter.
- [x] Search behavior:
      - for endpoints that support `community_id`, search exact community ID;
      - otherwise provide client-side filtering over the loaded page and label it
        “Filter this page”;
      - do not imply server-wide search when none exists.
- [x] Right-side details should show the raw normalized record in an accessible
      key/value view, plus related links when a community ID can be extracted.
- [x] Parse arrays/maps only through safe normalization utilities. Never use
      `eval` or `Function` on artifact values.
- [x] Artifact mode must show key, category, media type, schema version, stage,
      row count, byte size, and verification-related download action.
- [x] Intermediate artifacts must not be offered for download, matching backend
      restrictions.
- [x] Remove fake chats/messages, platform icons for unsupported records, local
      settings menus, and decorative actions with no behavior.

## Milestone 7 — Cross-Feature Community Identifier Rules

Tasks:

- [x] Document and implement normalization for IDs that may appear as strings or
      integers in API schemas.
- [x] Keep IF and WIF IDs distinct. Do not prefix them with fabricated `C-` IDs.
- [x] For matched topic/theme records, expose absolute/IF and weighted/WIF
      community IDs side by side.
- [x] When navigating from a matched record to the network, choose the community
      corresponding to the selected metric.
- [x] Add tests for numeric IDs, string IDs, missing IDs, and mismatched records.

## Tests

- [x] graph response transformer;
- [x] sampled graph labels and counts;
- [x] IF/WIF edge weight rendering metadata;
- [x] selecting/clearing a community through the URL;
- [x] community detail empty/unavailable cases;
- [x] centrality and community pagination;
- [x] Top Communities supported sorting;
- [x] Data Explorer mode switching and independent pagination;
- [x] no fake records on empty responses;
- [x] safe display of arrays, mappings, nulls, and strings;
- [x] artifact downloads use manifest key URLs.

## Acceptance Criteria

- [x] The Network page contains no hard-coded analytical number or selected
      community.
- [x] The graph is built only from `NetworkResponse` and indicates sampling.
- [x] Community detail and tables use supported API fields.
- [x] Top Communities and Data Explorer are functional, paginated, and honest
      about page-local filters.
- [x] IF/WIF selection is reflected in graph weights, community rankings, labels,
      and navigation.
- [x] Tests, typecheck, lint, and build pass.

## Risks

| Risk | Mitigation |
|---|---|
| Generic centrality records vary by artifact schema. | Inspect fixture columns and use an allowlisted adapter with a raw-record fallback. |
| Dense graph canvas becomes slow. | Respect bounded server limits, lazy-load, reduce labels, and use deterministic simple styling. |
| Community IDs differ between structural and semantic artifacts. | Centralize ID extraction and enrich only when match is unambiguous. |

## Rollback Plan

Revert this feature branch. The functional Overview remains intact. If one
advanced panel blocks completion, ship the real graph and structural community
features first, and render a documented unavailable state for that panel rather
than restoring mocks.

## Decision Log

| Date | Decision | Reason |
|---|---|---|
| 2026-07-18 | Keep network requests conservatively bounded at 400 nodes and 1,000 edges in the UI. | This stays below the backend hard caps, protects canvas performance, and avoids adding an advanced control that was not required for the current UI. |
| 2026-07-18 | Keep community and centrality sorting page-local. | The read-only API does not expose server-side sort parameters; the UI labels this scope rather than implying a global ranking. |
| 2026-07-18 | Allowlist the frozen centrality columns `month`, `absolute`, and `weighted`, with a raw-record fallback in the explorer. | Centrality is exposed through a generic table schema, so the adapter must not assume unsupported column names. |
| 2026-07-18 | Enrich community details with topic/theme records only after exact metric-aware ID matching. | IF and WIF identifiers must remain distinct and semantic records must not be attached ambiguously. |
| 2026-07-18 | Keep intermediate artifacts visible but non-downloadable. | This matches the backend download restrictions and avoids exposing internal pipeline files as public outputs. |
| 2026-07-18 | Make no backend route, schema, metric, or algorithm changes. | All Plan 028 functionality was achievable through the existing bounded read-only API. |

## Progress Log

| Date | Update |
|---|---|
| 2026-07-18 | Plan created. |
| 2026-07-18 | Confirmed `HARNESS.md` and root `ARCHITECTURE.md` are absent from the uploaded source zip, then reviewed the repository contracts, active dependency plans, API schemas/routers, and existing frontend implementation. |
| 2026-07-18 | Replaced the Community Network mock model with URL-backed `community` and `minWeight` state, bounded graph queries, deterministic graph transformation, real community detail, centrality pagination, and sampling metadata. |
| 2026-07-18 | Rebuilt Top Communities around paginated canonical community summaries, supported page-local sorting, exact semantic enrichment, and metric-aware Network navigation. |
| 2026-07-18 | Rebuilt Data Explorer with independent paginated modes for communities, centrality, matched topics, partial topics, themes, transitions, and artifacts; added safe normalized record details and manifest-key downloads. |
| 2026-07-18 | Added shared community-ID, pagination, graph, community, and explorer adapters plus unit and integration coverage. No fabricated `C-` IDs, mock records, or unsupported analytical values remain on the three routes. |
| 2026-07-18 | Validation: backend API tests 10 passed; frontend typecheck passed; 19 frontend test files / 43 tests passed; lint completed with 0 errors and 4 pre-existing unused-import warnings outside Plan 028 files; production build passed. Vite still reports the existing main-chunk size warning, while the graph library is now emitted as a separate lazy-loaded chunk. |
