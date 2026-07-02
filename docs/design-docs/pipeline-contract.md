# Pipeline Contract

## Full Current Pipeline

The production rebuild must cover this full sequence:

1. Configure dataset run.
2. Export graph relationships from Neo4j/Memgraph or load an existing relationship CSV.
3. Split creator and spreader relationships.
4. Build user dataframe.
5. Build normalized network dataframe.
6. Detect or translate language where configured.
7. Build follower-followee edges.
8. Build absolute and weighted NetworkX graphs.
9. Run Louvain community detection.
10. Filter prominent communities.
11. Extract community edge and message details.
12. Compute centrality summaries.
13. Compute user/message count summaries.
14. Compute daily message statistics.
15. Compare absolute and weighted communities.
16. Preprocess community text.
17. Run unigram LDA.
18. Run bigram/trigram LDA.
19. Save LDA scores.
20. Export matched and partially matched LDA topic comparisons.
21. Load monthly matched LDA outputs.
22. Generate GPT themes from keywords.
23. Compare communities across consecutive months.
24. Build Sankey transition data.
25. Render Sankey transition diagrams.
26. Extract community transition paths.
27. Render membership-change diagrams.
28. Compute theme sentence similarity.
29. Render theme similarity heatmaps.

## Pipeline Commands

Target commands:

```bash
python -m src.cli export-graph --config configs/<run>.yml
python -m src.cli run-social-network --config configs/<run>.yml
python -m src.cli run-topics --config configs/<run>.yml
python -m src.cli run-theme-analysis --config configs/<run>.yml
python -m src.cli run-all --config configs/<run>.yml
```

Make targets:

```bash
make db-up
make db-check
make ingest-sample
make run-network-sample
make run-topic-sample
make run-theme-sample
make run-pipeline-sample
make build-report
make test
```

## Run Configuration

Every run should be configurable with:

- `data_type`
- `content_type`
- `month`
- `year`
- `input_path`
- `output_base_path`
- `creator_relation`
- `spreader_relation`
- `creator_node_column`
- `spreader_node_column`
- `text_node_column`
- `date_column`
- `min_total_post`
- `min_shared_post`
- `min_members`
- `lda.num_topics`
- `lda.top_n_keywords`
- `theme.enable_gpt`
- `theme.model`
- `theme.sleep_seconds`
- `theme.transition_threshold`

## Output Preservation

The production pipeline must preserve the output categories listed in `docs/design-docs/current-code-feature-inventory.md`.

If output paths are modernized, provide compatibility aliases or documented migration mapping.

## Offline And Online Modes

Offline mode:

- Runs export from existing CSV.
- Runs network, community, and LDA stages.
- Uses cached or mocked theme responses.
- Does not call OpenAI.

Online mode:

- May connect to database.
- May call OpenAI for GPT theme generation if `OPENAI_API_KEY` is configured.

## Failure Behavior

- Fail fast on missing config.
- Fail fast on missing required columns.
- Never delete raw input files.
- Do not overwrite previous run outputs unless explicitly configured.
- GPT failures should not destroy LDA outputs.
- Visualization failures should be reported separately from analysis failures.

