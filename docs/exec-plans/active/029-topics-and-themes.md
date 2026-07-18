# Plan 029 — Topics and Themes

Status: active

Owner: agent

Last updated: 2026-07-18

## Goal

Replace the Thematic Analysis route's fabricated theme cards, distributions,
heatmaps, and community details with canonical matched/partial LDA records and
downstream theme labels, while making the LDA-to-theme relationship explicit.

## Dependencies

- Plans 026–028 are complete.
- Community identifier normalization is shared and tested.
- API clients for topics, themes, overview, and theme similarity exist.

## Non-Goals

- No topic modeling or theme generation in the browser.
- No replacement of LDA outputs with LLM-only summaries.
- No claim that provider-generated theme labels are raw topics.
- No frontend re-clustering of themes with HDBSCAN.
- No fabricated topic percentages, sentiment, or community reach.

## Files Expected To Change

- `frontend/src/pages/ThematicAnalysis.jsx`
- `frontend/src/features/topics/` (new)
- `frontend/src/features/themes/` (new)
- `frontend/src/components/KeywordList.tsx` (new)
- `frontend/src/components/ThemeLabel.tsx` (new)
- `frontend/src/components/ProviderMetadata.tsx` (new)
- `frontend/src/components/SimilarityMatrix.tsx` (new or shared with Plan 030)
- `frontend/src/utils/artifactValues.ts` (new)
- relevant tests
- `docs/exec-plans/active/029-topics-and-themes.md`

## Milestone 1 — Define Safe Semantic Record Adapters

Tasks:

- [x] Create a safe normalization utility for API fields typed as `Any`:
      - `null`/undefined;
      - arrays;
      - objects/maps;
      - numbers/booleans;
      - plain strings;
      - JSON-encoded strings where parsing is unambiguous.
- [x] Do not parse Python literals with code execution. If a non-JSON serialized
      value cannot be normalized safely, display the original string.
- [x] Create a `TopicViewModel` exposing:
      - record type matched/partial;
      - IF/absolute community ID;
      - WIF/weighted community ID;
      - Jaccard score when available;
      - unigram topic/keywords for each metric;
      - bigram topic/keywords for each metric;
      - common/uncommon members when available.
- [x] Create a `ThemeViewModel` exposing:
      - month;
      - IF/WIF community IDs;
      - general, IF/absolute, and WIF/weighted theme names;
      - associated keywords;
      - provider metadata.
- [x] Add tests using the exact API schemas and representative normalized values.

## Milestone 2 — Make Thematic Controls Functional

Tasks:

- [x] Replace the fake “topic granularity” control with supported controls:
      - topic record type: matched or partial;
      - token view: unigram or bigram;
      - metric view: IF, WIF, or side-by-side;
      - optional exact community ID filter.
- [x] Store controls in URL search parameters so links are reproducible.
- [x] Validate values and use defaults: matched, side-by-side, unigram.
- [x] Month filtering applies only to `/themes` and uses month values present in
      theme records; do not invent months.
- [x] Explain that matched/partial concerns structural community matching, while
      unigram/bigram concerns LDA keyword representation.

## Milestone 3 — Replace Thematic KPI Cards

Tasks:

- [x] Use supported counts:
      - `overview.top_themes.length` or unique theme-label count in current page;
      - topics response total;
      - themes response total;
      - matched percentage from overview;
      - provider/model metadata availability.
- [x] Avoid “most diverse,” “hottest,” or “dominant platform” metrics unless they
      are derived transparently from current response data and labelled as
      presentation summaries.
- [x] Show `null`/missing semantic artifacts as unavailable rather than zero.

## Milestone 4 — Build the Topic and Theme Browser

Tasks:

- [x] Render a paginated list/table of topic records with IF and WIF side-by-side.
- [x] Each record should show community IDs, Jaccard score, selected unigram or
      bigram keywords, and member-overlap fields when available.
- [x] Add a selected-record panel with all topic fields and links to the selected
      metric's network community.
- [x] Render theme records as human-readable labels and keyword evidence.
- [x] Clearly label provider-generated theme fields separately from LDA topic
      fields.
- [x] Display provider metadata from `ThemesResponse.provider_metadata` and model
      metadata from Overview without assuming OpenAI or GPT-4.
- [x] Add pagination for topics and themes independently.
- [x] On artifact unavailable, explain the required pipeline stage rather than
      showing fabricated theme cards.

## Milestone 5 — Implement Theme Summary Visuals from Real Data

Tasks:

- [x] Replace fixed percentages with a theme-frequency summary computed from
      returned/canonical theme names. State the denominator and whether data is a
      page or full result set.
- [x] Prefer requesting enough records to compute a complete small-run summary;
      when the total exceeds the safe cap, display a paginated list instead of a
      misleading partial chart.
- [x] Use stable theme colors generated from theme names.
- [x] A heatmap may be shown only from `/theme-similarity`:
      - render `matrix` and `labels` when present;
      - otherwise display manifest-listed image artifacts through download URLs;
      - otherwise show optional artifact unavailable.
- [x] Include accessible table/text alternatives for any matrix visualization.
- [x] Do not compute new sentence embeddings in the browser.

## Milestone 6 — Connect Semantic Views to Structural Views

Tasks:

- [x] From a topic/theme record, provide “Open IF community” and “Open WIF
      community” links when IDs are present.
- [x] Preserve run ID and set the corresponding metric in the destination URL.
- [x] From the Network/Top Communities detail panel, provide a link back to the
      Thematic route filtered to the selected community.
- [x] Handle records where only one metric/community is present.

## Tests

- [x] safe value normalization without code execution;
- [x] matched and partial record adapters;
- [x] unigram/bigram and metric controls update query/UI;
- [x] provider metadata for non-OpenAI providers;
- [x] topic and theme pagination;
- [x] artifact unavailable states;
- [x] theme similarity matrix and artifact-only fallback;
- [x] structural/semantic deep links preserve run and metric;
- [x] empty responses never show mock topics or percentages.

## Acceptance Criteria

- [x] Thematic Analysis uses only `/topics`, `/themes`, `/overview`, and optional
      `/theme-similarity` data.
- [x] The UI visibly preserves the analytical order: LDA topics/keywords first,
      provider theme labels downstream.
- [x] No hard-coded theme counts, distributions, communities, or provider names
      remain.
- [x] Matched vs partial, unigram vs bigram, and IF vs WIF controls are functional
      and URL-restorable.
- [x] Tests, typecheck, lint, and build pass.

## Decision Log

| Date | Decision | Reason |
|---|---|---|
| 2026-07-18 | Parse only unambiguous JSON strings in the frontend semantic adapters. | API `Any` fields may contain heterogeneous values; preserving non-JSON text avoids executable parsing and prevents misrepresenting Python-style literals. |
| 2026-07-18 | Use `semanticMetric` separately from the global `metric` URL parameter. | The semantic route needs a side-by-side display mode while the global structural metric remains exactly `if` or `wif`. |
| 2026-07-18 | Cap complete theme-frequency summaries at 500 records and suppress partial aggregation above the cap. | The themes endpoint hard-caps pages at 500; withholding a partial chart is more accurate than presenting a page as the full distribution. |
| 2026-07-18 | Render theme similarity only from the API matrix or manifest-key download URLs. | This preserves saved pipeline outputs and prevents browser-side embedding or similarity recomputation. |
| 2026-07-18 | Limit Vitest to four workers. | The expanded offline component suite exhausted the high default worker count in the execution environment; the bounded pool makes the documented test command deterministic without changing test behavior. |
| 2026-07-18 | Make no backend route, schema, metric, topic-model, or provider changes. | All Plan 029 requirements were satisfied through the existing read-only API contract. |

## Risks

| Risk | Mitigation |
|---|---|
| Theme fields contain heterogeneous serialized values. | Normalize safely, preserve raw text when uncertain, and test representative artifacts. |
| Full theme-frequency summary requires all pages. | Avoid partial aggregation or label it explicitly; prefer table/list for large totals. |
| Provider metadata is absent for cached/mock runs. | Show “Provider metadata unavailable” without inferring a model. |

## Rollback Plan

Revert the feature branch. Keep the real structural pages. If similarity
visualization is blocked, ship the topic/theme browser and render a clear
optional-artifact state for similarity rather than retaining the old mock
heatmap.

## Progress Log

| Date | Update |
|---|---|
| 2026-07-18 | Plan created. |
| 2026-07-18 | Confirmed `HARNESS.md` and root `ARCHITECTURE.md` are absent from the uploaded source, then reviewed the repository contracts, active dependency plans, topic/theme/evolution schemas, services, and existing frontend semantic route. |
| 2026-07-18 | Added safe semantic value normalization, typed topic/theme adapters, URL-backed matched/partial, unigram/bigram, side-by-side metric, exact community, and theme-month controls. |
| 2026-07-18 | Replaced all fabricated thematic KPIs, distributions, heatmaps, community rows, provider names, and prose with canonical topic/theme/overview/similarity data or explicit unavailable states. |
| 2026-07-18 | Added independent topic/theme pagination, complete-result theme-frequency summaries, provider/model provenance, accessible saved similarity matrices, artifact-only fallbacks, and metric-aware structural deep links in both directions. |
| 2026-07-18 | Added adapter, normalization, control, pagination, provider, matrix, artifact-fallback, empty-state, and deep-link tests. No browser-side LDA, clustering, theme generation, embeddings, or backend changes were introduced. |
| 2026-07-18 | Validation: backend API tests 10 passed; frontend typecheck passed; 25 frontend test files / 59 tests passed; lint completed with 0 errors and 3 pre-existing unused-import warnings in Reports and Comparative Analysis; production build passed. The existing Vite main-chunk size warning remains deferred to the frontend quality/performance plan. |
