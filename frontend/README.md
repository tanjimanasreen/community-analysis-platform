# Community Analysis Dashboard

This Vite/React app is a read-only dashboard for generated community-analysis
artifacts. It consumes the backend `/api/v1` artifact API and does not run any
pipeline stages.

## Setup

From the project root:

```bash
make frontend-install
```

This uses `npm ci` against the checked-in `package-lock.json`.

## Development

Generate sample artifacts and start the backend API from the project root:

```bash
make demo
make demo-api
```

Then start the dashboard:

```bash
make demo-frontend
```

The direct frontend command is:

```bash
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000` during local development. The
client defaults to:

```text
VITE_API_BASE_URL=/api/v1
```

Override it in a local `.env` file only when needed. Do not commit secrets or
machine-specific absolute paths.

## State and API ownership

Global dashboard state is limited to the selected canonical run and affinity
metric (`if` or `wif`). Both are stored in the URL as `run` and `metric` search
parameters and are managed by `DashboardProvider`.

Page-specific filters and API queries belong inside their feature/page. The
application shell must not prefetch community, topic, theme, or evolution data
for every route.

The typed API boundary lives under `src/api/` and mirrors the backend Pydantic
schemas in `src/types/api.ts`. The frontend does not use legacy `/facets`,
`/community-summary`, or `/files` routes.

## Checks

From the frontend directory:

```bash
npm run typecheck
npm run lint
npm run test -- --run
npm run build
npm run check
```

Equivalent Make targets are available:

```bash
make frontend-typecheck
make frontend-lint
make frontend-test
make frontend-build
make frontend-check
```

Unit tests run without a backend or internet connection. The build is static
and does not require the API to be running.

Playwright is installed for later end-to-end coverage. Run its current suite
with:

```bash
npm run test:e2e
```

## Structural analysis routes

The Network, Top Communities, and Data Explorer routes consume only canonical,
run-scoped API records:

- **Community Network** requests a bounded graph for the selected `run` and
  `metric`. Its selected `community` and applied `minWeight` filter are stored in
  the URL. Degree values shown by the graph are presentation calculations within
  the returned subgraph, not new thesis metrics. Sampling labels use the API's
  available and returned counts.
- **Top Communities** uses server pagination and displays only community ID, node
  count, edge count, and metric-aware total weight. Sorting is explicitly local
  to the loaded page because the backend does not expose a sort parameter.
- **Data Explorer** provides independent modes for communities, centrality,
  matched topics, partial topics, themes, transitions, and artifacts. Exact
  community-ID filtering is used only where the endpoint supports it; other
  filters are labelled “Filter this page.”

Community identifiers are preserved as strings and IF/WIF identifiers remain
separate. Semantic enrichment is shown only when an exact metric-aware match is
available. Artifact downloads use manifest keys, and intermediate artifacts are
shown as unavailable for download in accordance with the backend contract.

## Semantic analysis route

The Thematic Analysis route is a read-only browser over canonical semantic
artifacts. Its URL-backed controls are:

- `topicType=matched|partial` for structural IF/WIF community matching;
- `token=unigram|bigram` for the saved LDA keyword representation;
- `semanticMetric=both|if|wif` for the display layout;
- `semanticCommunity=<community_id>` for exact server-side community filtering;
- `themeMonth=<month>` for filtering monthly theme records only.

The route always presents LDA topics and keyword evidence before downstream
provider-generated theme labels. Provider/model metadata is rendered exactly as
reported by the API and no provider is inferred when metadata is missing.
Theme-frequency summaries are shown only when the complete filtered result fits
the 500-record safe cap. Theme similarity is rendered only from the saved
`/theme-similarity` matrix or its manifest-listed report artifacts; the browser
does not calculate embeddings or run topic/theme generation.

Topic and theme records link to the corresponding IF or WIF community while
preserving the selected run. Community detail panels provide the reverse link
back to the semantic route with the exact metric-aware community filter.

## Longitudinal, comparison, report, and methodology routes

The remaining analytical routes are read-only views over canonical run
artifacts:

- **Evolution Over Time** groups completed runs by the same platform and content
  type, loads their overview records, and plots one compatible unit at a time.
  Missing values stay unavailable, and configuration differences are shown as
  warnings rather than hidden.
- **Community Transitions** loads transitions, persistent communities,
  membership changes, and theme similarity independently. The Sankey uses saved
  Jaccard membership similarity, tables preserve canonical community IDs, and
  CSV exports contain only the loaded real records.
- **Comparative Analysis** requires an explicit Twitter/X run and an explicit
  Telegram run. It compares only shared overview fields and exact normalized
  top-theme label overlap, with visible content, date, configuration, model, and
  artifact-availability warnings.
- **Reports** is a manifest-backed artifact library. It does not create or
  schedule reports, and intermediate artifacts remain unavailable for download.
- **Methodology** separates protected thesis defaults from selected-run
  configuration, provider/model metadata, and artifact categories. Theme labels
  are shown as downstream interpretations of LDA keyword evidence.

These routes do not execute pipelines, recalculate community detection, invoke
an LLM, or infer missing run metadata in the browser.
