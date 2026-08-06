# Final Handoff

## Architecture and state ownership

- The CLI pipeline remains under `src.cli`; its analytical metrics, defaults,
  public artifacts, and offline sample workflows are unchanged.
- FastAPI is a read-only adapter over verified `runs/<run_id>/manifest.json`
  bundles. It never executes ingestion, NetworkX, Louvain, LDA, providers, TEI,
  or visualization generation in request paths.
- The Vite/React dashboard consumes only `/api/v1`. The typed API boundary is
  under `frontend/src/api/`.
- `DashboardProvider` owns only global run, IF/WIF metric, health, selected-run
  metadata, and verification state. Run and metric are URL search parameters.
- The Overview route additionally owns `period=YYYY-MM`, `networkView`,
  `sampling`, and optional `community` search state. Its KPI cards and graph are
  monthly; its longitudinal summary is run-level. The default community structure
  map uses the complete published monthly community summary. The optional user
  view is a deterministic bounded sample.
- Each route owns its filters, pagination, TanStack Query keys, and canonical
  record adapters. Community IDs remain strings and IF/WIF identifiers stay
  distinct.
- Route pages are lazy-loaded. Graph, chart, React, and data vendors are split
  into separate chunks.

## API-to-route map

| Route | Canonical API data |
|---|---|
| Overview | period-aware overview, complete published community summaries, deterministic monthly user samples, centrality leaders, monthly themes, optional run-level transitions |
| Community Network | network, communities, community detail, centrality, optional topics/themes |
| Thematic Analysis | overview, matched/partial topics, themes, optional theme similarity |
| Evolution | run catalog plus compatible-run overviews |
| Community Transitions | transitions, persistent communities, membership changes, theme similarity |
| Comparative Analysis | explicit Twitter/X and Telegram run overviews and theme labels |
| Top Communities | communities, community detail, optional topic/theme enrichment |
| Data Explorer | communities, centrality, topics, themes, transitions, artifacts |
| Reports | artifacts, verified inline report, manifest-key downloads |
| Methodology | run detail, overview config/model metadata, verification, artifact categories |

## Deterministic dashboard fixture

```bash
make dashboard-fixture
```

This writes `/tmp/community-dashboard-fixture` through canonical artifact
models and manifest validation. It includes real API shapes plus no-run,
missing-optional, empty-table, sampled-graph, and tampered-checksum variants.
The generator does not call databases, providers, TEI, models, or pipeline
analysis.

## Quality commands

```bash
make api-smoke-test
make frontend-typecheck
make frontend-lint
make frontend-test
make frontend-coverage
make frontend-build
make frontend-check
```

Install Playwright Chromium once, then execute the real integration workflows:

```bash
cd frontend && npx playwright install chromium && cd ..
make frontend-e2e
```

The browser suite starts its own fixture-backed API and Vite servers. Use
`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` only to opt into a trusted system browser.
Use `PLAYWRIGHT_HOST` only when loopback is unavailable in a controlled test
environment.

Intentional visual changes require:

```bash
cd frontend
npm run test:e2e:update
```

Review and commit the resulting route snapshots. Missing baselines are skipped
with an explicit reason; they are never manufactured by the test harness.

## Troubleshooting

- **No runs**: generate the canonical fixture or a canonical pipeline run and
  confirm `COMMUNITY_ANALYSIS_ARTIFACT_ROOT` points at the directory containing
  `runs/`.
- **Verification failure**: inspect the error code and regenerate or restore the
  manifest-listed artifact. Do not bypass checksum/schema validation.
- **API unavailable**: check `/api/v1/health`, port 8000, and the Vite `/api`
  proxy.
- **Playwright browser missing**: run `npx playwright install chromium`; the
  browser tests make no network calls after installation.
- **Ports already in use**: stop services on 8000/4173. Playwright deliberately
  refuses to reuse them so the fixture cannot be mixed with stale servers.
- **Visual snapshot skipped**: run `npm run test:e2e:update` in a reviewed,
  browser-capable environment and commit the generated baseline.
- **Bundle budget failure**: inspect `frontend/dist/assets`; keep route code lazy
  and do not move graph/chart imports into the shell.

## Known limitations

- The dashboard is read-only and provides no authentication or cloud deployment.
- Large network reads remain bounded by backend caps and presentation limits.
- Published prominent-community graph artifacts are induced within-community subgraphs; the API exposes this limitation and never fabricates inter-community edges.
- Sorting/filtering is labelled page-local where the API does not provide a
  server-wide operation.
- Theme-frequency charts are withheld when a complete safe result set cannot be
  obtained.
- Visual regression baselines must be generated and reviewed on each supported
  browser/OS target before claiming a visual release gate for that target.

## Commit hygiene

Commit source, tests, docs, lockfiles, and reviewed visual snapshots. Do not
commit `.venv/`, `frontend/node_modules/`, `frontend/dist/`, coverage,
Playwright reports/results, Python caches, generated dashboard fixtures, local
`.env` files, credentials, or absolute machine paths.

## Guardrails

Do not change `shared_post`, `weighted_post`, graph thresholds, Louvain defaults,
LDA defaults, output categories, public schemas, API contracts, or the
LDA-before-theme analytical order without an approved execution plan and
behavior-preservation tests.

## Performance handoff

- `CommunityMessageIndex` is the required path for full-data IF/WIF community
  message extraction. Do not restore per-edge dataframe filtering.
- `make benchmark-performance` is the regression benchmark and verifies exact
  output equivalence against the retained legacy reference.
- Longitudinal configs default to `orchestration.month_workers: 1` because each
  monthly topic stage uses `LdaMulticore`.
- Progress is emitted through structured logs for community extraction, topic
  stages, and theme-provider requests. Use `LOG_FORMAT=json` in ECS/Batch.
- Memgraph interaction imports use bounded `UNWIND` batches; database writes
  must not regress to one transaction per interaction edge.
- New runs contain community summaries, graph samples, and node indexes. The API
  uses these for bounded multi-month reads while full graph artifacts remain
  authoritative.

- API workers cache only small Parquet artifacts; tune
  `COMMUNITY_ANALYSIS_API_PARQUET_CACHE_MAX_BYTES` rather than increasing the
  dataframe LRU for full graphs. Duplicate manifest run IDs are rejected.
- The production container pins and validates `en_core_web_sm`; install the
  model locally before thesis-equivalent LDA runs.

## Optional service handoff

- MLflow is disabled by default. Enable `tracking.enabled` only with the
  tracking extra installed. Tracking failure does not invalidate a completed
  analytical bundle.
  Prompt-template/schema versions and aggregate provider metrics are logged; per-request prompt payloads remain outside the safe summary.
- OpenAI usage is recorded when returned by the provider; cost is not trustworthy
  until an explicit reviewed pricing table is configured.
- TEI mock embeddings are test-only. Real similarity rendering fails on TEI
  errors instead of silently changing the analytical method.
- DeepEval remains a separate benchmark/evaluation workflow and is not a
  prerequisite for normal pipeline execution.

  Its optional dependencies are lazy; the mock judge is a smoke test, not a
  meaningful quality evaluation.

## AWS next step

The next plan may start CDK work using separate frontend, API, and analytical
job roles. The current application boundary is ready for ECS/Fargate or AWS
Batch with a shared EFS artifact root. The API remains filesystem based; direct
S3 access is not implemented and requires a dedicated `ArtifactStore`, object
catalog, download/streaming, and checksum-validation adapter.

Before creating infrastructure, run:

```bash
uv sync --frozen --extra orchestration --extra tracking
make test
make frontend-check
python -m build
docker build -t community-analysis:local .
docker run --rm community-analysis:local --help
```
