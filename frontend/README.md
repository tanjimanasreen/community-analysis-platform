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

## Quality checks

From the frontend directory:

```bash
npm run typecheck
npm run lint
npm run test -- --run
npm run test:coverage
npm run build
npm run bundle:check
npm run check
```

Equivalent repository-level targets are available:

```bash
make frontend-typecheck
make frontend-lint
make frontend-test
make frontend-coverage
make frontend-build
make frontend-check
```

Vitest uses exact MSW handlers, rejects unhandled requests, and never needs a
running backend or internet connection. Coverage is intentionally focused on
API/state adapters and feature view models rather than icon markup.

The production build is route-split. The bundle gate keeps the initial entry
below 300 KiB minified and non-route application chunks below 500 KiB. Graph,
chart, React, and data libraries are emitted as separate chunks.

## Canonical dashboard fixture and Playwright

Build the deterministic artifact root without running the analytical pipeline:

```bash
make dashboard-fixture
```

The generator writes `/tmp/community-dashboard-fixture` by default. It uses the
canonical manifest models and includes completed Twitter/X and Telegram runs,
compatible monthly history, IF/WIF graph data, semantic and longitudinal
artifacts, a report, and deliberate no-run, missing-artifact, empty-table,
sampled-graph, and tampered-checksum variants.

Install Chromium once for Playwright, then run the browser workflows:

```bash
cd frontend
npx playwright install chromium
cd ..
make frontend-e2e
```

After the browser binary is installed, the suite is offline: Playwright starts
the real FastAPI service against the generated fixture and a local Vite server.
A managed/system Chromium can be selected explicitly with
`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`; the project never silently selects one.

Generate or intentionally refresh visual baselines in a browser-capable
environment with:

```bash
cd frontend
npm run test:e2e:update
```

Commit the resulting `tests/e2e/visual-regression.spec.ts-snapshots/` files.
Until a baseline exists for a route, that visual assertion is reported as
skipped rather than accepting a fabricated image. Functional and axe workflows
remain independent of visual baselines. Playwright traces and screenshots are
kept only for failures, and generated reports are ignored by Git.

## Structural analysis and Data & Reports route

The Communities and Research Data & Reports routes consume only canonical persisted API records:

- **Communities** is the canonical structural drill-down workspace. It is keyed
  by `(run, period, metric, community_id)`, because community IDs are month-local.
  The first section is a paginated monthly Community Directory; one selected
  community then drives its structural summary, bounded member interaction graph,
  LDA evidence, downstream theme labels, and graph coverage/provenance. The
  `minWeight` URL control filters only the returned member graph and never reruns
  Louvain or changes community membership. Degree values shown in graph tooltips
  describe only the returned graph and are not new thesis metrics.
- Legacy **`/network`** and **`/top-communities`** URLs redirect to
  **`/communities`** while preserving their query state.
- **Research Data & Reports** (`/data-reports`) is the canonical persisted-record and run-output workspace. Its `view=` state is URL-backed and grouped by thesis dimension: Structural · RQ1 (Communities, Centrality), Semantic · RQ2 (Matched LDA, Partial-match LDA, Generated Themes), Temporal · RQ3/RQ4 (Community Transitions), and Run Outputs (Artifacts & Reports). Month-local evidence resolves a canonical `period`; Communities/Centrality alone expose a local IF/WIF control, while paired semantic and longitudinal evidence do not pretend to use one global affinity filter. Exact community-ID filtering remains server-side where supported.
- Legacy **`/evidence`**, **`/data`**, and **`/reports`** URLs redirect to **`/data-reports`** while preserving query state. `/data` defaults to `view=communities`; `/reports` defaults to `view=outputs` when no explicit view is supplied.

Community identifiers are preserved as strings and interpreted within their canonical month/metric scope. Artifact downloads use manifest keys, and intermediate artifacts remain visible for provenance but unavailable for download in accordance with the backend contract.

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

## Longitudinal, comparison, output, and methodology routes

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
- **Data & Reports · Artifacts & Reports** is the single manifest-backed output library. It does not create or schedule reports; it opens only already-produced report artifacts and keeps intermediate artifacts unavailable for download.
- **Methodology** separates protected thesis defaults from selected-run
  configuration, provider/model metadata, and artifact categories. Theme labels
  are shown as downstream interpretations of LDA keyword evidence.

These routes do not execute pipelines, recalculate community detection, invoke
an LLM, or infer missing run metadata in the browser.
