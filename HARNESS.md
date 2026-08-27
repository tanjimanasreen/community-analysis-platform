# Thesis Project Harness

This harness reflects the production rebuild of the thesis codebase and guides
ongoing development. The original thesis scripts (`neo4j_data_fetcher.py`,
`social-network-analysis.py`, `theme-analysis.py`, and `utils/`) are
historical provenance. All production behavior is implemented in the `src/`
Python package.

## Harness Principles

1. Preserve thesis behavior before refactoring.
2. Make hard-coded script assumptions configurable.
3. Treat repository docs as the source of truth.
4. Treat execution plans as first-class implementation artifacts.
5. Keep validation mechanical through tests, fixtures, and CLI commands.

## File Map

### Core Contracts and Design Docs

| File | Purpose |
|---|---|
| `AGENTS.md` | Agent entry point, production state summary, and non-negotiable constraints. |
| `ARCHITECTURE.md` | Actual production architecture and module structure. |
| `docs/design-docs/current-code-feature-inventory.md` | Complete inventory of all implemented features (thesis + production additions). |
| `docs/product-specs/project-spec.md` | Product requirements based on the current codebase. |
| `docs/design-docs/data-contract.md` | Raw graph and derived interaction data shapes. |
| `docs/design-docs/database-contract.md` | `GraphRepository` pattern; Memgraph default; `GRAPH_DB_*` env contract. |
| `docs/design-docs/metric-contract.md` | Exact metric, threshold, algorithm, and output contracts. |
| `docs/design-docs/pipeline-contract.md` | End-to-end pipeline stages: ingestion → network → topic → theme → evolution. |
| `docs/design-docs/theme-intelligence-contract.md` | GPT theme, TEI embedding, clustering, transition, mobility, and similarity contracts. |
| `docs/design-docs/output-artifact-contract.md` | Frozen public/internal artifact schemas and Parquet path contracts. |
| `docs/verification/quality-gates.md` | Required validation gates for each development milestone. |
| `docs/verification/test-matrix.md` | Tests required by module and feature. |
| `docs/exec-plans/tech-debt-tracker.md` | Known cleanup and migration debt. |

### Key Execution Plans

| File | Status | Purpose |
|---|---|---|
| `docs/exec-plans/active/001-baseline-and-foundation.md` | active (foundational, milestones complete) | Captured defaults, built project foundation, fixture data. |
| `docs/exec-plans/active/002-database-and-ingestion.md` | milestones complete | GraphRepository abstraction, Memgraph implementation, ingestion pipeline. |
| `docs/exec-plans/active/003-network-community-topic-pipeline.md` | complete | Social network and LDA pipeline productionized. |
| `docs/exec-plans/active/004-theme-intelligence.md` | complete | Theme generation, transitions, Sankey, membership-change, heatmaps. |
| `docs/exec-plans/active/005-offline-sample-hardening.md` | complete | Offline sample commands with no database or OpenAI requirement. |
| `docs/exec-plans/active/010-output-contract-freeze-report-readiness.md` | complete | Parquet artifact contract and output verifier. |
| `docs/exec-plans/active/011-read-only-backend-api.md` | complete | FastAPI read-only artifact API over verified manifests. |
| `docs/exec-plans/active/012-frontend-dashboard-integration.md` | complete | Vite/React dashboard consuming `/api/v1` only. |
| `docs/exec-plans/active/019-prefect-orchestration-and-operational-lineage.md` | milestones complete | Prefect orchestration, run manifests, stage artifact cache. |
| `docs/exec-plans/active/039-production-theme-clustering-and-canonicalization.md` | implemented | HDBSCAN monthly Stage-A + AgglomerativeClustering Stage-B canonicalization. |
| `docs/exec-plans/active/075-cached-multilingual-translation.md` | implemented | Optional translation pipeline before LDA (Azure/AWS). |
| `docs/exec-plans/active/087-production-stage-a-theme-clustering-robustness-promotion.md` | implemented; production revalidation pending | Monthly clustering contract 3.0 (unit-Euclidean/leaf HDBSCAN). |

New work continues in plans numbered 030+. See `docs/exec-plans/active/` for the
full list. Any plan with `Status: complete` or `Status: implemented` describes
already-delivered behavior.

## Production Pipeline Flow

The production entry point is `src/cli.py`. The canonical pipeline sequence:

```text
src/cli.py run-evolution-pipeline --config configs/...
  → pipeline-preflight (dependency/credential/TEI validation)
  → src/orchestration/ (Prefect flow: composition_flow.py / tasks.py)
      → ingest-interactions (src/pipelines/ingestion_pipeline.py)
          → src/ingestion/ (network_data_extractor, schema)
          → src/graph_store/ (MemgraphRepository or --no-db)
      → run-social-network (src/pipelines/social_network_pipeline.py)
          → src/network/ (follower_followee, graphs, centrality)
          → src/communities/ (louvain, messages, similarity)
          → src/topics/ (text_preprocessor, lda, topic_inputs, topic_matching)
      → run-theme-analysis (src/pipelines/theme_pipeline.py)
          → src/themes/ (theme_generation, theme_clustering, community_paths,
                         community_transition, embedding_store, tei_client,
                         theme_similarity, membership_changes, heatmaps)
          → src/providers/ (LLM provider abstraction)
          → src/text/ (translation — optional)
      → src/artifacts/ (run manifest lifecycle)
      → src/reporting/ (output_contract verifier)
      → src/tracking/ (MLflow — optional)

Read-only consumers:
  FastAPI (src/api/) → discovers runs/*/manifest.json → serves verified artifacts
  Dashboard (frontend/) → calls /api/v1 only → never mutates artifacts
```

The original thesis script sequence (for provenance):

```text
[historical — not executed by production]
neo4j_data_fetcher.py → exported relationship CSV
social-network-analysis.py → network/community/LDA CSV outputs
theme-analysis.py → GPT themes, transitions, diagrams, similarity heatmaps
```

## Offline Sample Commands

The offline sample pipeline runs without Docker, database, OpenAI, model
downloads, or Kaleido:

```bash
make install-dev          # install .venv with all extras
make test                 # full unit test suite
make validate-config      # validate offline sample config
make ingest-sample        # derive interaction parquet from fixture CSV
make run-network-sample   # network/community/LDA from fixture
make run-topic-sample     # topic stage from saved network outputs
make run-theme-sample     # theme stage with offline mock provider
make run-pipeline-sample  # full offline pipeline + report
make build-report         # markdown artifact index
make verify-output-contract  # validate generated artifact schemas
```

## Acceptance Criteria

The harness is satisfied when:

- [x] The current code features are documented in `current-code-feature-inventory.md`.
- [x] The production pipeline can run on a small sample dataset without hard-coded local paths.
- [x] Existing metrics and thresholds are tested.
- [x] Thesis-aligned LDA behavior and outputs are preserved, with the approved production `LdaMulticore` prior contract (`alpha="symmetric"`, `eta="auto"`) documented and tested.
- [x] Theme generation is optional and can be skipped in offline tests.
- [x] Month-to-month transition, membership-change, and theme similarity outputs are covered.
- [x] General-theme semantic clustering is an additive upstream artifact stage: raw GPT/LDA evidence is preserved, tests inject embeddings, and dashboard/API requests never run TEI or HDBSCAN.
- [x] Clustering uses first-party `sklearn.cluster.HDBSCAN`; unique TEI vectors from both semantic profiles are persisted as content-addressed float32 Parquet run artifacts when produced, while duplicate theme observations remain in the clustering population.
- [x] Local semantic infrastructure can run both revision-pinned TEI profiles through one `make tei-up` command.
- [x] Real longitudinal runs have a mandatory `pipeline-preflight` dependency that fails before expensive work on stale dependencies, missing inputs/credentials, or required TEI failures.
- [x] All generated output categories from the current scripts have documented target locations.
- [x] Orchestrated outputs are isolated in immutable `runs/<run_id>/` bundles with atomic lifecycle management.
- [x] Cross-run stage artifact cache is content-addressed from input/config/code/runtime fingerprints — not from run IDs.
- [x] The FastAPI read-only API discovers runs through manifest files only and never executes analysis code.
- [x] The Vite/React dashboard consumes only `/api/v1` and never mutates output files.
- [x] Monthly Stage-A HDBSCAN clustering uses unit-Euclidean/leaf geometry (contract 3.0) with explicit provenance.
- [x] Stage-B canonicalization uses normalized-representative cosine complete-linkage at similarity 0.65 (contract 4.0).
