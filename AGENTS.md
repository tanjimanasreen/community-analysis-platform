# AGENTS.md

This repository contains an existing thesis codebase for social network/community analysis and theme analysis. Your job is to modernize it without losing any implemented thesis behavior.

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
10. `docs/verification/quality-gates.md`
11. `docs/verification/test-matrix.md`
12. The relevant active plan in `docs/exec-plans/active/`

## Current Codebase

The existing thesis implementation is centered around:

- `neo4j_data_fetcher.py`: manually configured Neo4j query/export script.
- `social-network-analysis.py`: end-to-end network, community, LDA, and community-comparison pipeline.
- `theme-analysis.py`: GPT theme generation, month-to-month community transition analysis, Sankey diagrams, membership-change diagrams, and theme similarity heatmaps.
- `utils/network_data_extractor.py`: creator/spreader extraction, Neo4j datetime conversion, user dataframe creation, follower-followee edge construction, and `shared_post`/`weighted_post` metric calculation.
- `utils/network_graph.py`: NetworkX graph construction and centrality helpers.
- `utils/community_generator.py`: Louvain community detection, prominent community filtering, community message extraction, and community message statistics.
- `utils/similarity_detector.py`: exact and partial community matching using Jaccard similarity.
- `utils/lda_analysis.py`: unigram/bigram LDA, perplexity/coherence, dominant topic assignment, and matched-topic export.
- `utils/text_preprocessor.py`: text cleaning, emoji removal, HTML cleaning, Unicode normalization, stopword filtering.
- `utils/lang_detector.py` and `utils/lang_translator.py`: English detection and Google translation helpers.

## Mission

Turn the thesis scripts into a production-ready, reproducible, locally runnable project while preserving all implemented features.

The final system must support:

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
- SentenceTransformer theme similarity heatmaps.

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

## Default Modernization Direction

- Replace hard-coded Neo4j connectivity with configuration.
- Use Memgraph Community Edition as the default local graph database target for the production rebuild.
- Keep compatibility with exported CSV relationship files from the existing Neo4j workflow.
- Convert scripts into importable modules and CLI commands.
- Add tests around current behavior before refactoring internals.

## Development Loop

For every task:

1. Read the active execution plan.
2. Inspect current code before editing.
3. Preserve behavior with tests or fixture outputs.
4. Make the smallest coherent change.
5. Run relevant validation.
6. Update the active execution plan progress log.
7. Update docs if behavior, commands, schemas, or assumptions change.

## Validation Commands

Use these commands when available:

```bash
make format
make lint
make test
make db-up
make db-check
make ingest-sample
make run-network-sample
make run-topic-sample
make run-theme-sample
make run-pipeline-sample
make build-report
```

If a command does not exist yet, create it in the relevant execution plan.

## Escalate Before

Ask the human before:

- Changing thesis metric definitions.
- Removing any existing output category.
- Changing algorithm defaults.
- Replacing Memgraph with a different database.
- Introducing paid cloud dependencies.
- Making OpenAI/GPT calls mandatory for the full local sample pipeline.
