# Plan 034 — Overview community structure and central actors

## Goal

Make the period-aware Overview network truthful and useful without changing any
analytical output. The Overview defaults to a complete community-summary map,
retains a deterministic user-level sample, supports month/metric-specific
community drill-down, and displays the existing monthly in-degree and out-degree
centrality leaders with their community assignments.

This plan does not change `shared_post`, `weighted_post`, graph thresholds,
Louvain, LDA, output categories, or the LDA-before-theme order. No pipeline rerun
is required.

## Source of truth

- `community-analysis-frontend-review-20260729-1747.zip`
- `dashboard-reproduction-739866ba-8f59-4784-a083-d64888b24ffd.tar.gz.part-000`
- Completed run `739866ba-8f59-4784-a083-d64888b24ffd`
- Manifest status `completed`, 93 canonical artifacts

## Inspection findings

1. Monthly `community_summary_absolute_*` and
   `community_summary_weighted_*` artifacts provide exact prominent-community
   membership, internal-edge, and total-weight summaries.
2. Monthly graph samples are deterministic strongest-edge artifacts bounded at
   pipeline publication time. In the supplied run their row counts equal the
   corresponding community-summary edge totals, so the published samples are
   complete for that run.
3. Canonical `communities_absolute_*` and `communities_weighted_*` artifacts are
   induced subgraphs of each Louvain community. They intentionally omit edges
   between communities. The current node-index artifacts contain node IDs but do
   not contain community assignments.
4. Therefore, this read-only patch can truthfully render every published
   community as a sized node, but it cannot construct inter-community edges.
   Those edges must not be inferred or fabricated. A future pipeline contract
   may add a cross-community aggregate artifact through a separately approved
   plan.
5. Monthly `user_centrality_*` artifacts already contain maximum and average
   in-degree/out-degree centrality values for both absolute (IF) and weighted
   (WIF) graph variants. The API can join each maximum actor to the exact
   period/metric prominent-community graph without recomputing NetworkX.
6. Derived edges run from original author/creator to spreader. Consequently,
   maximum in-degree identifies the broadest spreader/amplifier and maximum
   out-degree identifies the author reaching the broadest set of spreaders.

## Tasklist

### 1. Protect existing behavior

- [x] Read required architecture, product, data, database, metric, pipeline,
      theme, quality, test, and active-plan documentation in the prescribed order.
- [x] Verify artifact completeness and the absence of published cross-community
      edges in the supplied run.
- [x] Preserve the existing `view=users&sampling=strongest_edges` API default for
      backward compatibility.
- [x] Add focused service tests for period/metric routing and existing graph behavior.

### 2. Add explicit Overview graph modes

- [x] Extend the network read model with `view=communities|users`.
- [x] Add `sampling=community_balanced|strongest_edges` for user graphs.
- [x] Reject invalid filter combinations explicitly.
- [x] Add complete coverage metadata, including published users, edges,
      communities, and weight.
- [x] Mark whether cross-community edges are available.

### 3. Add the community structure map

- [x] Read only the exact period/metric community summary.
- [x] Return one node per published prominent community, sized by member count.
- [x] Include internal edge count and total IF/WIF weight.
- [x] Return no fabricated inter-community links.
- [x] Label node-limit truncation explicitly when a response limit is reached.

### 4. Add deterministic community-aware user sampling

- [x] Allocate a minimum quota per represented community where capacity permits.
- [x] Allocate remaining capacity using square-root community-size weighting.
- [x] Rank users deterministically by degree, incident weight, and stable ID.
- [x] Select strongest edges whose endpoints fit the chosen node set.
- [x] Retain deterministic strongest-edge sampling as an alternate mode.
- [x] Return community and IF/WIF weight coverage ratios.
- [x] Document that the canonical graph contains induced within-community edges,
      so a cross-community edge reserve is impossible with current artifacts.

### 5. Add centrality leaders

- [x] Add a period-aware `centrality-leaders` endpoint.
- [x] Read existing monthly centrality artifacts; do not call NetworkX.
- [x] Map `absolute` to IF and `weighted` to WIF.
- [x] Resolve leader membership using period + metric + user ID.
- [x] Return `null` and `unavailable` when no authoritative assignment exists.
- [x] Return masked display identifiers while retaining analytical IDs only for
      graph matching inside the typed API response.

### 6. Update the Overview UI

- [x] Default `networkView=communities` in URL-backed Overview state.
- [x] Add Community map/User sample controls and sampling selection.
- [x] Include view, strategy, period, metric, and drill-down community in query keys.
- [x] Prefetch adjacent periods and cancel stale requests through TanStack Query.
- [x] Render community nodes even when the response contains no links.
- [x] Display honest coverage and source-artifact limitations.
- [x] Support click-through from a community node to its bounded user subgraph.
- [x] Add selected-month spreader/influencer cards and all-month leader lists.
- [x] Show each leader's month- and metric-local community ID.
- [x] Distinguish “not in current preview” from “not in network”.

### 7. Tests and documentation

- [x] Add backend tests for community summaries, deterministic balanced sampling,
      strongest-edge fallback, leaders, membership lookup, and invalid filters.
- [x] Add frontend tests for URL defaults, graph modes, community map rendering,
      coverage wording, central actor assignments, and period interaction.
- [x] Update the API route fixture and query-name contract.
- [x] Update the verification matrix and handoff documentation.
- [ ] Run the complete Python suite in an environment with PyArrow and optional
      orchestration/tracking dependencies.
- [ ] Run frontend typecheck, lint, Vitest, build, bundle, and Playwright after a
      successful frozen npm install.

## Acceptance criteria

- Overview defaults to the community structure map.
- Every published community is displayed when within the configured response limit.
- The UI never calls a summary-only map a full inter-community network.
- User sampling is deterministic and its strategy and coverage are visible.
- Month, metric, view, sampling, and community drill-down state are URL-backed.
- IF and WIF remain separate.
- The top spreader and influencer are read from existing monthly artifacts for
  every available month.
- Leader community IDs are resolved from the exact month/metric graph and are
  labelled local to that partition.
- Missing assignments remain unavailable rather than becoming zero or inferred.
- No analytical metric/default/artifact changes and no provider calls occur.

## Validation log

| Date | Command/check | Result |
|---|---|---|
| 2026-07-29 | Source/reproduction SHA-256 and archive integrity checks | Passed. |
| 2026-07-29 | Required documentation review | Passed in required order. |
| 2026-07-29 | Reproduction manifest/artifact inspection | Confirmed 93 artifacts, four monthly snapshots, complete published graph samples for this run, and no cross-community edge artifact. |
| 2026-07-29 | `python -m pytest -q tests/unit/test_overview_monthly_services.py` | Passed: 7 focused service tests. |
| 2026-07-29 | Focused API-period, monthly-service, graph-publication, and graph-guard suite | Passed: 18 tests. |
| 2026-07-29 | Python compilation and `git diff --check` | Passed. |
| 2026-07-29 | Frontend syntax transpilation | Passed: 130 source files, zero syntax diagnostics. |
| 2026-07-29 | Checked-in OpenAPI route fixture comparison | Passed: 21 documented GET routes. |
| 2026-07-29 | JSON/YAML parsing | Passed: 8 JSON and 15 YAML files. |
| 2026-07-29 | Parquet-backed backend API tests | Blocked locally: neither PyArrow nor FastParquet is installed. |
| 2026-07-29 | `npm ci --ignore-scripts --no-audit --no-fund` | Blocked: internal package gateway returned 404 for `yargs-parser@21.1.1`. |

## Progress log

| Date | Update |
|---|---|
| 2026-07-29 | Added explicit network view/sampling schemas, coverage metadata, deterministic community-aware sampling, and a truthful community-summary map. |
| 2026-07-29 | Added the centrality-leaders read model and exact period/metric community membership lookup without NetworkX recomputation. |
| 2026-07-29 | Added Overview view controls, community drill-down, coverage descriptions, and central-actor cards/timelines. |
| 2026-07-29 | Documented that current canonical outputs do not contain cross-community edges, so this patch does not invent them. |

## Deferred work

- Publishing cross-community aggregate edges requires a new additive pipeline
  artifact and separate approval.
- Top-five rankings require a new canonical ranking artifact; current output
  preserves only maxima, minima, and averages.
- Persistent cross-month community colors require transition-identity mapping and
  belong in the Evolution workflow.
- Full user search and arbitrary ego expansion remain Network-page work.

## Rollback

Revert this patch as one unit. Run artifacts are read-only and require no
rollback. Retain the period-aware Overview work from Plan 033. Do not restore
cross-month graph merging or describe a strongest-edge sample as a complete
network.
