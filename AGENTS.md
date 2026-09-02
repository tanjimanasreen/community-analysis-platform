# AGENTS.md

This repository contains the production rebuild of a thesis codebase for social
network/community analysis and theme analysis. The original thesis scripts are
historical provenance. The live system is the `src/` Python package.

Use this file as the entry point. It is a map, not the full manual.

## Read First

Before changing code, read these files in order:

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
13. The relevant active plan in `docs/exec-plans/active/`

## Current Codebase

The production system lives entirely in the `src/` Python package. The original
thesis scripts (`neo4j_data_fetcher.py`, `social-network-analysis.py`,
`theme-analysis.py`, and `utils/`) are **historical provenance only** —
they document the original thesis behavior but are not executed by the
production pipeline. All production behavior is re-implemented in `src/`.

The `src/` package layout:

| Module | Purpose |
|---|---|
| `src/cli.py` | CLI entry point for all pipeline commands |
| `src/config/` | Configuration loading, validation, and settings |
| `src/graph_store/` | `GraphRepository` abstraction; Memgraph implementation |
| `src/ingestion/` | Network data extractor, schema constants, Memgraph loader |
| `src/network/` | Follower-followee edges, graph construction, centrality |
| `src/communities/` | Louvain detection, message extraction, similarity |
| `src/topics/` | Text preprocessing, LDA, topic inputs, topic matching |
| `src/themes/` | Theme generation, clustering, TEI embedding, transition, paths, heatmaps |
| `src/text/` | Multilingual translation pipeline (Azure/AWS provider abstraction) |
| `src/providers/` | LLM provider abstraction (OpenAI, Gemini, Mistral, LLM7, Nvidia, mock) |
| `src/orchestration/` | Prefect flows, tasks, stage cache, run hashing |
| `src/artifacts/` | Run manifest lifecycle models |
| `src/api/` | FastAPI read-only artifact API |
| `src/reporting/` | Output artifact contract validator, artifact index |
| `src/tracking/` | MLflow experiment tracking (optional) |
| `src/visualization/` | Sankey, membership-change, and theme-similarity charts |
| `src/preflight.py` | Pre-run dependency/credential/TEI preflight checks |
| `src/logging_config.py` | Structured logging (text/JSON) |

The `frontend/` directory contains the Vite/React read-only dashboard that
consumes the FastAPI `/api/v1` endpoints exclusively.

## Mission

The thesis scripts have been turned into a production-ready, reproducible,
locally runnable project. All original thesis analytical behavior is preserved.

The system supports:

- Neo4j export migration path into a local graph database workflow.
- Telegram and Twitter-style relationship datasets.
- Follower-followee graph construction.
- Absolute and weighted interaction metrics.
- NetworkX graph generation.
- Louvain community detection.
- Prominent community filtering.
- In-degree/out-degree centrality summaries.
- User/message count summaries.
- Daily community message statistics.
- Exact and partial community matching.
- Unigram and bigram LDA topic modeling.
- Matched and partially matched community topic comparison.
- GPT-assisted theme generation from LDA keywords.
- Month-to-month community transition analysis.
- Sankey community transition visualization.
- Membership-change visualization.
- SentenceTransformer/TEI theme similarity heatmaps.
- Monthly HDBSCAN theme clustering (Stage A, contract 3.0).
- Cross-month cosine complete-linkage canonical theme families (Stage B, contract 4.0).
- Prefect orchestration with content-addressed cross-run stage artifact cache.
- Immutable run manifests with checksum/schema/row-count verification.
- Read-only FastAPI artifact API discoverable through run manifests.
- Vite/React dashboard consuming only `/api/v1`.
- Optional MLflow experiment tracking.
- Optional multilingual translation (Azure/AWS) before LDA preprocessing.
- Pipeline preflight validation before expensive evolution runs.

## Non-Negotiable Constraints

- Preserve the existing `shared_post` and `weighted_post` metric behavior.
- Preserve graph filtering defaults unless explicitly changed in a documented experiment: `min_total_post=10`, `min_shared_post=5`.
- Preserve Louvain defaults unless explicitly changed in a documented experiment: `resolution=1`, `seed=123`.
- Preserve the approved production LdaMulticore defaults unless explicitly changed in a documented experiment: `num_topics=15`, `random_state=100`, `iterations=100`, `chunksize=20`, `passes=80`, `alpha='symmetric'`, `eta='auto'`. The `alpha` value is the documented LdaMulticore compatibility migration from the thesis-era `alpha='auto'` setting.
- Do not commit secrets or real database credentials.
- Do not hard-code local absolute paths such as external drive paths.
- Do not remove Telegram support while making Twitter/reply workflows configurable.
- Do not replace thesis outputs with only LLM-generated themes. GPT themes are downstream of LDA keywords.
- Do not call OpenAI APIs in tests.
- Do not run any destructive git commands (e.g., `git reset --hard`, `git clean -f`, `git restore`, `git checkout --`, `git push --force`, `git branch -D`, or any command that discards uncommitted work or git history).
- Do not change `shared_post`, `weighted_post`, graph thresholds, Louvain defaults, LDA defaults, monthly Stage-A clustering contract, Stage-B canonicalization contract, output categories, public schemas, or the LDA-before-theme analytical order without an approved execution plan and behavior-preservation tests.
- The FastAPI layer must not run ingestion, NetworkX, Louvain, LDA, provider, TEI, or visualization-generation code in request paths.
- Dashboard/API handlers must not compute or persist embeddings.

## Completed Foundation

The following modernization goals from the original HARNESS have been achieved:

- Neo4j hard-coded credentials replaced by `GRAPH_DB_*` environment contract.
- All paths configurable; no hard-coded external drive paths.
- `src/` package with importable modules and `src/cli.py` CLI commands.
- Tests around all core behavior before any refactoring.
- Memgraph Community Edition as the default local graph database.
- CSV compatibility for existing Neo4j workflow exports preserved.
- Prefect orchestration with ephemeral local execution (no server required).
- Immutable run manifests with atomic lifecycle management.
- Read-only FastAPI artifact API over verified manifests.
- Read-only Vite/React dashboard consuming only `/api/v1`.
- Monthly HDBSCAN theme clustering + cross-month cosine canonicalization.
- Content-addressed cross-run stage artifact cache (network, topic, theme stages).
- Optional MLflow tracking for prompt/schema versions and provider metrics.
- Optional multilingual translation pipeline (Azure default, AWS optional).
- Pipeline preflight for real evolution runs.
- TEI embedding service infrastructure (two revision-pinned profiles).

## Current Development Direction

New work continues in `docs/exec-plans/active/` with plan numbers 030+.
Before starting any new task:

1. Read the relevant active execution plan.
2. Inspect current source before editing.
3. Preserve behavior with tests or fixture outputs.
4. Make the smallest coherent change.
5. Run relevant validation.
6. Update the active execution plan progress log.
7. Update docs if behavior, commands, schemas, or assumptions change.

## Validation Commands

Use these commands when available:

```bash
# Core quality
make format
make lint
make test

# Database (optional — requires Docker)
make db-up
make db-check

# TEI embedding services (optional — requires Docker + GPU)
make tei-up
make tei-check
make tei-down

# Offline sample pipeline
make ingest-sample
make run-network-sample
make run-topic-sample
make run-theme-sample
make run-pipeline-sample
make build-report

# Evolution pipeline
make run-evolution-pipeline-test
make verify-output-contract
make verify-evolution-output-contract
make pipeline-preflight CONFIG=configs/twitter/reply_evolution.yml
make run-evolution-pipeline CONFIG=configs/twitter/reply_evolution.yml

# Translation planning (cloud-free)
make translation-preflight CONFIG=configs/telegram/forwarded_message_evolution.yml
make translation-detect CONFIG=configs/telegram/forwarded_message_evolution.yml

# Theme clustering benchmarks (read-only, no production change)
make canonical-theme-benchmark THEMES_DIR=<path>
make monthly-theme-cluster-benchmark THEMES_DIR=<path>

# API and dashboard
make api-smoke-test
make run-api API_ARTIFACT_ROOT=<path>
make dashboard-fixture
make run-frontend

# Frontend quality
make frontend-install
make frontend-build
make frontend-lint
make frontend-typecheck
make frontend-test
make frontend-coverage
make frontend-e2e
make frontend-check

# Full demo
make demo
```

If a Make target does not exist yet, create it in the relevant execution plan.

## Escalate Before

Ask the human before:

- Changing thesis metric definitions.
- Removing any existing output category.
- Changing algorithm defaults.
- Replacing Memgraph with a different database.
- Introducing paid cloud dependencies.
- Making OpenAI/GPT calls mandatory for the full local sample pipeline.
- Changing the Stage-A monthly clustering contract version.
- Changing the Stage-B canonicalization contract version.
- Changing TEI model IDs or Hugging Face revision pins.
- Running any destructive git operations or commands that could overwrite or discard git history or working tree state.
