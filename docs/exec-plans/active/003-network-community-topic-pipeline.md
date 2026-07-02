# Execution Plan: Network, Community, And Topic Pipeline

Status: complete

Owner: agent

Last updated: 2026-07-01

## Goal

Productionize the current `social-network-analysis.py` pipeline while preserving its metrics, graph construction, community detection, comparison, LDA, and output categories.

## Context

Read first:

- `social-network-analysis.py`
- `utils/network_graph.py`
- `utils/community_generator.py`
- `utils/similarity_detector.py`
- `utils/text_preprocessor.py`
- `utils/lda_analysis.py`
- `docs/design-docs/metric-contract.md`
- `docs/design-docs/pipeline-contract.md`

## Non-Goals

- Do not implement GPT theme generation in this plan.
- Do not change graph thresholds or LDA defaults.

## Files Expected To Change

- `src/network/follower_followee.py`
- `src/network/graphs.py`
- `src/network/centrality.py`
- `src/communities/louvain.py`
- `src/communities/messages.py`
- `src/communities/similarity.py`
- `src/topics/text_preprocessor.py`
- `src/topics/lda.py`
- `src/topics/topic_matching.py`
- `src/pipelines/social_network_pipeline.py`
- related tests

## Milestone 1: Network Metrics And Graphs

Tasks:

- [x] Port `shared_post`, `total_post`, and `weighted_post` logic.
- [x] Preserve self-spread exclusion.
- [x] Preserve graph thresholds.
- [x] Build absolute and weighted `MultiDiGraph` outputs.

Validation:

```bash
pytest tests/unit/test_follower_followee_metrics.py
pytest tests/unit/test_graph_thresholds.py
```

## Milestone 2: Communities And Statistics

Tasks:

- [x] Port Louvain detection with existing defaults.
- [x] Port prominent community filtering.
- [x] Port community message extraction.
- [x] Port centrality summaries.
- [x] Port user/message counts.
- [x] Port daily message statistics.

Validation:

```bash
pytest tests/unit/test_louvain_defaults.py
pytest tests/unit/test_community_messages.py
pytest tests/unit/test_community_stats.py
```

## Milestone 3: Community Matching

Tasks:

- [x] Port exact absolute/weighted matching.
- [x] Port partial matching.
- [x] Port unmatched community outputs.
- [x] Preserve Jaccard score behavior.

Validation:

```bash
pytest tests/unit/test_community_similarity.py
```

## Milestone 4: LDA Topic Modeling

Tasks:

- [x] Port text preprocessing.
- [x] Port unigram LDA.
- [x] Port bigram/trigram LDA.
- [x] Port LDA score output.
- [x] Port matched and partially matched topic comparison.
- [x] Preserve KneeLocator keyword cutoff.

Validation:

```bash
pytest tests/unit/test_text_preprocessor.py
pytest tests/unit/test_lda_contract.py
make run-topic-sample
```

## Acceptance Criteria

- [x] Sample relationship CSV runs through network/community/topic outputs.
- [x] Existing output categories from `social-network-analysis.py` are preserved.
- [x] Metrics, thresholds, Louvain defaults, and LDA defaults are tested.
- [x] No OpenAI dependency is introduced in this pipeline.

## Progress Log

| Date | Update |
|---|---|
| 2026-06-23 | Created plan from inspected thesis code. |
| 2026-07-01 | Started Milestone 1: graph construction now accepts configurable thresholds while preserving defaults `min_total_post=10` and `min_shared_post=5`; social network pipeline imports topic/LDA modules lazily so network-only imports do not require spaCy/gensim/model downloads. |
| 2026-07-01 | Validated the Plan 003 network/community subset in the project `.venv`: `test_current_defaults.py`, `test_follower_followee_metrics.py`, `test_graph_thresholds.py`, `test_louvain_defaults.py`, `test_community_messages.py`, `test_community_similarity.py`, and `test_pipelines.py` passed with 20 tests. A broader unit run excluding `test_gpt_themes.py` passed 45 tests and had one out-of-scope Plan 004 heatmap failure caused by offline SentenceTransformer model loading. |
| 2026-07-01 | Completed Plan 003: added missing community centrality/stat tests, hardened daily message date parsing for Neo4j tuple strings and ISO timestamps, made LDA importable offline by removing undeclared `nltk` usage and lazily loading spaCy with an offline blank-English fallback, preserved all LDA defaults, forced `c_v` coherence to `processes=1` for local sample stability, and added LDA/default/topic matching tests. Validation: Plan 003 focused suite passed 31 tests; broader non-theme unit suite passed 52 tests; sample relationship fixture ran through network, community, and LDA outputs successfully. |
