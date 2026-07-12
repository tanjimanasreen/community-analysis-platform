# Plan 019: Prefect Orchestration and Operational Lineage

## 1. Goal
Design an implementation-ready architecture to introduce Prefect orchestration and operational lineage to the existing thesis pipeline. This includes establishing task boundaries, explicit retries, precise caching, result persistence limits, a defined provider lifecycle, and robust run-context tracking without breaking existing domain code, benchmark operations, or unit tests.

## 2. Current-state Findings
- The repository has successfully implemented DVC versioning for raw data.
- Configurable multi-provider LLM routing and benchmarking exist.
- Provider fallback semantics and compatibility cleanups are complete.
- `make test` is green and acts as a strict regression gate.
- Pipeline entry points (`social_network_pipeline.py`, `theme_pipeline.py`) compose lower-level domain functions.

## 3. Current Call Graph
- `src/cli.py` -> `_run_social_pipeline_command` / `_run_theme_analysis_command`
- `_run_social_pipeline_command` -> `run_full_pipeline` or `run_network_community_pipeline`
- `run_full_pipeline` -> `run_network_phase`, `run_community_phase`, `save_pipeline_topic_inputs`, `run_topic_phase_from_saved_inputs`
- `_run_theme_analysis_command` -> `run_theme_pipeline` or `run_theme_pipeline_from_bundle` -> `run_theme_pipeline_from_monthly_data` -> `process_single_file_themes`, `get_community_transition`, `get_path_info`, `find_all_sankey_paths`, `extract_themes`, visual drawing.
- Provider lifecycle currently: Created via `build_theme_provider(config)`, wrapped in `CachedProvider`, passed into theme generation loops.

## 4. Proposed Orchestration Architecture
- Add an independent `src/orchestration/` module containing Prefect `@flow` and `@task` wrappers.
- The `src/cli.py` will have a flag (`--orchestrator prefect`) or a new command to swap from the direct runner to the Prefect flow runner.
- Introduce `PipelineRunContext` to carry run identifiers, dataset hashes (from DVC), config hashes, and metadata for future MLflow handoff.
- Domain functions remain unchanged and un-annotated, keeping them fully independent of Prefect.
- Use Prefect 3 APIs natively (`Asset`, `@materialize`, `prefect_test_harness()`).

## 5. Proposed Module Structure
```
src/orchestration/
  ├── __init__.py
  ├── flows/
  │   ├── __init__.py
  │   ├── social_network.py
  │   └── theme.py
  ├── tasks/
  │   ├── __init__.py
  │   ├── network_tasks.py
  │   ├── community_tasks.py
  │   ├── topic_tasks.py
  │   └── theme_tasks.py
  ├── context.py
  ├── cache.py
  └── assets.py
```

## 6. Flow and Task Decomposition
- **Top-level Flow**: `run_thesis_pipeline_flow`
- **Subflows**: Optional for logical separation (e.g., `social_network_subflow`, `theme_generation_subflow`) but not strictly required initially. Start with one main flow.
- **Tasks**: `extract_network_task`, `detect_communities_task`, `model_topics_task`, `generate_themes_task`, `analyze_transitions_task`.

## 7. Task-boundary Decision Table

| Task Name | Domain Function | Idempotent |
| :--- | :--- | :--- |
| `extract_network_task` | `run_network_phase` | Yes |
| `detect_communities_task` | `run_community_phase` | Yes |
| `model_topics_task` | `run_topic_phase` | Yes |
| `generate_themes_task` | `process_single_file_themes` / `generate_llm_themes` | Yes (cached via provider) |
| `analyze_transitions_task` | `get_community_transition` | Yes |

## 8. Provider Lifecycle
- Prefect must **not** serialize or pass a live `CachedProvider`, HTTP client, lock, or provider router between tasks.
- **Lifecycle**:
  1. The flow reads the provider configuration and passes the serializable dictionary to `generate_themes_task`.
  2. The `generate_themes_task` constructs the provider locally (e.g., via `build_theme_provider`).
  3. The same provider instance is reused for all theme calls owned by that specific task execution.
  4. The provider is not returned from the task or persisted in Prefect state.
  5. Lower-level domain functions receive the live provider only within that task's local execution scope.
  6. No provider is constructed per community.
- **Future Distributed Execution**: If workers run tasks on different nodes, each worker will independently construct its own provider instance using the serialized config.

## 9. Fallback versus Retry Ownership

| Layer | Responsibility | Details |
| :--- | :--- | :--- |
| Provider SDK (`BaseLLMProvider`) | Protocol-level retries | Low-level rate limits (429), timeouts. Bounds concurrency. |
| Provider Router | Model fallback | Switches to fallback models/providers if the champion fails. `RoutingBenchmarkProvider` owns this. Prefect MUST NOT create a separate fallback mechanism. |
| Prefect Task (`generate_themes_task`) | Transient task-level failure | `retries=0` initially. A future maximum of 1 retry is permitted **only** when the routing provider raises a typed aggregate error proving that *all* attempted providers failed *transiently*. Fallback-chain exhaustion by itself is not sufficient. Invalid credentials, invalid configuration, unsupported models, schema errors, and programming defects remain terminal and are never retried. |
| Prefect Task (General) | Deterministic failure | Configuration, schema, credential, and programming failures are **never retried**. |
| Prefect Task (Graph Store) | Connection failure | Bounded Prefect retries allowed for DB connection timeouts. |

## 10. Result-persistence Strategy
- **Directory**: Results will be stored in a private local directory: `.prefect_results/`.
- **Git-ignore**: This directory must be fully ignored in `.gitignore`.
- **Persistence Rules**: Prefect results contain **only small typed references and metadata** (e.g., file paths, basic metrics). Use `persist_result=True` only for selected small task returns when needed for cache/resume logic.
- **Prohibited**: Large DataFrames, NetworkX graphs, raw messages, provider objects, and credentials are **never** persisted as Prefect results. Pipeline outputs continue to be written by the project code exactly as before.
- **Retention/Cleanup**: Periodic manual cleanup of `.prefect_results/` is recommended when disk space is constrained. Older run results can be safely deleted without breaking historical lineage.
- **Separation**: This storage is strictly separated from Prefect's SQLite orchestration database (`~/.prefect/prefect.db`).

## 11. Initial Task Runner and Concurrency Policy
- The initial execution model will explicitly use:
  ```python
  ThreadPoolTaskRunner(max_workers=1)
  ```
  for the top-level flow (or rely on normal non-submitted task calls where sequential execution is strictly intended).
- Prefect's default task runner is concurrent. The initial implementation must **not** rely on the default worker count.
- Keep monthly runs sequential by default. Avoid process-based or distributed runners for now.
- Avoid parallelizing memory-heavy tasks (NetworkX, LDA).
- Bounded LLM concurrency remains controlled by the existing provider controls.
- **Future Concurrency Enablement**: Concurrency will only be introduced after output-path isolation, serialization verification, and memory profiling prove it is safe.

## 12. Local Server Behavior
- A persistent local server (`prefect server start`) is optional and used for UI and retained history.
- Direct local flow execution remains possible without a manually started server (using ephemeral or default local SQLite DB).
- Prefect result storage is configured separately from the orchestration DB.
- Unit and flow tests will use `prefect_test_harness()` with a temporary database.
- Cloud deployments, workers, and schedules remain deferred.

## 13. Cache-key Strategy
- Do not use the entire Git commit as the sole invalidation mechanism.
- Cache keys (`cache_key_fn`) must be stage-specific, combining:
  - Input/DVC or upstream artifact hash.
  - Relevant configuration subset (e.g., threshold config for network).
  - Algorithm parameters and random seeds.
  - Prompt version and provider/model settings (for theme generation).
  - A task-specific semantic implementation version.
- **Invalidation Matrix**:
  - Network thresholds changed -> Invalidates network and downstream.
  - Min members changed -> Invalidates community and downstream.
  - LDA parameters changed -> Invalidates topics and downstream.
  - Provider model/temperature changed -> Invalidates themes but NOT network/community/topics.
  - DVC hash changed -> Invalidates all dependent analytical stages.

## 14. Prefect Asset Graph
Use Prefect 3 APIs (`Asset`, `@materialize`, explicit upstream dependencies) for key outputs. Temporary files and Prefect result objects are not Assets.

| Asset Logical Key | Materializing Task | Physical Output Path | Platform | Content Type | Partition Identity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `community-analysis/network-interactions` | `extract_network_task` | `data/processed/...` | Twitter/TG | Reply/Retweet | Month-Year |
| `community-analysis/detected-communities` | `detect_communities_task` | `results/.../communities/` | Twitter/TG | Reply/Retweet | Month-Year |
| `community-analysis/topic-model-results` | `model_topics_task` | `results/.../LDA/scores/` | Twitter/TG | Reply/Retweet | Month-Year |
| `community-analysis/matched-topics` | `model_topics_task` | `results/.../LDA/matched/` | Twitter/TG | Reply/Retweet | Month-Year |
| `community-analysis/generated-themes` | `generate_themes_task` | `results/.../*_with_themes.csv` | Twitter/TG | Reply/Retweet | Month-Year |
| `community-analysis/community-transitions`| `analyze_transitions_task` | `results/.../community_transition.csv` | Twitter/TG | Reply/Retweet | Longitudinal |

## 15. DVC Lineage Integration
- The flow reads `dvc rev-parse` or hashes of `.dvc` tracking files at runtime.
- Attach the DVC hash to the `PipelineRunContext` and embed it in task cache keys.

## 16. Run-context and Manifest Contract
- Introduce `PipelineRunContext` containing: `pipeline_run_id` (UUID), `prefect_flow_run_id`, `dvc_dataset_hash`, `timestamp`, `config_hash`.
- Extend existing pipeline output manifests to include `prefect_flow_run_id` and `pipeline_run_id`.

## 17. MLflow Handoff Requirements
- The `PipelineRunContext` captures `pipeline_run_id`, which MLflow will later use as its parent run ID.
- Prefect metrics will eventually be logged to MLflow via a dedicated task or block in Phase 7.

## 18. CLI Migration Strategy
- Introduce `--orchestrator prefect` to `src/cli.py` or a dedicated command (`run-prefect-pipeline`) while keeping direct execution the default for Phase 6.

## 19. Testing Strategy
- Core domain unit tests remain Prefect-unaware.
- Add `tests/orchestration/` to test flows using `prefect_test_harness()` and synthetic data.
- Orchestration tests run entirely locally with temporary SQLite databases and no required server.

## 20. Dependency Plan
- Add `prefect` (version `~=3.0.0`) to `pyproject.toml` under a new optional group `[project.optional-dependencies] orchestration = ["prefect>=3.0.0"]`.
- Do not modify `uv.lock` or add Prefect in this planning phase.

## 21. Exact Files Expected to Change
- `pyproject.toml`
- `src/cli.py`
- `src/orchestration/*` (new)
- `tests/orchestration/*` (new)

## 22. Implementation Milestones
- **Milestone 1**: [x] Orchestration foundation (Dependencies, Context, Cache logic, Test Harness).
- **Milestone 2**: Core analytical task wrappers (Network, Community, Topics).
- **Milestone 3**: Theme and provider orchestration (Local instantiation, SDK integration).
- **Milestone 4**: Prefect Asset implementations (`@materialize` usage, graph creation).
- **Milestone 5**: Manifests, DVC linkage, and MLflow context prep.
- **Milestone 6**: CLI integration and local UI observability.
- **Milestone 7**: Cache, resume, and failure validation tests.
- **Milestone 8**: Documentation updates (README, Architecture).

## 23. Validation Commands
- `uv sync --all-extras`
- `make test`
- `prefect server start` (background)
- `python -m src.cli run-all --config <test_config> --orchestrator prefect`

## 24. Acceptance Criteria
- `make test` remains green.
- Small synthetic fixture completes via Prefect flow.
- No live LLM API is needed in orchestration tests.
- Tests execute via `prefect_test_harness`.
- Domain functions remain independently callable.
- DVC dataset identities and Prefect flow-run IDs appear in the final manifest.
- Large structures are NOT persisted as Prefect results.
- Unchanged reruns hit Prefect task cache cleanly.
- Provider instances are safely constructed locally per task.

## 25. Risks and Mitigations
- **Risk**: Provider serialization issues.
  - *Mitigation*: Ensure `generate_themes_task` receives config only, constructing the provider internally.
- **Risk**: Cache redundancy.
  - *Mitigation*: Strictly delineate Prefect coarse skipping from `CachedProvider` fine-grained deduplication.
- **Risk**: Orchestration database bloat.
  - *Mitigation*: Limit result persistence to file paths/metadata references.

## 26. Rollback Strategy
- Remove `src/orchestration/` and the optional `prefect` dependency from `pyproject.toml`.

## 27. Deferred Deployment and Scheduling Work
- Cloud deployments, Docker images for Prefect workers, Prefect Cloud integration, and scheduled runs are explicitly deferred.

### Milestone 1: Orchestration Foundation [x]

*   Add Prefect 3 to project optional dependencies (`prefect>=3.7.8,<4`) via `pyproject.toml` (group: `orchestration`).
*   Migrate `dev` dependencies to `[dependency-groups]` to support `uv sync --frozen --extra orchestration`.
*   Establish explicit `.prefect_results/` default storage.
*   Implement deterministic cache-key helpers (via string hashing of configuration subsets, inputs, and semantic versions).
*   Add typed data contracts (`DatasetIdentity`, `ArtifactReference`, `PipelineRunContext`).
*   Establish error retry classifications (`TransientProviderAggregateError`, `ProviderChainExhaustedError`, etc.).
    *   *Retry Semantics*: Derived strictly from typed constituent attempt failures. Fallback chain exhaustion (`ProviderChainExhaustedError`) is terminal unless `attempt_exceptions` is non-empty and *every* attempt is `is_retryable()`. Programming errors, schema violations, invalid configurations, and missing credentials are unconditionally terminal.
*   Ensure environment settings (`PREFECT_RESULTS_LOCAL_STORAGE_PATH`) are not modified on import, strictly via `configure_prefect_results_dir()`.
*   *Validation*: `DatasetIdentity` validates strictly for a 64-character lowercase hexadecimal `sha256` string.
*   *Installation & Testing*: `uv run --frozen --extra orchestration python -m pytest tests/unit` is the authoritative reproducible test command.
*   *Smoke Test Isolation*: Flow successfully executed offline using isolated `PREFECT_HOME` and `PREFECT_RESULTS_LOCAL_STORAGE_PATH`. Validated that small metadata persists without touching `~/.prefect/prefect.db` or `~/.prefect/storage`.

## 29. Progress Log
- [x] Phase 6 Planning completed and revised based on feedback.
- [x] **Milestone 2A: Foundation Flow Wrapper**
  - Wrap the coarse `run_network_community_pipeline` function.
  - Discover output paths via an explicit expected-output contract (no recursive scans).
  - Enforce isolated output directories keyed by `pipeline_run_id`.
  - Resolve dataset identity supporting both `known_sha256` and `verify_file_hash`.
  - Validate run configuration reusing the existing loader/validator rules.
  - Ensure returned Prefect states contain only lightweight metadata (no DataFrames).
  - Status: **Complete** (Verified with explicit artifacts, isolated outputs, config reuse, dataset hashing modes, clean test suite, and end-to-end integration via `smoke_test_2a.py`).

## 30. Official Prefect Documentation References
- Prefect 3.0 Task Runners (`ThreadPoolTaskRunner`): https://docs.prefect.io/3.0/develop/task-runners
- Prefect 3.0 Assets (`Asset`, `@materialize`): https://docs.prefect.io/3.0/manage/assets
- Prefect 3.0 Result Persistence & Caching: https://docs.prefect.io/3.0/develop/results, https://docs.prefect.io/3.0/develop/caching
- Prefect 3.0 Testing (`prefect_test_harness`): https://docs.prefect.io/3.0/develop/testing
