# Quality Gates

Work is complete only when the relevant gates pass.

## Gate 1: Baseline Preservation

Required:

- Current scripts are inventoried.
- Existing output categories are documented.
- A small fixture or sample run is available.
- Current hard-coded parameters are captured in config defaults.

Validation:

```bash
pytest tests/unit/test_current_defaults.py
```

## Gate 2: Configuration And Secrets

Required:

- No database credentials are hard-coded.
- No OpenAI API key is hard-coded.
- `.env.example` exists.
- Dataset run config supports Twitter and Telegram parameters.
- External drive paths are replaced by configurable paths.

Validation:

```bash
python -m src.cli validate-config --config configs/sample.yml
```

## Gate 3: Database Export Compatibility

Required:

- Existing `source,target,relation` CSV format is supported.
- Neo4j export can be configured without editing source.
- Memgraph local runtime exists.
- Graph store access is isolated.

Validation:

```bash
make db-up
make db-check
pytest tests/integration/test_graph_export_contract.py
```

## Gate 4: Network Metrics

Required:

- `shared_post` calculation is tested.
- `weighted_post = shared_post / total_post` is tested.
- Self-spread exclusion is tested.
- Graph filtering thresholds are tested.

Validation:

```bash
pytest tests/unit/test_follower_followee_metrics.py
pytest tests/unit/test_graph_thresholds.py
```

## Gate 5: Community Analysis

Required:

- Louvain defaults are preserved.
- Prominent community filtering is tested.
- Community message extraction is tested.
- Exact and partial community matching are tested.

Validation:

```bash
pytest tests/unit/test_louvain_defaults.py
pytest tests/unit/test_community_similarity.py
```

## Gate 6: LDA Topic Modeling

Required:

- Text preprocessing behavior is tested.
- LDA defaults are preserved.
- Unigram and bigram outputs are generated.
- Matched and partially matched topic comparison outputs are generated.
- Perplexity and coherence scores are saved.

Validation:

```bash
pytest tests/unit/test_text_preprocessor.py
pytest tests/unit/test_lda_contract.py
make run-topic-sample
```

## Gate 7: Theme Intelligence

Required:

- GPT theme generation is behind a provider interface.
- Theme generation supports mock/cached mode.
- Month-to-month transition uses correct thresholds.
- Sankey path detection is tested.
- Membership-change calculation is tested.
- Theme similarity matrix generation is tested.

Validation:

```bash
pytest tests/unit/test_theme_generation_contract.py
pytest tests/unit/test_community_transition.py
pytest tests/unit/test_membership_changes.py
pytest tests/unit/test_theme_similarity.py
make run-theme-sample
```

## Gate 8: End-To-End Sample

Required:

- Sample network pipeline runs.
- Sample topic pipeline runs.
- Sample theme pipeline runs in offline/mock mode.
- Final report or output index lists all generated artifacts.

Validation:

```bash
make run-pipeline-sample
make test
```
