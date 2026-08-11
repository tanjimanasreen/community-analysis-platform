# Thesis Project Harness

This harness reflects the existing thesis codebase and guides its production rebuild.

The previous generic harness is replaced by this project-specific one. It covers the actual implemented features in `neo4j_data_fetcher.py`, `social-network-analysis.py`, `theme-analysis.py`, and `utils/`.

## Harness Principles

1. Preserve thesis behavior before refactoring.
2. Make hard-coded script assumptions configurable.
3. Treat repository docs as the source of truth.
4. Treat execution plans as first-class implementation artifacts.
5. Keep validation mechanical through tests, fixtures, and CLI commands.

## File Map

| File | Purpose |
|---|---|
| `AGENTS.md` | Agent entry point and non-negotiable constraints. |
| `ARCHITECTURE.md` | Target architecture mapped to the current scripts. |
| `docs/design-docs/current-code-feature-inventory.md` | Complete inventory of implemented thesis features. |
| `docs/product-specs/project-spec.md` | Product requirements based on the current codebase. |
| `docs/design-docs/data-contract.md` | Current and target data shapes. |
| `docs/design-docs/database-contract.md` | Neo4j export behavior and Memgraph migration target. |
| `docs/design-docs/metric-contract.md` | Exact metric, threshold, algorithm, and output contracts. |
| `docs/design-docs/pipeline-contract.md` | End-to-end pipeline stages from database export to theme analysis. |
| `docs/design-docs/theme-intelligence-contract.md` | GPT theme, transition, membership-change, and similarity features. |
| `docs/verification/quality-gates.md` | Required validation gates. |
| `docs/verification/test-matrix.md` | Tests required by module and feature. |
| `docs/exec-plans/active/001-baseline-and-foundation.md` | Preserve current behavior and build project foundation. |
| `docs/exec-plans/active/002-database-and-ingestion.md` | Configurable Neo4j/Memgraph ingestion and graph store layer. |
| `docs/exec-plans/active/003-network-community-topic-pipeline.md` | Productionize social network and LDA pipeline. |
| `docs/exec-plans/active/004-theme-intelligence.md` | Productionize theme generation, transition, and similarity analysis. |
| `docs/exec-plans/tech-debt-tracker.md` | Known cleanup and migration debt. |

## Existing Script Flow

The current project runs in three broad phases:

1. `neo4j_data_fetcher.py`
   - Connects to Neo4j.
   - Runs a date-bounded query for Telegram or Twitter relationships.
   - Exports `source`, `target`, and `relation` rows to CSV.

2. `social-network-analysis.py`
   - Loads the exported CSV.
   - Splits creator/spreader relationships.
   - Builds user and network dataframes.
   - Builds follower-followee edges with `shared_post` and `weighted_post`.
   - Builds absolute and weighted NetworkX graphs.
   - Runs Louvain community detection.
   - Filters prominent communities.
   - Extracts community messages.
   - Computes centrality, user/message counts, and daily message stats.
   - Compares absolute and weighted communities.
   - Runs unigram and bigram LDA.
   - Exports topic comparisons for matched and partially matched communities.

3. `theme-analysis.py`
   - Loads monthly matched LDA outputs.
   - Combines absolute/weighted unigram and bigram keywords.
   - Generates GPT theme labels.
   - Compares communities across consecutive months using Jaccard similarity.
   - Draws Sankey transition diagrams.
   - Finds all Sankey paths.
   - Draws membership-change diagrams.
   - Computes theme text similarity with SentenceTransformer.
   - Draws absolute, weighted, and general theme similarity heatmaps.

## Modernization Goal

The production rebuild should keep the same analytical outputs but make them:

- Configurable.
- Testable.
- Locally runnable.
- Reproducible.
- Easier to inspect.
- Safer with secrets.
- Easier for an agent to continue improving.

## Required Development Order

1. Baseline and foundation.
2. Database and ingestion.
3. Network/community/topic pipeline.
4. Theme intelligence.
5. Reporting/API/automation only after core behavior is preserved.

## Acceptance Criteria

The harness is satisfied when:

- The current code features are documented in `current-code-feature-inventory.md`.
- The production pipeline can run on a small sample dataset without hard-coded local paths.
- Existing metrics and thresholds are tested.
- Thesis-aligned LDA behavior and outputs are preserved, with the approved production `LdaMulticore` prior contract (`alpha="symmetric"`, `eta="auto"`) documented and tested.
- Theme generation is optional and can be skipped in offline tests.
- Month-to-month transition, membership-change, and theme similarity outputs are covered.
- General-theme semantic clustering is an additive upstream artifact stage: raw GPT/LDA evidence is preserved, tests inject embeddings, and dashboard/API requests never run TEI or HDBSCAN.
- Clustering uses first-party `sklearn.cluster.HDBSCAN`; unique TEI vectors from both semantic profiles are persisted as content-addressed float32 Parquet run artifacts when produced, while duplicate theme observations remain in the clustering population.
- Local semantic infrastructure can run both revision-pinned TEI profiles through one `make tei-up` command.
- Real longitudinal runs have a mandatory `pipeline-preflight` dependency that fails before expensive work on stale dependencies, missing inputs/credentials, or required TEI failures.
- All generated output categories from the current scripts have documented target locations.
