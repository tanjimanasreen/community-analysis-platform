# Plan 038 — Aggregate Matched-Community Thematic Analysis

Status: implemented — validation constrained by review-package dependencies

Owner: agent

Last updated: 2026-08-06

## Goal

Refocus the **Thematic Analysis** route on RQ2 only: the themes generated for **all matched IF/WIF communities** over the selected timeline.

The page will:

1. show the top five themes and prominent LDA keywords for every month in the selected timeline;
2. summarize the most prevalent theme across the complete timeline;
3. visualize aggregate month-to-month theme progression across all matched communities;
4. preserve matched-community LDA and provider-label evidence for auditability.

The page will not use persisted-community paths, Community Continuity Timeline links, Jaccard transition scores, retained-member counts, member mobility, or persisted-path thematic similarity. Those belong to **Community Evolution**.

## Thesis alignment

This plan mirrors the Twitter community-theme result structure in Section 4.3.3 and Tables 4.27–4.29:

- month;
- top discussed themes;
- prominent LDA keywords;
- number of communities aligned with each theme;
- separate runs/content types for Retweet–Quote, Reply, and Combined networks.

The longitudinal visualization is an aggregate view of monthly matched-community theme prevalence. It is not a community-persistence visualization and does not answer RQ3/RQ4.

## Scope boundary

### In scope — Thematic Analysis / RQ2

- all matched IF/WIF community pairs in each month;
- top five saved general theme labels per month;
- prominent LDA keywords for each theme;
- matched-community count and percentage per theme;
- aggregate rank/prevalence changes across months;
- most prevalent theme across the selected timeline;
- matched LDA evidence and downstream provider-theme evidence;
- provider/model provenance.

### Out of scope — Community Evolution / RQ3 and RQ4

- persisted community paths;
- transition graph/path ranking;
- Community Continuity Timeline;
- Jaccard values between consecutive-month communities;
- retained, joined, exited, or reappearing members;
- thematic-similarity matrices or heatmaps for persisted paths;
- path-specific theme stability classifications.

No transition or theme-similarity artifact is to be read by the Thematic Analysis route.

## Non-negotiable preservation rules

- Do not change `shared_post` or `weighted_post` behavior.
- Do not change graph thresholds, Louvain defaults, LDA defaults, provider behavior, prompts, or generated artifacts.
- Do not call LDA, GPT, embeddings, HDBSCAN, or external providers in the browser.
- Do not generate new community matches or infer structural continuity.
- Do not remove transition, membership, or similarity functionality from the project; only remove it from this page.
- Keep Telegram and all Twitter content types configurable through the selected run.
- Do not introduce paid dependencies or mandatory provider calls.

## Analytical definitions

### Matched community pair

```text
normalized absolute_community + normalized weighted_community
```

Rows lacking both identifiers are excluded and reported in response metadata.

### Theme source and identity

Use the saved final general theme fields from the matched-theme artifact:

1. `general_theme_names` when present;
2. keys from `general_theme_gpt` when the names field is absent;
3. IF/WIF labels only as the existing fallback when no general label exists.

Theme identity is the saved label string. The dashboard will not merge synonyms, punctuation variants, or semantically similar labels. Adding thesis-style semantic standardization requires a separately approved upstream artifact; it must not be introduced silently in the frontend.

### Monthly theme prevalence

For one month and one saved theme label:

```text
community_count = distinct matched pairs carrying the theme
percentage = community_count / total themed matched pairs in that month
```

A pair carrying multiple themes contributes once to every applicable theme. Percentages therefore need not sum to 100%.

### Monthly ranking

Sort themes by:

1. `community_count` descending;
2. percentage descending;
3. saved theme label ascending for deterministic ties.

Display the first five themes.

### Prominent LDA keywords

Use only keyword evidence from matched-pair rows carrying that saved theme label. Preserve the existing deterministic keyword ordering:

1. distinct pair coverage;
2. first saved source order;
3. lexical order as the final tie-break.

Display up to five keywords in the monthly summary and retain full evidence in the lower evidence browser.

### Timeline leader

The most prevalent theme across the selected range ranks by:

1. total matched community-pair/month count;
2. number of months present;
3. highest single-month pair count;
4. saved label ascending.

Use **community-month coverage**, not message volume.

### Aggregate theme progression

Build progression only from the monthly top-five summaries returned by the theme timeline endpoint.

For every saved theme label in the union of monthly top-five themes, derive:

- month;
- rank, 1–5;
- matched-pair count;
- percentage;
- prominent keywords;
- status: `new`, `continued`, `exited`, or `re-entered`.

Connect a theme only when the identical saved label appears in **adjacent months**. Do not bridge over missing months and do not connect semantically similar but differently named themes. A later reappearance begins a new segment and is marked `re-entered`.

## Proposed page information architecture

### 1. Header and scope statement

Title: **Thematic Analysis**

Description:

> Explore the themes generated for all matched IF/WIF communities across the selected timeline. Monthly rankings use distinct matched-community coverage and preserve LDA keywords as upstream evidence.

Scope badge: **All matched IF/WIF communities**

Add a short boundary note:

> Persisted-community thematic similarity is available under Community Evolution.

### 2. Primary timeline filters

Keep only controls that affect the aggregate thematic analysis:

- Timeline start
- Timeline end

Defaults:

- first available theme month;
- last available theme month.

Rules:

- invalid ranges are clamped as today;
- changing the range clears selected theme evidence when the selected month leaves the range;
- the selected run continues to determine platform and content type.

### 3. Timeline summary cards

Replace selected-month and persistence metrics with:

1. **Months analyzed** — number of months in the selected range;
2. **Themed community-months** — sum of monthly themed matched-pair denominators;
3. **Distinct saved themes** — union of saved labels across the selected range;
4. **Most prevalent theme** — timeline leader and total community-month count.

Do not show Persistent Paths.

### 4. Monthly Top Five Theme Matrix

Create a timeline-wide section that displays every selected month.

For each month, show exactly up to five ranked themes with:

- rank;
- saved theme label;
- matched-community count;
- percentage of themed matched pairs;
- up to five prominent LDA keywords;
- rank movement from the immediately previous month when the identical label was present.

Recommended layout:

- four month columns for a four-month run;
- responsive two-column/one-column wrapping on smaller screens;
- horizontal scrolling with sticky month headers only for long timelines where wrapping would make comparison difficult.

Clicking a theme sets the evidence month and exact theme filter without changing the aggregate summary.

### 5. Aggregate Theme Progression

Replace **Theme Progression Across Persistent Communities** with an aggregate rank-flow/bump chart.

Encoding:

- x-axis: months;
- y-axis: rank 1–5;
- point label: theme name;
- point annotation/tooltip: matched-pair count, percentage, keywords;
- stable label-derived color per theme;
- solid line only between identical labels in adjacent months;
- no line across absent months;
- entrance/exit/re-entry markers.

The visualization must not display:

- community IDs;
- path IDs;
- Jaccard;
- retained members;
- transition widths;
- continuity arrows between communities.

Provide an accessible companion table beneath the chart:

| Theme | Month | Rank | Matched communities | Percentage | Status | Keywords |

Clicking a point or row filters the evidence section to that month and exact label.

### 6. Evidence Explorer — matched records only

Keep evidence on the page, but visually separate it from aggregate controls.

Evidence controls:

- Evidence month;
- Token representation: unigram, bigram, combined;
- Metric evidence view: general labels, IF/WIF side by side, IF only, WIF only;
- Exact community ID.

Changes:

- force topic record type to `matched` on this route;
- remove the Partially Matched option from this page;
- preserve partial-topic inspection on the Topic Modeling page;
- keep independent topic/theme pagination;
- clicking a monthly theme sets `themeMonth` and `exactTheme` for evidence;
- community filter affects evidence only, never aggregate rankings.

### 7. Provider provenance

Keep Provider Metadata because it documents how the human-readable theme labels were generated downstream from LDA.

### 8. Remove Community Evolution content from this page

Remove from the Thematic Analysis render/query path:

- Persistent Paths metric card;
- `ThemeProgressionTimeline`;
- `ThemeProgressionDetails`;
- link to Community Transitions inside thematic progression;
- saved theme-similarity panel;
- transition query;
- similarity query;
- path auto-selection and `themePath` behavior on this route.

The existing transition/similarity APIs, artifacts, models, and Community Transitions page remain intact.

## Implementation strategy

### Milestone 1 — Protect the corrected scope with tests

Before editing the page, update/add tests asserting:

- the page requests theme timeline and matched evidence only;
- no transition request is made;
- no theme-similarity request is made;
- no Persistent Paths, Jaccard, retained-member, or persisted-community headings appear;
- every month in a four-month fixture renders up to five themes and keywords;
- aggregate progression uses monthly summaries only;
- only identical labels in adjacent months are connected;
- missing-month gaps are not bridged;
- re-entry is marked without implying continuity;
- partial topic records are not selectable on this route;
- evidence filters do not change aggregate rankings.

### Milestone 2 — Add pure aggregate trend models

Extend `frontend/src/features/themes/themeTrendModel.ts` with pure functions:

- `timelineSummaryMetrics(response)`;
- `monthlyTopFive(response, limit = 5)`;
- `buildAggregateThemeProgression(response, limit = 5)`;
- `themeStatusForMonth(...)`;
- `progressionRows(...)`.

The functions must be deterministic, side-effect free, and must not use transition data.

Suggested types:

```ts
interface MonthlyTopThemePoint {
  period: string;
  name: string;
  rank: number;
  communityCount: number;
  percentage: number;
  keywords: string[];
  status: 'new' | 'continued' | 'exited' | 're-entered';
}

interface AggregateThemeSeries {
  name: string;
  points: MonthlyTopThemePoint[];
  segments: MonthlyTopThemePoint[][];
}
```

### Milestone 3 — Build timeline-wide components

Add:

- `MonthlyThemeMatrix.tsx`;
- `AggregateThemeProgression.tsx`;
- `AggregateThemeProgressionTable.tsx` or an accessible table embedded in the progression component.

Reuse:

- `stableThemeColor`;
- `periodLabel`;
- `KeywordList`;
- existing loading/error/unavailable components.

Refactor `MonthlyTopThemes.tsx` only if useful as a reusable single-month child. Avoid duplicating ranking logic inside UI components.

### Milestone 4 — Surgically refactor ThematicAnalysis.jsx

Modify `frontend/src/pages/ThematicAnalysis.jsx`:

- remove transition/similarity imports and query use;
- remove persistent-path model and effects;
- use `timelineQuery.data.monthly_summaries` as the source for all monthly summaries;
- remove the separate selected-month trend query from the main summary path;
- render the timeline summary cards;
- render the monthly theme matrix;
- render aggregate theme progression;
- move selected month to Evidence Explorer and rename it **Evidence month**;
- force matched topic evidence;
- preserve exact-theme click filtering, evidence pagination, provider metadata, and network deep links;
- remove saved theme similarity from the page.

### Milestone 5 — Simplify the data hook without changing APIs

Modify `frontend/src/features/topics/useThematicAnalysisData.ts`:

- remove `getTransitions` and `getThemeSimilarity` imports;
- remove `transitionsQuery` and `similarityQuery`;
- remove the redundant `monthlyTrendQuery` if all monthly summaries are consumed from `timelineQuery`;
- force `getTopics(... type: 'matched')` on this route;
- keep `themesQuery` month/exact-label/community pagination for evidence;
- keep `overviewQuery` only for periods/model metadata if still required.

No backend endpoint or artifact schema change is expected. `ThemeTrendService.timeline` already provides complete monthly summaries and the timeline leader.

### Milestone 6 — URL-state behavior

Keep:

- `themeStart`;
- `themeEnd`;
- `themeMonth` as Evidence month;
- `exactTheme`;
- `semanticMetric`;
- `token`;
- `semanticCommunity`.

On this route:

- canonicalize `topicType` to `matched`;
- ignore/deprecate `themePath` and remove it when the page rewrites canonical search parameters;
- clicking a monthly theme writes both `themeMonth` and `exactTheme`;
- changing the timeline does not alter evidence month unless it falls outside the range.

Avoid a broad shared-search-state rewrite if a route-local normalization is sufficient.

### Milestone 7 — Documentation correction

Update:

- `docs/design-docs/theme-intelligence-contract.md`;
- `docs/verification/test-matrix.md`;
- `docs/HANDOFF.md`;
- relevant frontend README/methodology copy;
- Plan 037 with a note that its persisted-path page scope was superseded by Plan 038.

Document the strict separation:

```text
Thematic Analysis = all matched communities / aggregate theme trends / RQ2
Community Evolution = persisted community paths / thematic similarity / RQ3
```

Do not delete the underlying transition or theme-similarity contracts.

## Expected files to change

### Frontend

- `frontend/src/pages/ThematicAnalysis.jsx`
- `frontend/src/features/topics/useThematicAnalysisData.ts`
- `frontend/src/features/topics/semanticSearchParams.ts` — route-local canonicalization only if needed
- `frontend/src/features/themes/themeTrendModel.ts`
- `frontend/src/features/themes/MonthlyTopThemes.tsx` — optional refactor
- `frontend/src/features/themes/DominantThemeTimeline.tsx` — wording/placement update
- `frontend/src/features/themes/MonthlyThemeMatrix.tsx` — new
- `frontend/src/features/themes/AggregateThemeProgression.tsx` — new
- `frontend/src/pages/__tests__/ThematicAnalysis.test.jsx`
- `frontend/src/features/themes/__tests__/themeTrendModel.test.ts`
- `frontend/tests/e2e/network-thematic.spec.ts`
- visual-regression baseline only after intentional review

### Documentation

- `docs/exec-plans/active/038-thematic-analysis-aggregate-matched-theme-progression.md`
- `docs/exec-plans/active/037-thematic-analysis-matched-theme-trends.md`
- `docs/design-docs/theme-intelligence-contract.md`
- `docs/verification/test-matrix.md`
- `docs/HANDOFF.md`

### Expected not to change

- network metric code;
- Louvain/LDA/provider pipeline code;
- transition generation;
- theme-similarity computation;
- transition/evolution API routes;
- Community Transitions page, except a separate later plan if its thematic-evolution presentation is expanded.

## Test plan

### Pure model tests

- top-five selection for every month;
- deterministic tie order;
- multi-label pair counting;
- denominator and percentage behavior;
- stable keyword order;
- timeline summary metrics;
- same-label consecutive connection;
- absent-month gap;
- re-entry segmentation;
- no synonym/case/punctuation merging;
- year-boundary month ordering;
- empty and incomplete responses.

### Page tests

- renders all four monthly columns/cards;
- shows five or fewer themes per month;
- renders prominent keywords;
- timeline filters update all monthly summaries and progression;
- clicking a theme updates Evidence month and exact label;
- Evidence community filter does not change aggregate sections;
- matched-only evidence;
- no persistent paths/Jaccard/retention/similarity UI;
- no transition/similarity query state required;
- provider metadata and network deep links remain;
- loading, empty, error, and artifact-unavailable states.

### API/backend regression tests

Retain `tests/unit/test_theme_trend_service.py` unchanged unless a real service defect is discovered. Re-run it to ensure monthly/timeline aggregation behavior remains stable.

### End-to-end tests

For the four-month Retweet–Quote fixture:

- January–April are all visible;
- top-five themes and keywords render per month;
- progression chart and accessible table agree;
- no persisted-community visual appears;
- clicking April's top theme filters April evidence;
- browser console is clean;
- keyboard navigation and accessible names pass.

## Validation commands

Run from the complete repository:

```bash
make format
make lint
make test
make frontend-check

python -m pytest -q \
  tests/unit/test_theme_trend_service.py \
  tests/unit/test_backend_api.py \
  tests/unit/test_dashboard_fixture.py

cd frontend
npm run test -- --run \
  src/features/themes/__tests__/themeTrendModel.test.ts \
  src/pages/__tests__/ThematicAnalysis.test.jsx
npm run typecheck
npm run lint
npm run build
npm run test:e2e -- network-thematic.spec.ts
cd ..

git diff --check
```

If the environment is missing dependencies, record the exact blocked command. Do not weaken tests or claim full validation.

## Acceptance criteria

- [ ] The page analyzes all matched IF/WIF theme records in the selected timeline.
- [ ] Every selected month shows up to five themes, counts, percentages, and prominent LDA keywords.
- [ ] Aggregate theme progression is derived only from monthly matched-theme summaries.
- [ ] Identical labels connect only across adjacent months.
- [ ] No semantic similarity or community continuity is inferred in the browser.
- [ ] No persisted path, transition, Jaccard, retained-member, membership-mobility, or theme-similarity visualization remains on the page.
- [ ] The page does not request transitions or theme-similarity data.
- [ ] Topic/theme evidence is matched-only and remains auditable.
- [ ] Provider provenance remains visible.
- [ ] Existing transition and thematic-evolution functionality remains intact elsewhere.
- [ ] No thesis metric, algorithm default, provider behavior, or artifact output changes.
- [ ] Unit, frontend, build, and focused E2E validation pass in the complete environment.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Similar generated labels fragment one conceptual theme. | Preserve saved labels and state the limitation. Do not silently cluster. Propose a separate upstream standardization artifact if thesis-table parity is required. |
| Many months make the matrix crowded. | Use responsive wrapping for short ranges and a local horizontal scroller with sticky month headers for long ranges. |
| Many theme series make the bump chart unreadable. | Limit the chart to the union of monthly top five, direct-label points, selectable highlighting, and an accessible table. |
| Lines imply continuity after a theme disappears. | Break the series at missing months and mark later appearances as re-entry. |
| Evidence controls are mistaken for aggregate filters. | Put them in a separately titled Evidence Explorer and label Evidence month explicitly. |
| Removing page queries accidentally removes project capability. | Delete only page/hook dependencies; preserve APIs, artifacts, models, and Community Transitions behavior. |
| Old URLs contain `themePath` or `topicType=partial`. | Canonicalize safely to the new route scope without breaking page loading. |


## Progress log

### 2026-08-06 — Source inspection and protection

- Treated `community-analysis-frontend-review-20260806-1738.zip` as the source of truth after Patch 037.
- Read the repository harness, architecture, analytical contracts, quality gates, test matrix, and active Plan 037 before editing.
- Preserved all backend trend, transition, membership, and theme-similarity APIs and artifacts.

### 2026-08-06 — Surgical implementation

- Removed transition, persisted-path, retained-member, and saved similarity queries from the Thematic Analysis hook only.
- Forced matched topic evidence on the route and canonicalized obsolete `topicType=partial` and `themePath` URL state without changing shared Topic Modeling behavior.
- Added timeline-wide summary metrics, a monthly top-five theme matrix, and aggregate rank progression derived exclusively from monthly matched-theme summaries.
- Added adjacent-label segmentation, gap breaking, re-entry/exit status, LDA keyword evidence, accessible chart text, and a companion evidence-selection table.
- Kept downstream theme evidence, provider provenance, independent pagination, exact community filtering, and IF/WIF network deep links.
- Updated focused model, hook, page, and Playwright coverage plus the theme-intelligence, verification, and handoff documentation.

### 2026-08-06 — Validation

- Passed TypeScript syntax transpilation for every modified frontend source and test file.
- Passed strict targeted TypeScript checks for the new models, components, hook, and their TypeScript tests using temporary declaration stubs only; no stubs are included in the patch.
- Passed runtime assertions for timeline metrics, adjacent-month segmentation, gap breaking, and re-entry behavior.
- Passed scope-isolation source assertions and `git diff --check`.
- `npm ci` was blocked because the configured package registry returned HTTP 404 for `yargs-parser-21.1.1.tgz`; therefore the canonical Vitest, lint, build, and Playwright commands could not run in this archive.
- `make frontend-check` was consequently blocked by missing installed type packages (`vite/client`, `vitest/globals`, and `@testing-library/jest-dom`).
- `python -m pytest -q tests/unit/test_theme_trend_service.py` was blocked during collection because the review archive omits `src.artifacts`.
- `make test` was blocked because the configured Python registry could not resolve the build requirement `setuptools>=61.0`.

## Rollback plan

Revert Plan 038 as one unit.

Rollback restores the current Plan 037 Thematic Analysis page without changing:

- analytical artifacts;
- transition/similarity APIs;
- database state;
- network/topic/theme pipeline outputs.
