# Community Analysis Thesis Project

This repository contains the thesis codebase for social network/community analysis and theme analysis.

The harness docs have been updated to reflect the actual implemented code features:

- Neo4j relationship export.
- Telegram and Twitter relationship workflows.
- Follower-followee network construction.
- `shared_post` and `weighted_post` edge metrics.
- Absolute and weighted NetworkX graphs.
- Louvain community detection.
- Prominent community filtering.
- Centrality, user/message count, and daily message statistics.
- Exact and partial community comparison.
- Unigram and bigram LDA topic modeling.
- Matched and partially matched community topic comparison.
- GPT theme generation from LDA keywords.
- Month-to-month community transition analysis.
- Sankey transition diagrams.
- Membership-change diagrams.
- TEIClient theme similarity heatmaps.

## Harness Start Point

Read the repository source-of-truth documents in this order before changing
pipeline behavior:

1. `HARNESS.md`
2. `ARCHITECTURE.md`
3. `docs/design-docs/current-code-feature-inventory.md`
4. `docs/product-specs/project-spec.md`
5. `docs/design-docs/data-contract.md`
6. `docs/design-docs/database-contract.md`
7. `docs/design-docs/metric-contract.md`
8. `docs/design-docs/pipeline-contract.md`
9. `docs/design-docs/theme-intelligence-contract.md`
10. `docs/design-docs/output-artifact-contract.md`
11. `docs/verification/quality-gates.md`
12. `docs/verification/test-matrix.md`
13. the relevant active execution plan

The foundational plans (001–004) are complete. New work continues in
`docs/exec-plans/active/` with plan numbers 030+. Before starting new
development, identify the highest-numbered active plan for the area you are
working in and read its status.

## Important Rule

Before refactoring, preserve the current behavior with tests or fixture outputs. Do not change metric definitions, graph thresholds, Louvain defaults, LDA defaults, or GPT theme defaults unless the change is documented as a separate experiment.

## How To Run This Project

By default, the CLI commands use **Prefect** as the local orchestrator. MLflow
tracking is optional and disabled by default in `configs/algorithms.yml`; enable
it only when the tracking extra is installed. Prefect provides task state and
retries, while immutable run manifests remain the source of truth for lineage.

```bash
# Runs the full pipeline via Prefect
python -m src.cli run-all --config tests/configs/test_single_month.yml
```

### 1. Prefect Orchestration (Default)
Prefect orchestrates the sequential network/community, Topic, and Theme stages through `run_monthly_analysis_flow`.
**You do NOT need to run a Prefect server.** The flow executes completely ephemerally (like a standard script).

If you *want* to view the Prefect dashboard to see historical runs:
```bash
prefect server start
```
Tests do not require a dedicated server. Local result payloads are isolated from Prefect state under `.prefect_results/`. To clear only the local Prefect result cache, run `rm -rf .prefect_results/`.

### 2. Local MLflow Experiment Tracking
MLflow tracking is opt-in. Set `tracking.enabled: true` in the selected config
and install the tracking extra. When tracking is disabled the pipeline does not
attempt prompt registration or import MLflow. The immutable run bundle remains
complete without MLflow.

If you enable tracking and want to inspect metrics, parameters, and dataset hashes:
```bash
make mlflow-ui
```
Then open `http://127.0.0.1:5001`. Tracking failures are warning-only and do not alter analytical success.
The registered prompt artifact contains the versioned system/user templates and output schema; per-request keyword payloads are intentionally excluded from the safe provider summary to avoid duplicating potentially sensitive content in MLflow. Aggregate request, cache, token, and latency metrics are tracked when available.

### 3. Local Debugging (`--debug` Flag)
Use `--debug` only when you intentionally want raw Python execution for local
step-through debugging. It bypasses Prefect, MLflow, and canonical run-bundle
finalization:

```bash
python -m src.cli run-all --config tests/configs/test_single_month.yml --debug
```

A debug run is not discoverable by the dashboard API. An AWS Step Functions
implementation may invoke debug-stage containers only if the state machine also
implements the same manifest lifecycle and canonical publication contract.
Otherwise, run the normal non-debug `run-all` command in the batch container.

## Final Handoff Docs

- `docs/DEMO_SCRIPT.md`: presenter script for the offline demo and dashboard walkthrough.
- `docs/HANDOFF.md`: architecture, operations, validation, cleanup, and commit checklist.
- `docs/RELEASE_NOTES.md`: summary of completed modernization work, limitations, and future work.

## Setup

Use Python 3.11.9 or newer. The sample Make targets assume a project-local
virtual environment named `.venv`.

Create and install the local environment:

```bash
make install-dev
```

The project uses a uv dependency group for development tools and optional
extras for orchestration/tracking. The equivalent explicit setup is:

```bash
uv sync --frozen --extra orchestration --extra tracking
```

Install the read-only dashboard dependencies with:

```bash
make frontend-install
```

`frontend/package-lock.json` is the canonical frontend dependency lock and must
remain committed. Production builds use the lock rather than resolving an
unpinned dependency tree.

`pyproject.toml` and the committed `uv.lock` are the canonical Python dependency
contract. Production containers install from the frozen lock.


The thesis topic pipeline expects the pinned English spaCy model. Install it in
local development after dependency sync:

```bash
uv run python -m spacy download en_core_web_sm
```

The production Dockerfile installs and verifies the pinned `en_core_web_sm`
model wheel during the image build. If the model is absent locally, the code
logs a warning and uses a blank English tokenizer for offline tests; that
fallback can change lemmatization and must not be used for thesis-equivalent
production runs.

## Development Quality & CI

This repository uses local `pre-commit` hooks for minimal hygiene and GitHub Actions CI as the authoritative enforcement gate.

To set up local development tools and run CI steps locally, use:

```bash
uv sync --extra orchestration --extra tracking
uv run pre-commit install
uv run pre-commit run --all-files
make test-unit
make test-integration
make test
```

* **Pre-commit is a local convenience**: It fixes simple issues like trailing whitespace and mixed line endings before you commit.
* **CI is the authoritative enforcement gate**: GitHub Actions runs the exact same checks on `main` branch pushes and PRs.
* **Black/Flake8 scope**: Broad codebase formatting with Black and Flake8 is currently deferred (Strategy A) because of extensive legacy formatting. Only low-risk hygiene hooks are active.
* **Updating hook revisions**: Run `uv run pre-commit autoupdate` or edit `.pre-commit-config.yaml` to pin newer versions.
* **Reproduce CI locally**: The commands above run exactly what CI runs.
* **API Credentials**: The full test suite runs entirely offline. Network guards in `tests/conftest.py` block outbound requests. No live API credentials are required to pass tests or CI.

## Canonical Pipeline-to-Dashboard Workflow

The dashboard discovers only immutable run bundles with a completed
`manifest.json`. Use the evolution pipeline with one of the canonical production
configs for a real multi-month analytical run that must become visible through
the API and frontend:

```bash
make run-evolution-pipeline CONFIG=configs/twitter/retweet_quote_evolution.yml
```

On success, the CLI prints the generated run ID and artifact root. Start the API
against the same `output_base_path` configured for the run, then start the
frontend:

```bash
export COMMUNITY_ANALYSIS_ARTIFACT_ROOT=/path/to/output_base_path
uvicorn src.api.app:app --host 0.0.0.0 --port 8000

cd frontend
npm install
npm run dev
```

The Vite development server proxies `/api` to `http://127.0.0.1:8000` by
default. For separate hosts, set `VITE_API_BASE_URL` before building the
frontend.

Stage-only commands (`run-social-network`, `run-topics`, and
`run-theme-analysis`) preserve debugging and thesis-export workflows, but they
do not publish a complete dashboard run. `run-all --debug` also bypasses the
canonical Prefect run-bundle lifecycle and is not API-discoverable. Use plain
`run-all` for dashboard-visible results.

The global network view reads a deterministic, bounded graph sample while
community detail views retain access to the authoritative full graph. Configure
`dashboard.graph_sample_max_edges` to balance initial dashboard latency and
visual density without changing analytical outputs.

For the checked-in sample configuration, the Make targets share the same
artifact root, so this sequence publishes and serves the exact run just created:

```bash
make run-dashboard-sample
make run-api
# in another terminal
make run-frontend
```

## Dashboard release-quality workflow

The dashboard consumes canonical run artifacts through the read-only FastAPI
API. A deterministic fixture is available for frontend quality gates and does
not execute database, provider, model-download, or analytical pipeline code.

```bash
make dashboard-fixture
make api-smoke-test
make frontend-check
```

For browser workflows, install Playwright Chromium once and then run the real
API/Vite integration suite:

```bash
cd frontend && npx playwright install chromium && cd ..
make frontend-e2e
```

The browser suite is offline after the browser binary has been installed. See
`frontend/README.md` for visual-baseline updates and environment overrides.

## Running The Offline Sample

Start with the full offline sample pipeline:

```bash
make run-pipeline-sample
```

This ingests legacy raw CSV relationships, then runs social network/community analysis, topic modeling,
theme intelligence, and artifact indexing from tiny checked-in fixtures. It
does not require Neo4j, Memgraph, Docker, OpenAI, Hugging Face downloads, or
Kaleido.

Sample outputs are written to:

```text
local_output/tests/community-analysis-sample/
local_output/tests/community-analysis-theme-sample/
local_output/tests/community-analysis-sample-interactions.parquet
local_output/tests/community-analysis-artifact-index.md
```

The longitudinal two-month sample writes to:

```text
local_output/tests/community-analysis-evolution-test/
local_output/tests/community-analysis-evolution-test/
local_output/tests/community-analysis-evolution-artifact-index.md
```

## Offline Sample Commands

For a full release/demo proof from generated fixtures, run:

```bash
make demo
```

This runs the one-month sample, output-contract verification, the two-month
evolution sample, evolution verification, artifact indexing, and the read-only API
smoke tests.

Run individual stages with:

```bash
make install-dev
make frontend-install
make test
make validate-config
make ingest-sample
make run-network-sample
make run-topic-sample
make run-theme-sample
make run-pipeline-sample
make run-dashboard-sample
make run-evolution-pipeline-test
make verify-output-contract
make verify-evolution-output-contract
make api-smoke-test
make demo
make demo-api
make demo-frontend
make frontend-install
make frontend-lint
make frontend-typecheck
make frontend-test
make frontend-coverage
make frontend-check
make dashboard-fixture
make frontend-e2e
make frontend-build
make clean-generated
make clean-cache
make build-report
```

What each command does:

- `make test`: runs unit tests.
- `make validate-config`: validates `tests/configs/test_single_month.yml`.
- `make ingest-sample`: converts the legacy `source,target,relation` fixture into derived interaction metrics without importing to a database.
- `make run-network-sample`: runs network/community sample stages and writes internal topic-input prerequisites.
- `make run-topic-sample`: runs only topic modeling from saved topic-input prerequisites. Run `make run-network-sample` first, or use `make run-pipeline-sample`.
- `make run-theme-sample`: runs only theme intelligence from saved theme-input prerequisites. Run `make run-topic-sample` first, or use `make run-pipeline-sample`.
- `make run-pipeline-sample`: runs the legacy stage-by-stage offline sample workflow and writes the artifact index.
- `make run-dashboard-sample`: runs the canonical Prefect sample and publishes a manifest-backed run for the API/dashboard.
- `make run-evolution-pipeline-test`: runs the canonical two-month offline evolution workflow and verifies theme transitions.
- `make run-evolution-pipeline`: runs the multi-month evolution pipeline dynamically using a custom config file (e.g., `make run-evolution-pipeline CONFIG=configs/twitter/reply_evolution.yml`).
- `make verify-output-contract`: validates generated one-month sample artifact paths and schemas without rerunning the pipeline.
- `make verify-evolution-output-contract`: validates generated two-month evolution artifact paths, manifests, hashes, and transitions.
- `make api-smoke-test`: runs offline tests for the read-only artifact API.
- `make demo`: runs the full offline demo proof and read-only API smoke tests.
- `make demo-api`: starts the read-only artifact API for generated demo outputs.
- `make demo-frontend`: starts the Vite dashboard.
- `make frontend-install`: installs dashboard dependencies with `npm ci` when a lockfile is present.
- `make frontend-lint`: lints the read-only dashboard with zero-warning enforcement.
- `make frontend-typecheck`: type-checks the TypeScript API/state boundary and touched components.
- `make frontend-test`: runs offline unit and component tests with strict MSW request handling.
- `make frontend-coverage`: applies focused adapter/state/view-model coverage thresholds.
- `make frontend-check`: runs typecheck, lint, coverage, production build, and bundle-budget checks.
- `make dashboard-fixture`: generates deterministic canonical dashboard runs and integrity variants.
- `make frontend-e2e`: starts the fixture-backed FastAPI/Vite services and runs Chromium workflows.
- `make frontend-build`: builds the route-split dashboard without requiring the API to be running.
- `make clean-generated`: removes only known generated demo outputs and the frontend build output.
- `make clean-cache`: removes Python/test/Vite caches and egg-info without deleting `.venv` or `frontend/node_modules`.
- `make build-report`: writes `local_output/tests/community-analysis-artifact-index.md`.
- `make benchmark-performance`: compares the legacy and indexed community-message implementations and verifies exact output equivalence.

## Direct CLI Usage

The same checks can be run directly through the CLI:

```bash
.venv/bin/python -m src.cli validate-config --config configs/sample_telegram.yml
.venv/bin/python -m src.cli validate-config --config tests/configs/test_single_month.yml
.venv/bin/python -m pytest tests/unit
.venv/bin/python -m src.cli ingest-interactions \
  --file tests/fixtures/sample_relationships.csv \
  --config tests/configs/test_single_month.yml \
  --out local_output/tests/community-analysis-sample-interactions.parquet \
  --no-db
.venv/bin/python -m src.cli run-social-network --config tests/configs/test_single_month.yml --debug
.venv/bin/python -m src.cli run-topics --config tests/configs/test_single_month.yml
.venv/bin/python -m src.cli run-theme-analysis --config tests/configs/test_single_month.yml
.venv/bin/python -m src.cli run-all --config tests/configs/test_single_month.yml --theme-provider mock
.venv/bin/python -m src.cli verify-output-contract --config tests/configs/test_single_month.yml
.venv/bin/python -m src.cli build-report \
  --config tests/configs/test_single_month.yml \
  --out local_output/tests/community-analysis-artifact-index.md
```

`run-topics` reads internal topic-input artifacts from
`<output_base_path>/<data_type>/_intermediate/topic_inputs/<content_type>/<month>_<year>/`.
Run `run-social-network` first when using direct CLI commands.

`run-theme-analysis` reads internal theme-input artifacts from
`<output_base_path>/<data_type>/_intermediate/theme_inputs/<content_type>/<year>/`.
Run `run-topics` first when using direct CLI commands, or set `theme.input_dir`
explicitly for manual fixture runs.

`verify-output-contract` is read-only. It checks generated Parquet artifact paths and schemas,
internal topic/theme-input manifests, theme-input SHA256 hashes, and schema
compatibility between generated matched LDA outputs and copied theme inputs. Raw
`source,target,relation` CSV compatibility remains limited to the ingestion boundary.
Use the internal `--longitudinal` verifier flag with the two-month evolution test
config after `make run-evolution-pipeline-test`.

## Read-Only Artifact API

The dashboard API reads only canonical run bundles created by non-debug
`run-all` below `<artifact_root>/runs/<run_id>/`. It validates manifest-listed files before
returning analytical data and never runs ingestion, NetworkX, Louvain, LDA,
theme providers, TEI, or visualization generation.

Start it with an artifact root that contains the `runs/` directory (for example, the `output_base_path` defined in your config):

```bash
make run-api API_ARTIFACT_ROOT=/path/to/artifacts
# Example: make run-api API_ARTIFACT_ROOT=local_output/twitter/reply_evolution
```

Useful endpoints:

```text
GET /api/v1/health
GET /api/v1/runs?platform=twitter&content_type=reply&year=2017&month=3
GET /api/v1/runs/{run_id}
GET /api/v1/runs/{run_id}/artifacts
GET /api/v1/runs/{run_id}/verification
GET /api/v1/runs/{run_id}/overview
GET /api/v1/runs/{run_id}/network?metric=if&max_nodes=200&max_edges=500
GET /api/v1/runs/{run_id}/communities?metric=wif
GET /api/v1/runs/{run_id}/centrality
GET /api/v1/runs/{run_id}/topics?type=matched
GET /api/v1/runs/{run_id}/themes?month=03
GET /api/v1/runs/{run_id}/transitions
GET /api/v1/runs/{run_id}/persistent-communities
GET /api/v1/runs/{run_id}/membership-changes
GET /api/v1/runs/{run_id}/theme-similarity
GET /api/v1/runs/{run_id}/report
GET /api/v1/runs/{run_id}/downloads/{artifact_key}
```

The OpenAPI document is available at `/openapi.json`. API errors use a stable
JSON envelope with `code`, `message`, `run_id`, and `artifact_key` fields where
applicable.


The API caches only small Parquet tables in process memory. Configure the byte
threshold with `COMMUNITY_ANALYSIS_API_PARQUET_CACHE_MAX_BYTES` (16 MiB by
default); larger artifacts use projected/predicate-pushed reads and are not
retained in the dataframe LRU. The run catalog rejects duplicate run IDs across
discovered roots instead of silently selecting one bundle.

## Read-Only Dashboard

After generating outputs and starting the API, start the Vite dashboard:

```bash
make demo
make demo-api
make demo-frontend
```

The dashboard consumes only `/api/v1` read-only endpoints. It has no controls
for ingestion, network/community analysis, LDA, theme generation,
visualization rendering, database access, or external services.

Frontend checks:

```bash
make frontend-install
make frontend-lint
make frontend-build
```


## DeepEval Benchmark Evaluation

DeepEval is an optional, separate model-benchmark workflow; it is not invoked by
normal network, topic, theme, or longitudinal pipeline commands. Install the
evaluation extra and run the configured benchmark/evaluation target:

```bash
uv sync --frozen --extra eval
make evaluate-sample
```

`benchmark.evaluator_judge: mock` is an offline smoke configuration only. Use a
reviewed real judge provider for meaningful LLM-as-a-judge scores. Optional
DeepEval and MLflow modules are imported lazily, and the evaluation adapter
executes blocking provider calls outside the event loop. Benchmark outputs are
validated before scoring and written to `deepeval_scores.parquet`.

## AWS Deployment Boundary

The backend image is suitable for separate ECS/Fargate roles:

- a batch/task role runs `community-analysis run-all` and writes immutable run
  bundles to a mounted artifact filesystem;
- the API role mounts the same artifact root read-only and serves `/api/v1`;
- the frontend image serves static assets and proxies `/api` to the API service.

The current API reader is filesystem-based. For the first CDK deployment, use a
shared EFS artifact root or materialize completed S3 run bundles onto a
read-only filesystem before serving them. Do not point the API directly at
arbitrary local paths supplied by the browser. A direct S3 `ArtifactStore`
adapter is a separate follow-up and is not required for local reproducibility.

Keep provider/database credentials in Secrets Manager or SSM and inject them as
environment variables; never bake them into either image or a run manifest.

## Optional Database Commands

Memgraph checks are optional integration checks. Use these only when Docker is
available and you intentionally want a local graph database:

```bash
.venv/bin/python -m src.cli db-up
.venv/bin/python -m src.cli db-check --config tests/configs/test_single_month.yml
```

Neo4j export remains a migration path for existing thesis data. Configure
Neo4j connection settings before running export commands; the offline sample
does not need Neo4j.


## Full-Data Performance Guidance

The dominant Retweet/Quote bottleneck was community-message extraction. New
runs build one monthly edge index and reuse it across IF, WIF, and daily message
statistics instead of scanning the full dataframe for every community edge.
Verify the regression benchmark with:

```bash
make benchmark-performance
```

Longitudinal Twitter configs intentionally use:

```yaml
orchestration:
  month_workers: 1
```

Each month already runs `LdaMulticore`; processing several months concurrently
can oversubscribe CPU and memory. Theme requests retain bounded thread
concurrency through `theme.max_workers`.

Long-running stages emit periodic structured logs. Use local text logs by
default and JSON logs for Docker/ECS/CloudWatch:

```bash
export LOG_LEVEL=INFO
export LOG_FORMAT=json
```

Real semantic runs use two explicit, revision-pinned TEI profiles. `make tei-up`
starts both, `make tei-check` verifies both with a lightweight embedding request,
and `make tei-down` stops both:

- similarity: `sentence-transformers/paraphrase-MiniLM-L6-v2` on local port
  `8080` (existing Community Evolution thematic similarity);
- clustering: `sentence-transformers/all-MiniLM-L6-v2` on local port `8081`
  (general-theme HDBSCAN clustering/canonicalization).

Use profile-specific `TEI_SIMILARITY_*` and `TEI_CLUSTERING_*` settings. Legacy
`TEI_*` similarity settings remain backward compatible. Model revisions are
pinned independently because the two analytical tasks intentionally use
different models. When `theme.render_visuals=false`, the Community Evolution
TEI/heatmap stage is skipped; theme clustering is controlled independently by
`theme.clustering_enabled`. Real TEI failures stop the affected analytical stage
rather than silently substituting mock embeddings.

Theme clustering uses `sklearn.cluster.HDBSCAN`; the standalone `hdbscan` Python
package is not required. TEI inference is deduplicated by exact content-addressed
text/model contract, but duplicate theme observations are expanded back before
clustering so density semantics are preserved. Unique vectors produced by the clustering profile, and by the similarity
profile when heatmaps are rendered, are persisted as immutable `float32` Parquet
run artifacts under `data/themes/embeddings/`; no vector database or Memgraph
vector storage is used.

## Production Evolution Runs

Bootstrap the locked local environment once, then preflight each real
evolution configuration before spending compute/provider quota:

```bash
make bootstrap
make tei-up
make pipeline-preflight CONFIG=configs/twitter/reply_evolution.yml
```

`make run-evolution-pipeline` runs the same preflight automatically. Run the
real pipelines sequentially to avoid nested multicore pressure:

```bash
make run-evolution-pipeline CONFIG=configs/twitter/reply_evolution.yml
make run-evolution-pipeline CONFIG=configs/twitter/retweet_quote_evolution.yml
make run-evolution-pipeline CONFIG=configs/telegram/forwarded_message_evolution.yml
```

The preflight checks the locked direct dependency contract,
`sklearn.cluster.HDBSCAN`, required input CSVs, output writability, live-provider
credentials, and only the TEI profiles required by the selected config. Memgraph
is not checked for the evolution command because that path consumes exported
relationship CSVs directly. Tracking remains opt-in; install the `tracking`
extra only when a config enables MLflow.

The Twitter evolution configs each produce one January-April run. The Telegram
forwarded-message evolution config produces one January-October 2019 run from
legacy `source,target,relation` exports, which are normalized through the
existing ingestion boundary before IF/WIF network analysis. The shared SQLite
theme cache is cross-run; do not delete `.cache/theme_cache.sqlite3` unless a
deliberate full provider rerun is required.

## Read-only API container

A dedicated `Dockerfile.api` runs only the dashboard API as a non-root user. It
expects canonical run bundles below `/artifacts` (local bind mount or EFS) and
uses environment configuration for CORS, trusted hosts, root path, graph caps,
and docs exposure. It does not execute analytical pipeline stages.

```bash
docker build -f Dockerfile.api -t community-analysis-api:local .
docker run --rm -p 8000:8000 \
  -v "$PWD/local_output/twitter/retweet_quote_evolution:/artifacts:ro" \
  -e COMMUNITY_ANALYSIS_API_ALLOWED_HOSTS=localhost,127.0.0.1 \
  community-analysis-api:local
```

Use `/api/v1/health` for liveness and `/api/v1/ready` for artifact-mount
readiness. Direct S3 artifact access is not implemented; use EFS for the first
AWS deployment or add an explicit `ArtifactStore` adapter later.
