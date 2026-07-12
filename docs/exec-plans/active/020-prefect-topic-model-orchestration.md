# Plan 020: Prefect Milestone 2B - Topic-Model Execution and Lineage

## 1. Goal
Design an implementation-ready architecture to introduce Prefect orchestration and operational lineage to the topic modeling phase. This includes wrapping the existing topic domain function in a coarse task, establishing explicit caching behavior, ensuring explicit typed output references, and isolated run artifacts, without breaking the existing pipeline or introducing Prefect imports into domain code.

## 2. Current-state Findings
- The core topic execution is performed by `run_topic_phase` inside `src/pipelines/social_network_pipeline.py`.
- It is wrapped by `run_topic_phase_from_saved_inputs` which reads saved topic inputs from `_intermediate/topic_inputs/...` generated in Milestone 2A.
- The topic execution is deterministic and local. No external API is involved.
- `make test` acts as a regression gate and the repo is currently clean.

## 3. Exact Domain Function to Wrap
- **Name**: `run_topic_phase`
- **Signature**:
  ```python
  def run_topic_phase(
      abs_community_messages: pd.DataFrame, 
      per_community_messages: pd.DataFrame,
      matched_df: pd.DataFrame,
      partial_matched: pd.DataFrame,
      month: str,
      year: str,
      data_type: str,
      content_type: str,
      output_dir: str
  ):
  ```
- **Inputs**: DataFrames of absolute and weighted community messages, matched communities, and partially matched communities.
- **Outputs**: Writes LDA scores, matched communities and their topics, and partially matched communities and their topics CSVs, and saves theme inputs to an intermediate directory.
- **Returns**: `df_lda_scores` DataFrame.

## 4. Current Call Graph
- `src/cli.py` -> `run_full_pipeline` -> `run_topic_phase_from_saved_inputs` -> `load_topic_inputs`
- `run_topic_phase_from_saved_inputs` -> `run_topic_phase`
- `run_topic_phase` -> `message_preprocess`, `get_unigram_lda`, `get_bigram_lda`, `get_matched_topic_df`, `save_pipeline_theme_inputs`

## 5. Proposed Task Boundary
We will create a coarse Prefect task `run_monthly_topic_phase_task` that wraps `run_topic_phase`. The task will receive a validated `TopicInputBundle` containing explicit `ArtifactReference` instances instead of arbitrary previous output directories. The task will prepare the inputs (load the dataframes) and call the domain function. The task will return a `TopicOutputBundle`.

## 6. Typed Input Contract
```python
@dataclass(frozen=True)
class TopicInputBundle:
    absolute_community_messages: ArtifactReference
    weighted_community_messages: ArtifactReference
    matched_communities: ArtifactReference
    partial_matched_communities: ArtifactReference | None
```
- **absolute_community_messages**: `_intermediate/topic_inputs/.../absolute_community_messages.csv`, Required, CSV, Hash required, Stage 2A.
- **weighted_community_messages**: `_intermediate/topic_inputs/.../weighted_community_messages.csv`, Required, CSV, Hash required, Stage 2A.
- **matched_communities**: `_intermediate/topic_inputs/.../matched_communities.csv`, Required, CSV, Hash required, Stage 2A.
- **partial_matched_communities**: `_intermediate/topic_inputs/.../partial_matched_communities.csv`, Optional, CSV, Stage 2A.

## 7. Typed Output Contract
```python
@dataclass(frozen=True)
class TopicOutputBundle:
    lda_scores: ArtifactReference
    matched_communities_topics: ArtifactReference | None
    partial_matched_communities_topics: ArtifactReference | None
    theme_inputs: tuple[ArtifactReference, ...]
```
Only durable output references cross Prefect boundaries. The returned dataframe from `run_topic_phase` will be logged/manifested as metadata or converted to an artifact reference but not persisted natively as a Prefect Result object containing large dataframes.

## 8. Artifact Inventory
**Inputs:**
- absolute_community_messages.csv
- weighted_community_messages.csv
- matched_communities.csv
- partial_matched_communities.csv

**Outputs:**
- `LDA/scores/{month}.csv` (Required)
- `LDA/matched/{month}_{year}.csv` (Optional, if matched communities exist)
- `LDA/partial_matched/{month}_{year}.csv` (Optional, if partially matched communities exist)
- `_intermediate/theme_inputs/...` (Theme input bundle references)

## 9. Output-isolation Strategy
The topic outputs will be written under the `pipeline_run_id` specific directory: `<parent_output_root>/<pipeline_run_id>/...`.
Artifact discovery within the task will rely on paths returned by the domain function or explicit expected-output contracts (checking for file existence post-execution in the stage directory), rather than unrestricted recursive scans.

## 10. Retry Policy
- `retries=0`
- The topic execution is local and deterministic. Failures due to schema errors, missing inputs, configuration errors, or execution errors will fail immediately and explicitly without retries.

## 11. Cache Policy
- Option B: **Deferred**.
- We will implement and test the deterministic `topic_cache_key_fn` helper, but leave task caching disabled (`cache_key_fn=None` initially).
- Caching will only be enabled after we introduce robust external-file existence and hash validation on cache hits.
- The cache key includes: topic-input artifact hashes, preprocessing config, LDA parameters (topics, passes, iterations, random seed), matching thresholds, semantic task implementation version.
- Excludes: Theme provider settings, overall pipeline non-topic configs.

## 12. Result-persistence Policy
- `persist_result=True` will be used to store only small typed output bundles (the `TopicOutputBundle`) inside `.prefect_results/`.
- No dataframes, raw corpus, dictionaries, models, or tokens will be stored as results.

## 13. Manifest and Lineage Changes
Additively extend the existing manifest generation to record the topic phase lineage:
- Stage name and status.
- Topic config digest and LDA hyperparameters.
- Topic-input artifact identities (DVC or explicit hashes).
- Topic-output artifact references.
- Semantic task version and failure summary.
- Start and completion timestamps.

## 14. Flow Integration
- Preferred Design: Create a composition flow `run_monthly_analysis_flow(...)` that coordinates `network_community_task` -> `topic_model_task`. This keeps the existing `run_network_community_pipeline` boundaries clear.

## 15. Optional-stage Dependency Rules
- **Run network + topics**: The topic input bundle is piped from the current network execution's outputs.
- **Run topics only**: The caller supplies a validated `TopicInputBundle`. The task rejects execution if the bundle is missing or invalid.
- **Run network only**: The topic task is skipped entirely.

## 16. Exact Files Expected to Change
- `src/orchestration/tasks/topic_tasks.py` (new)
- `src/orchestration/flows/composition_flow.py` (new or updated)
- `src/orchestration/models.py` (extend schemas)
- `src/orchestration/manifest.py` (extend manifest logic)
- `tests/unit/test_orchestration_topic_tasks.py` (new)

## 17. Tests
- **Domain regression**: `run_topic_phase` is unmodified.
- **Wrapper delegation**: Prefect task passes parameters exactly, isolates output.
- **Input validation**: Missing or mismatched hashes fail explicitly.
- **Output references**: Outputs generated are properly bundled.
- **Cache-key tests**: Validate deterministic keys and invalidations.
- **Flow tests**: Target flow using `prefect_test_harness()` with offline fixtures.

## 18. Manual Smoke Test
- Run `run_monthly_analysis_flow` orchestrator with a temporary `PREFECT_HOME` and temporary result storage, utilizing tiny topic input fixtures.
- Assert generation of valid topic artifacts without calling external processes or live DBs.

## 19. Acceptance Criteria
- Exact existing topic function is wrapped.
- Topic domain code remains Prefect-independent.
- Topic inputs are explicit references.
- Topic outputs are typed references.
- No large model or data object enters Prefect state.
- Topic retries are zero.
- Cache behavior is explicit and safe (Deferred).
- Run manifest records topic lineage.
- Offline targeted tests pass.
- Full `make test` passes.
- Fresh isolated smoke test passes.
- No theme/provider implementation is included in this phase.
- Working tree is clean after a focused commit.

## 20. Risks
- **Risk**: Returning `matched_df` from `run_topic_phase` may inadvertently leak into Prefect state if not properly isolated.
  - **Mitigation**: The task wrapper explicitly constructs `TopicOutputBundle` from disk paths and ignores the returned dataframe.
- **Risk**: Cache keys colliding if semantic task changes are unversioned.
  - **Mitigation**: Enforce semantic versioning in `topic_cache_key_fn`.

## 21. Rollback Strategy
- Remove the `src/orchestration/tasks/topic_tasks.py` and revert the flow composition if necessary. The baseline `social_network_pipeline.py` remains intact.

## 22. Deferred Work
- Prefect Assets representation.
- MLflow tracking for topics.
- Active task caching (pending existence validation logic).

## 23. Commit Boundary
- **Expected scope**: topic task wrapper, topic typed models, topic composition flow, topic cache-key helpers, topic manifest changes, topic tests, Plan 020 progress update.

## 24. Decision Log
- **Task caching deferred**: Because checking output existence outside of Prefect's state database requires a robust validation hook, which is not yet present.
- **Composition Flow**: Rather than altering `run_network_community_pipeline`, a parent flow will orchestrate the phases to adhere to separation of concerns.

## 25. Progress Log
- YYYY-MM-DD: Created Plan 020.

## 26. Official Prefect Documentation References
- Task caching: https://docs.prefect.io/3.0/develop/caching
- Testing: https://docs.prefect.io/3.0/develop/testing
- Results: https://docs.prefect.io/3.0/develop/results
