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
- SentenceTransformer theme similarity heatmaps.

## Harness Start Point

Ask your local agent to read:

1. `AGENTS.md`
2. `HARNESS.md`
3. `ARCHITECTURE.md`
4. `docs/design-docs/current-code-feature-inventory.md`
5. `docs/product-specs/project-spec.md`
6. `docs/design-docs/metric-contract.md`
7. `docs/design-docs/pipeline-contract.md`
8. `docs/design-docs/theme-intelligence-contract.md`

Then implement plans in this order:

1. `docs/exec-plans/active/001-baseline-and-foundation.md`
2. `docs/exec-plans/active/002-database-and-ingestion.md`
3. `docs/exec-plans/active/003-network-community-topic-pipeline.md`
4. `docs/exec-plans/active/004-theme-intelligence.md`

## Important Rule

Before refactoring, preserve the current behavior with tests or fixture outputs. Do not change metric definitions, graph thresholds, Louvain defaults, LDA defaults, or GPT theme defaults unless the change is documented as a separate experiment.

## Prefect Orchestration (Foundation)

Prefect 3 is now available as an optional orchestration foundation. The full pipeline is not yet orchestrated, and direct domain execution remains fully supported.

Optional local UI command:
```bash
prefect server start
```

Tests do not require a server. Local results and small metadata payloads are directed to a private directory isolated from the Prefect SQLite database:
```text
.prefect_results/
```
To safely clear the local result cache, simply remove this directory: `rm -rf .prefect_results/`.

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

If you already activated another virtual environment, the equivalent install
command is:

```bash
python -m pip install -e ".[dev]"
```

Install the read-only dashboard dependencies with:

```bash
make frontend-install
```

`pyproject.toml` is the canonical Python dependency declaration. The
`requirements.txt` file is only a compatibility wrapper for hosts that expect
one.

## Development Quality & CI

This repository uses local `pre-commit` hooks for minimal hygiene and GitHub Actions CI as the authoritative enforcement gate.

To set up local development tools and run CI steps locally, use:

```bash
uv sync --extra orchestration
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

## Running The Offline Sample

Start with the full offline sample pipeline:

```bash
make run-pipeline-sample
```

This runs CSV ingestion, social network/community analysis, topic modeling,
theme intelligence, and artifact indexing from tiny checked-in fixtures. It
does not require Neo4j, Memgraph, Docker, OpenAI, Hugging Face downloads, or
Kaleido.

Sample outputs are written to:

```text
/tmp/community-analysis-sample/
/tmp/community-analysis-theme-sample/
/tmp/community-analysis-sample-interactions.csv
/tmp/community-analysis-artifact-index.md
```

The longitudinal two-month sample writes to:

```text
/tmp/community-analysis-longitudinal-sample/
/tmp/community-analysis-longitudinal-theme-sample/
/tmp/community-analysis-longitudinal-artifact-index.md
```

## Offline Sample Commands

For a full release/demo proof from generated fixtures, run:

```bash
make demo
```

This runs the one-month sample, output-contract verification, the longitudinal
sample, longitudinal verification, artifact indexing, and the read-only API
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
make run-longitudinal-sample
make verify-output-contract
make verify-longitudinal-output-contract
make api-smoke-test
make demo
make demo-api
make demo-frontend
make frontend-install
make frontend-lint
make frontend-build
make clean-generated
make clean-cache
make build-report
```

What each command does:

- `make test`: runs unit tests.
- `make validate-config`: validates `configs/sample_twitter_reply.yml`.
- `make ingest-sample`: converts the legacy `source,target,relation` fixture into derived interaction metrics without importing to a database.
- `make run-network-sample`: runs network/community sample stages and writes internal topic-input prerequisites.
- `make run-topic-sample`: runs only topic modeling from saved topic-input prerequisites. Run `make run-network-sample` first, or use `make run-pipeline-sample`.
- `make run-theme-sample`: runs only theme intelligence from saved theme-input prerequisites. Run `make run-topic-sample` first, or use `make run-pipeline-sample`.
- `make run-pipeline-sample`: runs the offline sample workflow and writes the artifact index.
- `make run-longitudinal-sample`: runs a two-month offline workflow and verifies longitudinal theme transitions.
- `make verify-output-contract`: validates generated one-month sample artifact paths and schemas without rerunning the pipeline.
- `make verify-longitudinal-output-contract`: validates generated two-month longitudinal artifact paths, manifests, hashes, and transitions.
- `make api-smoke-test`: runs offline tests for the read-only artifact API.
- `make demo`: runs the full offline demo proof and read-only API smoke tests.
- `make demo-api`: starts the read-only artifact API for generated demo outputs.
- `make demo-frontend`: starts the Vite dashboard.
- `make frontend-install`: installs dashboard dependencies with `npm ci` when a lockfile is present.
- `make frontend-lint`: lints the read-only dashboard.
- `make frontend-build`: builds the dashboard without requiring the API to be running.
- `make clean-generated`: removes only known generated demo outputs and the frontend build output.
- `make clean-cache`: removes Python/test/Vite caches and egg-info without deleting `.venv` or `frontend/node_modules`.
- `make build-report`: writes `/tmp/community-analysis-artifact-index.md`.

## Direct CLI Usage

The same checks can be run directly through the CLI:

```bash
.venv/bin/python -m src.cli validate-config --config configs/sample_telegram.yml
.venv/bin/python -m src.cli validate-config --config configs/sample_twitter_reply.yml
.venv/bin/python -m pytest tests/unit
.venv/bin/python -m src.cli ingest-interactions \
  --file tests/fixtures/sample_relationships.csv \
  --config configs/sample_twitter_reply.yml \
  --out /tmp/community-analysis-sample-interactions.csv \
  --no-db
.venv/bin/python -m src.cli run-social-network --config configs/sample_twitter_reply.yml
.venv/bin/python -m src.cli run-topics --config configs/sample_twitter_reply.yml
.venv/bin/python -m src.cli run-theme-analysis --config configs/sample_twitter_reply.yml
.venv/bin/python -m src.cli verify-output-contract --config configs/sample_twitter_reply.yml
.venv/bin/python -m src.cli build-report \
  --config configs/sample_twitter_reply.yml \
  --out /tmp/community-analysis-artifact-index.md
```

`run-topics` reads internal topic-input artifacts from
`<output_base_path>/<data_type>/_intermediate/topic_inputs/<content_type>/<month>_<year>/`.
Run `run-social-network` first when using direct CLI commands.

`run-theme-analysis` reads internal theme-input artifacts from
`<output_base_path>/<data_type>/_intermediate/theme_inputs/<content_type>/<year>/`.
Run `run-topics` first when using direct CLI commands, or set `theme.input_dir`
explicitly for manual fixture runs.

`verify-output-contract` is read-only. It checks generated public thesis CSVs,
internal topic/theme-input manifests, theme-input SHA256 hashes, and schema
compatibility between public matched LDA outputs and copied theme inputs. Use
`--longitudinal` with the April longitudinal config after
`make run-longitudinal-sample`.

## Read-Only Artifact API

After generating sample outputs, start the read-only backend API with:

```bash
make run-api
```

The API serves generated artifacts only. It does not run ingestion, network,
community, topic, theme, visualization, database, or model code.

Useful endpoints:

```text
GET /api/v1/health
GET /api/v1/runs
GET /api/v1/runs/{run_id}/facets
GET /api/v1/runs/{run_id}/verification
GET /api/v1/runs/{run_id}/artifacts
GET /api/v1/runs/{run_id}/community-summary?month=03
GET /api/v1/runs/{run_id}/topics?month=03&type=matched
GET /api/v1/runs/{run_id}/themes?month=03
GET /api/v1/runs/{run_id}/transitions
```

Override configured API runs with:

```bash
COMMUNITY_ANALYSIS_API_CONFIGS=configs/sample_twitter_reply.yml,configs/longitudinal/sample_twitter_reply_04.yml \
.venv/bin/python -m uvicorn backend.main:app --reload
```

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

## Optional Database Commands

Memgraph checks are optional integration checks. Use these only when Docker is
available and you intentionally want a local graph database:

```bash
.venv/bin/python -m src.cli db-up
.venv/bin/python -m src.cli db-check --config configs/sample_twitter_reply.yml
```

Neo4j export remains a migration path for existing thesis data. Configure
Neo4j connection settings before running export commands; the offline sample
does not need Neo4j.
