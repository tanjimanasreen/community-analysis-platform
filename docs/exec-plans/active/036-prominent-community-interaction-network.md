# Plan 036 — Prominent Community Interaction Network and Expandable Community Inspector

Status: implemented; browser/full-Parquet validation environment-blocked

Last updated: 2026-08-02

Source of truth: `community-analysis-latest-20260802-1809.zip`

## Goal

Replace the Overview's separate Community Landscape and User Sample presentation with one honest, high-level network of **prominent communities** for the selected month and metric.

Each node represents one prominent community. Its area is determined by member count. A connection exists only when at least one original user-to-user interaction crosses the two community memberships. Selecting a community opens an expandable inspector containing every detail that the published run artifacts and current API can support, including the bounded member graph, topics, and themes when available.

## Decisions for review

1. **Displayed cohort**
   - Include all and only prominent communities published for the selected month and IF/WIF partition.
   - Do not limit the graph to matched/LDA/theme communities.
   - Do not display ordinary user nodes until a community is selected.

2. **Community edge semantics**
   - Community membership is metric-local and month-local.
   - For each directed user-user interaction in the complete filtered monthly graph, map the source and target users to their selected metric's community IDs.
   - Publish a cross-community edge only when:
     - both users belong to prominent communities;
     - the two community IDs differ; and
     - at least one interaction exists.
   - Preserve the direction of the original creator-to-spreader interaction.
   - Aggregate, without redefining, the selected thesis metric:
     - IF edge weight = sum of existing `shared_post` values;
     - WIF edge weight = sum of existing `weighted_post` values.
   - Also publish the number of distinct underlying user-user pairs contributing to the aggregate edge.

3. **Visual edge treatment**
   - Render one visual connection for each unordered community pair to reduce duplicate clutter.
   - Show one or two arrowheads to represent the observed direction(s).
   - Width encodes total bidirectional selected-metric weight using a logarithmic display scale.
   - Opacity encodes the number of contributing user-user pairs.
   - Tooltip exposes the directional breakdown, pair count, and selected metric weight.

4. **Selection and expansion**
   - A click selects, enlarges, and pins the community node.
   - Open a side inspector on desktop and a bottom sheet/stacked panel on mobile.
   - The inspector contains three tabs:
     1. Summary;
     2. Member network;
     3. Topics and themes.
   - The member network is loaded lazily using the existing bounded community-detail graph endpoint.
   - A dedicated `Open full community network` action navigates to the Network route with run, month, metric, and community ID preserved.

## Current-source limitation

The current canonical community graph artifacts are induced within-community subgraphs and therefore cannot reveal whether users in different communities interacted. The uploaded reproduction bundle also omits the large raw monthly network artifacts. Cross-community links must not be inferred from the current summaries or fabricated in the frontend.

Implementation therefore requires an additive pipeline artifact generated from the complete filtered user-user graph before induced prominent-community graph export. Existing runs lacking the artifact must render a clear nodes-only compatibility state.

## Non-negotiable constraints

- Do not change `shared_post` or `weighted_post` behavior.
- Do not change graph thresholds, Louvain defaults, community IDs, or prominent-community filtering.
- Do not alter LDA, theme generation, transition, or similarity outputs.
- Do not synthesize cross-community links from themes, member overlap, layout proximity, or summary counts.
- Do not call OpenAI, TEI, Memgraph, or external services in automated tests.
- Keep Telegram and Twitter/reply/retweet-quote workflows supported.
- Keep all new artifacts additive and backward-compatible.

## Proposed additive artifact contract

Create one metric-specific artifact per month:

```text
data/communities/interactions/absolute/<content_type>/<month>.parquet
data/communities/interactions/weighted/<content_type>/<month>.parquet
```

Manifest keys:

```text
community_interactions_absolute_<month>
community_interactions_weighted_<month>
```

Required columns:

| Column | Meaning |
|---|---|
| `source_community_id` | Metric-local prominent community containing the original source user |
| `target_community_id` | Metric-local prominent community containing the interacting target user |
| `user_pair_count` | Number of distinct directed source-target user pairs contributing to this aggregate |
| `interaction_count` | Sum of existing `shared_post` values for provenance, available in both artifacts |
| `total_weight` | Selected metric aggregate: IF=`shared_post`, WIF=`weighted_post` |
| `source_user_count` | Distinct source users contributing to this direction |
| `target_user_count` | Distinct target users contributing to this direction |

Rules:

- Exclude same-community rows from this cross-community artifact.
- Exclude any endpoint not assigned to a prominent community.
- Keep directed rows; do not merge directions in the artifact.
- Sort deterministically by source community ID and target community ID.
- Empty months produce a valid empty artifact with the same schema.

## Milestone 1 — Protect current behavior and freeze fixtures

Tasks:

- [x] Copy this plan into `docs/exec-plans/active/` after approval.
- [ ] Record current Overview screenshots and API responses for:
  - community view with 200+ prominent communities;
  - a single-community user drill-down;
  - a legacy run with no cross-community artifact.
- [x] Add fixtures covering:
  - two prominent communities with one directed cross-community interaction;
  - bidirectional interactions between the same pair;
  - non-prominent endpoints;
  - same-community interactions;
  - isolated prominent communities;
  - IF and WIF aggregation differences;
  - an empty cross-community artifact.
- [ ] Confirm existing community summaries and user graph outputs are unchanged byte-for-byte or dataframe-equivalent.

## Milestone 2 — Publish cross-community interaction artifacts

Tasks:

- [x] Locate the monthly full user-user dataframe after existing filters and before prominent induced-subgraph export.
- [x] Build a deterministic user-to-community membership map separately for IF and WIF.
- [x] Aggregate directed cross-community interactions according to the contract above.
- [x] Write the additive Parquet artifacts and register them in the run manifest.
- [x] Add output-contract documentation and artifact validation.
- [x] Ensure no additional full raw graph copy is persisted.
- [x] Keep memory bounded by grouping required columns only.

Required tests:

- exact IF aggregation;
- exact WIF aggregation;
- directed A→B and B→A preservation;
- exclusion of same-community and non-prominent endpoints;
- stable sort/order;
- empty schema;
- original analytical outputs unchanged.

## Milestone 3 — Extend the read-only API

Preferred approach: retain `view=communities` and enhance it additively.

Tasks:

- [x] Read community nodes from existing community summaries.
- [x] Read cross-community directed edges from the new artifact when available.
- [x] Populate node fields:
  - member count;
  - internal edge count;
  - internal selected-metric weight;
  - inbound cross-community weight;
  - outbound cross-community weight;
  - cross-community neighbor count.
- [x] Add edge metadata without changing existing meanings:
  - selected metric weight;
  - distinct contributing user-pair count;
  - directional source and target.
- [x] Set `coverage.cross_community_edges_available=true` only when the canonical artifact exists.
- [x] Keep all prominent community nodes even when they are isolated.
- [x] Bound edge responses deterministically only when necessary, sorted by total weight and stable community IDs; disclose exact edge/weight coverage.
- [x] For legacy runs, return all community nodes, no edges, and an explicit compatibility reason.
- [x] Preserve current community detail and user graph endpoints.

Schema changes should be additive. Prefer optional fields such as:

```text
NetworkNode.cross_community_neighbor_count
NetworkEdge.user_pair_count
```

## Milestone 4 — Replace Community Landscape/User Sample with Prominent Community Network

Tasks:

- [x] Rename the Overview panel to **Prominent Community Network**.
- [x] Remove the User Sample toggle from Overview.
- [x] Render only `node_type=community` nodes in the initial graph.
- [x] Use the existing lazy force-graph bundle for the high-level network.
- [x] Node visual encoding:
  - area = square-root-scaled member count;
  - label = `C<community_id>` for selected, hovered, searched, and largest communities;
  - fill = selected metric identity/neutral community palette;
  - ring intensity = internal selected-metric weight;
  - selection = enlarged node plus high-contrast outline.
- [x] Edge visual encoding:
  - width = logarithmic total bidirectional selected-metric weight;
  - opacity = contributing user-pair count;
  - arrowheads = observed direction(s);
  - tooltip = directional IF/WIF totals and user-pair counts.
- [x] Keep isolated prominent communities visible in a peripheral orbit or separated `No cross-community links` band so they do not obscure the connected core.
- [x] Add search by community ID.
- [x] Add presentation-only controls:
  - minimum cross-community weight;
  - connected/isolated visibility;
  - labels on/off;
  - zoom, fit, reset, fullscreen.
- [x] Clearly state that filters affect presentation only and do not change community detection.
- [x] Display coverage:
  - prominent communities shown / available;
  - cross-community links shown / available;
  - selected-metric weight coverage.

## Milestone 5 — Expandable community inspector

Tasks:

- [x] On node click, set the selected community in URL state.
- [x] Highlight the selected node and first-degree neighboring community links.
- [x] Lazy-load the existing community detail endpoint.
- [x] Lazy-load selected-month topics and themes for the selected community.
- [x] Render `Unavailable for this community/run` when optional topic/theme artifacts do not contain the selected community.

### Summary tab

Show only supported values:

- community ID;
- month and metric;
- member count;
- internal edge count;
- internal selected-metric weight;
- inbound/outbound cross-community weight;
- connected prominent-community count;
- top neighboring communities by aggregate cross-community weight;
- whether matched topics/themes are available.

### Member network tab

- Reuse the existing bounded user-level community graph.
- Show users and within-community directed edges only.
- Display returned/available nodes and edges.
- Preserve masked identifiers and existing graph encodings.
- Provide a link to the dedicated Network route for larger exploration.

### Topics and themes tab

- Show matched or partial topic output only when the existing APIs support an unambiguous selected metric/community mapping.
- Show LDA unigram/bigram keywords before provider-generated theme labels.
- Preserve provider metadata and downstream-of-LDA language.
- Never generate a new theme from the inspector.

## Milestone 6 — Responsive and accessible behavior

Tasks:

- [x] Desktop: graph plus right inspector.
- [ ] Tablet/mobile: graph followed by collapsible inspector; no page-level horizontal overflow.
- [x] Keyboard-accessible community selection and graph controls.
- [ ] Non-hover details for selected node and selected edge.
- [x] Screen-reader summary listing selected community, size, neighbors, and available detail tabs.
- [x] Reduced-motion mode disables animated reheating and uses deterministic positioning where practical.
- [ ] Labels remain readable at 200% zoom and 320 CSS pixels.

## Milestone 7 — Validation and documentation

Backend/pipeline:

```bash
make format
make lint
python -m pytest -q \
  tests/unit/test_network_dashboard_sample.py \
  tests/unit/test_overview_monthly_services.py \
  tests/unit/test_backend_api.py \
  tests/unit/test_output_artifact_contract.py
```

Frontend:

```bash
cd frontend
npm ci
npm run test -- --run \
  src/components/charts/__tests__/NetworkGraph.test.jsx \
  src/pages/__tests__/Overview.test.jsx \
  src/features/overview/__tests__/useOverviewData.test.tsx
npm run typecheck
npm run lint
npm run build
npm run test:e2e -- overview
```

Project-level:

```bash
make test
make build-report
```

Documentation:

- [x] Update `docs/design-docs/output-artifact-contract.md`.
- [x] Update `docs/design-docs/pipeline-contract.md`.
- [x] Update `docs/verification/test-matrix.md`.
- [x] Update `docs/HANDOFF.md`.
- [x] Update this plan's progress and validation logs.

## Acceptance criteria

1. The Overview initial graph contains every published prominent community for the selected month/metric and no ordinary user nodes.
2. Node area monotonically reflects community member count.
3. A community connection appears only when the new canonical artifact contains at least one cross-community user interaction.
4. IF and WIF edges use the existing metric values without redefinition.
5. Isolated prominent communities remain discoverable without dominating the connected core.
6. Clicking a community opens supported summary details, its bounded member graph, and available topics/themes.
7. Optional semantic data is never fabricated and missing data is explicitly identified.
8. Legacy runs without the additive artifact remain usable through an honest nodes-only state.
9. Existing thesis outputs, defaults, and dedicated routes remain unchanged.
10. All available validation passes; environment-blocked checks are logged exactly.

## Implementation progress log

- 2026-08-02: Verified the source archive checksum and initialized a clean patch baseline from `community-analysis-latest-20260802-1809.zip`.
- 2026-08-02: Added metric-local, directed prominent-community interaction aggregation and additive IF/WIF Parquet artifacts without modifying existing graph, Louvain, or metric behavior.
- 2026-08-02: Extended manifest routing, output contracts, API schemas, network/community services, and selected-period topic reads. Legacy runs retain an explicit nodes-only response.
- 2026-08-02: Replaced the Overview Community Landscape/User Sample switch with the Prominent Community Network and a lazy Summary/Members/Topics & themes inspector. Dedicated Network-route sampling remains unchanged.
- 2026-08-02: Added unit/component coverage, responsive styles, reduced-motion handling, and documentation updates. Browser rendering and full Parquet-backed suites remain environment-blocked as recorded below.

## Decision log

| Decision | Outcome |
|---|---|
| Initial Overview cohort | All published prominent communities for the selected month and metric; no ordinary user nodes. |
| Cross-community relationship source | Only the new canonical monthly interaction artifact generated from the filtered user-user graph. No frontend inference. |
| Reciprocal directions | Kept as separate directed rows in the artifact/API and merged only for visual presentation, with directional weights and pair counts preserved. |
| Community expansion | Master-detail inspector with lazy bounded member graph and existing published semantic outputs. |
| Existing runs | All prominent nodes remain usable in a clearly labeled nodes-only compatibility state. |

## Validation log

| Command/check | Result |
|---|---|
| Source archive SHA-256 | Passed: `65fbfef317685da426aab4833179d1e8a9223b36ac03b3cef836bac72c97822a`. |
| Focused backend tests: `test_community_interactions`, `test_topic_service_period`, `test_overview_monthly_services`, `test_artifact_key_routing`, `test_network_dashboard_sample` | Passed: 22 tests. |
| `python -m compileall -q src tests` | Passed. |
| TypeScript `transpileModule` syntax check for 14 changed frontend files | Passed. |
| Runtime assertions for reciprocal link aggregation, directional totals, member-count node scaling, and isolate positioning | Passed. |
| `git diff --check` | Passed. |
| Fresh-source `git apply --check` plus focused backend/compile/frontend-syntax checks after applying the patch | Passed against a new extraction of the source-of-truth archive. |
| `tests/unit/test_backend_api.py` and `tests/unit/test_output_artifact_contract.py` | Blocked: the environment has neither `pyarrow` nor `fastparquet`, so fixture Parquet files cannot be created. |
| `npm ci --ignore-scripts` | Blocked: internal npm gateway returned HTTP 404 for `yargs-parser@21.1.1`; Vitest, full typecheck, lint, Vite build, and Playwright could not run. |
| `make format` | Blocked: `.venv/bin/python` was unavailable; global Python has no Black installation. |
| `make lint` | Blocked: dependency resolution could not find `mlflow-skinny==3.14.0` in the available package registry. |
| `make test` | Blocked: package resolution/build could not obtain `setuptools>=61.0` from the available registry. |
| `make build-report` | Blocked: the incomplete environment lacks `pydantic`. |

Open validation items are the baseline screenshots/API captures, byte/dataframe equivalence through a full pipeline run, mobile collapse behavior, non-hover edge detail, and browser checks at 200% zoom/320 CSS pixels. These are not claimed as passed.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Existing artifacts cannot produce cross-community links | Add canonical pipeline artifact; explicit legacy fallback |
| 200+ nodes and many links form a hairball | Aggregate reciprocal directions, logarithmic widths, isolate placement, labels on demand, weight filter |
| Large pipeline memory cost | Select required columns, map IDs once, group incrementally, benchmark |
| Community IDs differ between IF and WIF | Build and publish one metric-local network at a time |
| Click inspector over-fetches data | Lazy queries keyed by run, month, metric, community ID |
| “All details” implies unavailable metrics | Render only published/API-supported values and mark unavailable sections |
| User graph is larger than API limits | Show exact coverage and link to dedicated Network route |

## Rollback

- The new artifacts and optional API fields are additive.
- The current nodes-only community response remains the compatibility fallback.
- The previous Community Landscape component can remain temporarily behind a feature flag until the new artifact is available in a verified sample run.
