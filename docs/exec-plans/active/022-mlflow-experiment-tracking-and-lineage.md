# Plan 022: MLflow Experiment Tracking and Operational Lineage

Status: active

Owner: agent

Last updated: 2026-07-14

Implementation status: code-complete in the review snapshot; repository acceptance remains pending the authoritative lockfile refresh, full `make test`, exact-commit, and detached-worktree gates in the user's complete local repository.

## 1. Goal

Add local MLflow experiment tracking to the verified Prefect pipeline so every orchestrated analysis run records reproducible, queryable metadata, metrics, stage status, safe lineage, and small artifact references without changing the analytical algorithms or duplicating DVC-managed datasets.

The milestone is complete when a local user can run the Prefect pipeline, open the MLflow UI, locate the parent pipeline run and its stage runs, inspect dataset/Git/DVC/config lineage, compare Topic and Theme metrics, and verify that no credentials, provider objects, DataFrames, graphs, raw messages, or large analytical outputs were stored in MLflow.

## 2. Verified Starting Baseline

- Stable branch: `main`.
- Verified merge commit: `5a08199e2d027133eca4a41d2f75a8702186a48d`.
- Prefect Topic and Theme implementation commit: `8fbc00c2a4a7b6efda6805409a8c0e3d386c5ecb`.
- Plans 020 and 021 are completed.
- Detached-worktree verification passed.
- Current regression baseline:
  - 286 tests passed.
  - 1 expected Memgraph integration skip when Docker is unavailable.
  - 6 existing warnings.
  - 0 failures.
- The current orchestration boundary is artifact-reference based.
- DVC owns raw dataset versioning.
- Prefect owns execution order, retries, run context, and task/flow state.
- Provider fallback remains owned by the provider router.
- Topic and Theme task retries remain `0`.
- Domain pipeline functions remain Prefect-independent.

Create the implementation branch from this baseline:

```bash
git switch main
git status --short
git switch -c experiment/mlflow-tracking
```

## 3. Context and Existing Contracts

The implementation must preserve the following repository contracts:

- `src/orchestration/models.py`
  - `PipelineRunContext`
  - `PipelineRunResult`
  - `ArtifactReference`
  - Topic and Theme input/output bundles
- `src/orchestration/composition_flow.py`
  - `run_monthly_analysis_flow`
- `src/orchestration/tasks.py`
  - configuration validation
  - dataset identity resolution
  - network/community execution
  - Topic execution
  - Theme execution
- `src/orchestration/artifact_validation.py`
  - containment, size, hash, and schema validation
- `src/providers/`
  - provider construction
  - caching
  - routing and fallback
- `configs/providers.yml`
  - provider/model configuration
- DVC metadata under `data/raw/**.dvc`
- Existing `.prefect_results/` separation and result-boundary tests
- Existing external-network guard in `tests/conftest.py`

The MLflow integration must be an additive observability layer around these contracts. It must not become a new analytical execution path.

## 4. Ownership Boundaries

| System | Ownership in this repository |
|---|---|
| Git | Source-code and configuration revision |
| DVC | Dataset identity, content versioning, and data retrieval |
| Prefect | Orchestration, task/flow state, retries, execution order, and operational run identity |
| MLflow | Experiment metadata, comparison metrics, safe tags/parameters, stage status, and small lineage artifacts |
| Domain pipelines | Analytical computation and analytical output generation |
| Provider router | Primary/fallback provider selection and fallback semantics |

MLflow must not replace DVC, Prefect, the provider cache, or the analytical output directories.

## 5. Non-Goals

This plan intentionally does not implement:

- MLflow Model Registry.
- Model packaging or model serving.
- Automatic promotion or deployment.
- Remote MLflow infrastructure.
- Cloud object storage.
- Authentication or multi-user MLflow access control.
- Prefect deployments, schedules, workers, or Prefect Cloud.
- Prefect Assets.
- DVC pipeline orchestration.
- DVC experiment replacement.
- Automatic dataset upload to MLflow.
- Logging raw message datasets to MLflow.
- Logging full Topic or Theme CSV outputs to MLflow.
- Logging provider prompts or raw provider responses.
- MLflow autologging.
- LLM tracing or OpenTelemetry tracing.
- Changes to Topic, Theme, network, or community algorithms.
- Changes to provider routing or fallback semantics.
- New parallelism.
- Changes to `ThreadPoolTaskRunner(max_workers=1)`.
- Changes to the expected Memgraph skip policy.

## 6. Primary Design Decisions

### 6.1 Explicit local backend

Do not rely on MLflow's process-wide default tracking backend.

Use explicit repository-relative configuration that is resolved to absolute paths at runtime:

```yaml
tracking:
  enabled: false
  backend: mlflow
  experiment_name: community-analysis
  backend_store_path: .mlflow/mlflow.db
  artifact_root: .mlflow/artifacts
  nested_stage_runs: true
  failure_policy: warn
  log_artifact_references: true
```

The runtime resolver converts:

- `backend_store_path` to an absolute SQLite tracking URI.
- `artifact_root` to an absolute file URI.

The first milestone uses a local SQLite backend because execution is local and the current Prefect runner is sequential. The application dependency is pinned to `mlflow-skinny==3.14.0`; the full UI is launched on demand with `uvx --from mlflow==3.14.0` so CI and analytical execution do not install server/model-serving dependencies.

### 6.2 Disabled by default

Tracking remains disabled unless configuration explicitly enables it.

The direct analytical and Prefect workflows must behave exactly as before when:

```yaml
tracking:
  enabled: false
```

### 6.3 Explicit client operations

Use `MlflowClient` or an equivalent explicit-client adapter.

Do not rely on a globally active MLflow run shared across Prefect task boundaries. MLflow client objects are constructed locally and are never passed through or persisted by Prefect.

### 6.4 Serializable run references

Only a small typed run reference may cross Prefect boundaries:

```python
@dataclass(frozen=True)
class TrackingRunReference:
    backend: str
    experiment_id: str
    parent_run_id: str
    tracking_uri: str
```

The exact final fields may be adjusted to match repository model conventions, but the object must contain only strings and small metadata.

It must never contain:

- `MlflowClient`
- active-run objects
- provider objects
- HTTP clients
- DataFrames
- graphs
- models
- raw configuration

### 6.5 One parent run per Prefect pipeline run

Create one MLflow parent run for every tracked invocation of `run_monthly_analysis_flow`.

The parent run must be tagged with:

- `pipeline_run_id`
- `prefect_flow_run_id`
- `dataset_id`
- `git_commit`
- `dvc_revision`
- `config_digest`
- `tracking_schema_version`
- `orchestration_semantic_version`
- execution mode

### 6.6 Optional nested stage runs

When `nested_stage_runs: true`, create child runs for:

- `network_community`
- `topic`
- `theme`

Use explicit parent-run linkage rather than relying on thread-local nested-run state.

A child run is created only when its corresponding stage executes.

Examples:

- Network only: parent + network child.
- Topic only: parent + Topic child.
- Theme only: parent + Theme child.
- Full pipeline: parent + network + Topic + Theme children.

### 6.7 Tracking failures do not change analytical outcomes

Initial policy:

```yaml
failure_policy: warn
```

If the local MLflow backend cannot be initialized or written:

1. Log a warning through the normal application/Prefect logger.
2. Continue the analytical pipeline.
3. Do not retry analytical tasks because of tracking failure.
4. Do not mask the original analytical exception.

A strict tracking mode is deferred.

## 7. Proposed Module Structure

Add a dedicated package that is independent from analytical domain code:

```text
src/tracking/
├── __init__.py
├── contracts.py
├── factory.py
├── mlflow_tracker.py
├── noop_tracker.py
├── sanitization.py
└── summaries.py
```

Responsibilities:

### `contracts.py`

Define small typed contracts:

- `TrackingSettings`
- `TrackingRunReference`
- `StageRunReference`
- `StageMetrics`
- `TrackingArtifactReference`
- `ExperimentTracker` protocol

### `factory.py`

- Build `NoOpExperimentTracker` when tracking is disabled.
- Build `MlflowExperimentTracker` when enabled.
- Resolve local paths safely.
- Validate supported backend and failure policy.
- Never accept credentials through this milestone.

### `mlflow_tracker.py`

Implement explicit-client operations:

- ensure experiment exists
- start parent run
- finish parent run
- start stage run
- finish stage run
- log parameters
- log tags
- log metrics
- log small JSON summaries
- log selected small artifacts

### `noop_tracker.py`

Implement the same protocol without side effects.

### `sanitization.py`

Provide one explicit shared sanitizer for tracking payloads.

The sanitizer must:

- use allowlisted output schemas
- recursively reject secret-like keys
- reject unsupported object types
- reject excessive values and payload size
- normalize paths
- normalize enums and datetimes

### `summaries.py`

Build safe, deterministic summaries from existing typed output bundles and artifact references.

This module must not read complete analytical CSV files unless a metric explicitly requires a bounded schema-aware count.

## 8. Files Expected to Change

Expected additions:

- `src/tracking/__init__.py`
- `src/tracking/contracts.py`
- `src/tracking/factory.py`
- `src/tracking/mlflow_tracker.py`
- `src/tracking/noop_tracker.py`
- `src/tracking/sanitization.py`
- `src/tracking/summaries.py`
- `tests/unit/test_tracking_contracts.py`
- `tests/unit/test_tracking_sanitization.py`
- `tests/unit/test_mlflow_tracker.py`
- `tests/unit/test_tracking_summaries.py`
- `tests/integration/test_mlflow_tracking_smoke.py`

Expected modifications:

- `pyproject.toml`
- `uv.lock`
- `.gitignore`
- `Makefile`
- `.github/workflows/ci.yml`
- `configs/algorithms.yml` or a dedicated tracking config file
- `src/config/defaults.py`
- `src/config/loader.py`
- `src/orchestration/models.py`
- `src/orchestration/composition_flow.py`
- `src/orchestration/tasks.py`
- `tests/unit/test_config.py`
- `tests/unit/test_orchestration_models.py`
- `tests/unit/test_orchestration_tasks.py`
- `tests/integration/test_orchestration_smoke.py`
- `README.md`
- this execution plan

Do not modify analytical implementation files unless a small read-only metric accessor is demonstrably required and separately justified.

## 9. Dependency and Environment Policy

Add MLflow as an optional dependency group:

```toml
[project.optional-dependencies]
tracking = [
  "mlflow>=<validated-compatible-version>",
]
```

The exact lower bound must be selected by checking current official MLflow releases and compatibility with Python 3.11 and the locked repository environment.

Do not add an unconstrained dependency.

Update validation commands to install both optional groups:

```bash
uv sync --frozen --extra orchestration --extra tracking
```

Update `make test` and CI only as required to make tracking tests available. Do not otherwise redesign CI.

## 10. Git-ignore and Local Storage

Add all local MLflow state to `.gitignore`:

```gitignore
.mlflow/
mlruns/
mlflow.db
```

The canonical repository-owned local paths are:

```text
.mlflow/mlflow.db
.mlflow/artifacts/
```

Do not place MLflow state inside:

- `.prefect/`
- `.prefect_results/`
- `data/raw/`
- DVC cache directories
- pipeline output roots

## 11. Configuration Contract

Add a validated tracking configuration model or equivalent explicit validation.

Required fields when tracking is enabled:

```text
backend
experiment_name
backend_store_path
artifact_root
nested_stage_runs
failure_policy
log_artifact_references
```

Validation rules:

- `backend` must equal `mlflow` in this milestone.
- `experiment_name` must be non-empty.
- `backend_store_path` must be repository-relative in committed config.
- `artifact_root` must be repository-relative in committed config.
- Runtime paths must resolve under the repository root or an explicitly permitted root.
- `failure_policy` must equal `warn` in this milestone.
- Unknown tracking keys fail validation.
- Environment-variable credentials are not supported or read.
- No silent defaults when `enabled: true`, except the tracking schema version owned by code.

When tracking is disabled, validation must not require local MLflow directories to exist.

## 12. Tracking Schema Versions

Define explicit semantic versions:

```text
tracking_schema_version = 1.0
tracking_adapter_version = 1.0.0
```

Persist these as tags on the parent run and in the lineage summary.

Schema changes require version increments and tests.

## 13. Parent Run Contract

The parent run represents one Prefect pipeline execution.

### Parent run name

Use a deterministic readable name:

```text
{data_type}-{content_type}-{year}-{month}-{pipeline_run_id_short}
```

The MLflow run ID remains unique even when the same logical inputs are executed multiple times.

### Parent tags

Allowlist only:

```text
tracking_schema_version
tracking_adapter_version
pipeline_run_id
prefect_flow_run_id
dataset_id
data_type
content_type
month
year
git_commit
git_branch
dvc_revision
config_digest
orchestration_semantic_version
execution_mode
run_status
```

### Parent parameters

Allowlist only immutable run configuration:

```text
run_topics
run_themes
network_algorithm
community_algorithm
topic_algorithm
topic_random_seed
theme_prompt_version
configured_primary_provider
configured_primary_model
configured_fallback_count
```

Do not log complete provider configuration.

### Parent metrics

At completion log:

```text
total_duration_seconds
stage_count
artifact_count
artifact_total_bytes
completed_stage_count
failed_stage_count
```

## 14. Stage Run Contracts

### 14.1 Network/community child run

Parameters/tags:

```text
stage_name=network_community
stage_semantic_version
network_algorithm
community_algorithm
```

Metrics when available:

```text
input_row_count
node_count
edge_count
community_count
matched_message_count
stage_duration_seconds
artifact_count
artifact_total_bytes
```

### 14.2 Topic child run

Parameters/tags:

```text
stage_name=topic
stage_semantic_version
topic_algorithm
random_seed
```

Metrics:

```text
community_count
topic_count
matched_community_count
partial_match_count
unmatched_community_count
theme_input_artifact_count
stage_duration_seconds
artifact_count
artifact_total_bytes
```

### 14.3 Theme child run

Parameters/tags:

```text
stage_name=theme
stage_semantic_version
prompt_version
configured_primary_provider
configured_primary_model
configured_fallback_count
```

Metrics:

```text
theme_input_count
theme_output_count
theme_generation_success_count
theme_generation_failure_count
provider_fallback_count
provider_retry_count
visualization_count
stage_duration_seconds
artifact_count
artifact_total_bytes
```

Only log a metric when its value is computed reliably from an existing bounded contract. Do not invent zeros for unavailable metrics; omit unavailable metrics and document them as deferred.

## 15. Provider Lineage Contract

Reuse the safe provider summary produced by the Theme stage.

Allowed provider lineage fields:

```text
schema_version
configured_primary_provider
configured_primary_model
configured_fallback_chain
provider_config_digest
prompt_version
generation_settings_digest
semantic_task_version
```

MLflow may log:

- scalar allowlisted values as tags or parameters
- fallback-chain length as a numeric parameter
- the complete safe provider summary JSON as a small artifact

MLflow must not log:

- raw provider configuration
- API keys
- tokens
- passwords
- authorization headers
- credentials
- raw prompts
- raw provider responses
- request/response headers
- provider object representations

Add a nested secret-injection test that scans:

- parent tags
- parent parameters
- child tags
- child parameters
- logged JSON artifacts
- captured logs

## 16. Dataset and DVC Lineage Contract

Log references, not dataset contents.

Required lineage fields when available:

```text
dataset_id
dataset_relative_path
dataset_sha256
dataset_byte_size
dvc_file_relative_path
dvc_content_hash
dvc_revision
git_commit
```

Rules:

- Dataset paths must be normalized relative to repository root where possible.
- Do not log absolute home-directory paths.
- Do not upload raw dataset files to MLflow.
- Do not duplicate DVC cache objects.
- Missing optional DVC metadata must be represented by omission or an explicit safe status tag, not a fabricated value.

## 17. Artifact Logging Policy

### Allowed MLflow artifacts

- `lineage_summary.json`
- `run_metrics_summary.json`
- safe `provider_run_summary.json`
- optional bounded warning/failure summary JSON
- optional artifact-reference manifest JSON

### Reference manifest schema

```json
{
  "schema_version": "1.0",
  "pipeline_run_id": "...",
  "artifacts": [
    {
      "asset_key": "...",
      "relative_path": "...",
      "sha256": "...",
      "byte_size": 123,
      "media_type": "...",
      "stage": "topic"
    }
  ]
}
```

### Prohibited MLflow artifacts

- Raw datasets.
- DVC cache files.
- Full network/community CSVs.
- Full Topic CSVs.
- Full Theme CSVs.
- Large visualization collections.
- Pickled models.
- Gensim models or dictionaries.
- NetworkX graphs.
- Prefect databases.
- Prefect result-storage files.
- Provider caches.

Set and test an explicit maximum size for each generated summary artifact.

## 18. Result-boundary Policy

MLflow integration must not weaken the existing Prefect result boundary.

Permitted across Prefect task/flow boundaries:

- `TrackingRunReference`
- `StageRunReference`
- strings
- numbers
- booleans
- small mappings with fixed schemas
- existing typed artifact references

Prohibited:

- `MlflowClient`
- MLflow run objects
- active-run contexts
- DataFrames or Series
- NetworkX graphs
- Gensim objects
- provider objects
- HTTP clients
- raw prompts/messages/responses
- secret-bearing configuration
- large bytes or collections

Extend the recursive result-boundary tests accordingly.

## 19. Orchestration Integration

### 19.1 Parent lifecycle

At the top-level composition flow:

1. Validate configuration.
2. Resolve pipeline and dataset identity.
3. Build a tracking adapter locally.
4. Start the parent tracking run when enabled.
5. Execute requested analytical stages.
6. Log parent summary metrics and artifact-reference manifest.
7. Mark parent run `FINISHED` on success.
8. Mark parent run `FAILED` on analytical failure, preserving the original exception.
9. Return the existing analytical result plus optional small tracking reference.

### 19.2 Stage lifecycle

For each executed stage:

1. Create a stage child run.
2. Record start time.
3. Execute the existing domain wrapper.
4. Derive metrics from the returned typed bundle and bounded artifact metadata.
5. Log safe metrics/tags/artifacts.
6. Mark child run `FINISHED`.
7. On failure, record safe failure category and mark child run `FAILED`.
8. Re-raise the original analytical error unchanged.

### 19.3 Tracking-disabled path

When disabled:

- Do not import or initialize a live MLflow backend unnecessarily.
- Do not create `.mlflow/`.
- Do not alter the returned analytical artifacts.
- Do not change task retry or cache behavior.

## 20. Failure and Status Semantics

Use explicit run termination statuses:

```text
FINISHED
FAILED
KILLED only when explicitly supported later
```

Safe failure tags may include:

```text
failure_category
failure_stage
exception_type
```

Do not log:

- complete exception representations if they may include credentials
- raw provider payloads
- full local paths
- environment variables

Sanitize failure messages before logging. Prefer typed error category and exception class over free-form text.

Tracking failures follow `failure_policy: warn` and must not replace analytical failures.

## 21. Idempotency and Duplicate Runs

- Every Prefect pipeline execution creates a new MLflow run ID.
- Reusing the same `pipeline_run_id` accidentally must be detected in tests or prevented by existing pipeline ID generation.
- Run names may repeat; run IDs may not.
- Parameters must be logged once per run with stable values.
- Do not attempt to mutate an existing parameter to a different value.
- Metrics may be logged once at completion in this milestone.
- Resume/reconnect to an interrupted MLflow run is deferred.

## 22. Local MLflow UI Workflow

Document a local workflow in `README.md` and/or a focused MLflow guide:

```bash
uv sync --frozen --extra orchestration --extra tracking
mlflow ui --backend-store-uri sqlite:///<absolute-path-to>/.mlflow/mlflow.db
```

The implementation should provide a repository command that avoids requiring users to manually construct the absolute path, for example:

```bash
make mlflow-ui
```

The command must bind to loopback by default.

Do not expose the UI publicly by default.

## 23. Milestones

### Milestone 1: Tracking contracts and configuration

Tasks:

- [ ] Add MLflow optional dependency and update `uv.lock`. (`mlflow-skinny==3.14.0` is added; lock refresh is pending in the complete local repository.)
- [ ] Add `.mlflow/`, `mlruns/`, and `mlflow.db` ignores. (The source ZIP omitted the root `.gitignore`; apply the supplied fragment locally.)
- [x] Add validated tracking configuration.
- [x] Add tracking contracts and protocol.
- [x] Add no-op tracker.
- [x] Add explicit path resolution.
- [x] Add tracking schema/version constants.
- [x] Add unit tests for enabled and disabled configuration.
- [x] Confirm tracking-disabled runs do not create local MLflow state.

Validation:

```bash
uv lock --check
PYTHONPATH=. uv run --extra orchestration --extra tracking pytest \
  tests/unit/test_tracking_contracts.py \
  tests/unit/test_config.py \
  -v
```

Commit boundary:

```text
feat(tracking): add local experiment tracking contracts
```

### Milestone 2: Safe MLflow adapter

Tasks:

- [x] Implement explicit local SQLite `MlflowClient` adapter.
- [x] Implement experiment creation/reuse.
- [x] Implement parent run lifecycle.
- [x] Implement child run lifecycle with explicit parent linkage.
- [x] Implement allowlisted tags, parameters, and metrics.
- [x] Implement safe JSON artifact logging.
- [x] Implement warning-only tracking failure policy.
- [x] Add no-global-active-run tests.
- [x] Add secret-injection tests.
- [x] Add local SQLite adapter tests.

Validation:

```bash
PYTHONPATH=. uv run --extra orchestration --extra tracking pytest \
  tests/unit/test_tracking_sanitization.py \
  tests/unit/test_mlflow_tracker.py \
  -v
```

Commit boundary:

```text
feat(tracking): add safe local mlflow adapter
```

### Milestone 3: Prefect parent and stage integration

Tasks:

- [x] Integrate optional parent-run lifecycle with `run_monthly_analysis_flow`.
- [x] Integrate network/community child run.
- [x] Integrate Topic child run.
- [x] Integrate Theme child run.
- [x] Preserve task retries and cache settings.
- [x] Preserve provider lifecycle and fallback ownership.
- [x] Return only small tracking references.
- [x] Mark stage and parent status correctly on failures.
- [x] Ensure tracking backend failure does not fail analysis.

Validation:

```bash
PYTHONPATH=. uv run --extra orchestration --extra tracking pytest \
  tests/unit/test_orchestration_tasks.py \
  tests/unit/test_orchestration_models.py \
  tests/integration/test_orchestration_smoke.py \
  -v
```

Commit boundary:

```text
feat(orchestration): record prefect runs in mlflow
```

### Milestone 4: Metrics and lineage summaries

Tasks:

- [x] Add parent summary metrics.
- [x] Add network/community metrics where reliable.
- [x] Add Topic metrics.
- [x] Add Theme metrics.
- [x] Add safe provider summary logging.
- [x] Add dataset/Git/DVC lineage summary.
- [x] Add artifact-reference manifest.
- [x] Enforce bounded summary size.
- [x] Add deterministic summary tests.
- [x] Confirm no analytical file is duplicated into MLflow.

Validation:

```bash
PYTHONPATH=. uv run --extra orchestration --extra tracking pytest \
  tests/unit/test_tracking_summaries.py \
  tests/integration/test_mlflow_tracking_smoke.py \
  -v
```

Commit boundary:

```text
feat(tracking): log pipeline metrics and lineage summaries
```

### Milestone 5: Local operator workflow and final hardening

Tasks:

- [x] Add `make mlflow-ui` or an equivalent repository command.
- [x] Document local tracking enablement and cleanup.
- [x] Update CI to install the tracking extra.
- [x] Add a clean temporary-SQLite integration smoke test.
- [ ] Run the complete suite.
- [ ] Verify the exact commit in a detached worktree.
- [ ] Update this plan with final commit hashes and exact test counts.
- [ ] Move this plan to `completed/` only after all acceptance criteria pass.

Validation:

```bash
uv lock --check
make test
git diff --check
git show --check HEAD
git status --short
```

Commit boundary:

```text
test(tracking): finalize mlflow lineage verification
```

## 24. Test Matrix

### Configuration tests

- Tracking disabled with no MLflow directories.
- Tracking enabled with valid relative paths.
- Missing enabled fields fail validation.
- Absolute committed paths fail validation.
- Unsupported backend fails validation.
- Unknown keys fail validation.

### Adapter tests

- Experiment is created once and reused by name.
- Parent run starts and finishes.
- Child run contains explicit parent linkage.
- Failed stage is marked failed.
- Tracking failure warns and does not fail analysis.
- No active global run leaks after calls.
- Separate calls do not share clients or active state.

### Sanitization tests

Inject nested values containing:

```text
OPENAI_API_KEY
GEMINI_API_KEY
apiKey
access_token
client_secret
authorization
credentials
token
password
secret
Bearer secret-value
```

Assert none appears in:

- MLflow tags
- MLflow parameters
- MLflow artifacts
- captured application logs
- Prefect results

### Parent/child topology tests

- Network-only run: one parent and one child.
- Topic-only run: one parent and one child.
- Theme-only run: one parent and one child.
- Full run: one parent and three children.
- Disabled run: zero MLflow runs.

### Metrics tests

- Numeric types only for MLflow metrics.
- No fabricated zero for unavailable metrics.
- Deterministic counts for fixed fixture artifacts.
- Stage duration is non-negative.
- Artifact counts and total bytes match typed artifact references.

### Dataset lineage tests

- Dataset SHA-256 matches actual input.
- Dataset byte size matches actual input.
- DVC pointer metadata is captured when available.
- Absolute user home path is not logged.
- Raw dataset is not present in MLflow artifacts.

### Result-boundary tests

Reject:

- `MlflowClient`
- active-run objects
- DataFrames/Series
- graph objects
- provider objects
- HTTP clients
- Gensim objects
- raw messages/prompts/responses
- secret-bearing mappings

### Integration smoke test

Use:

- `prefect_test_harness()`
- temporary `PREFECT_HOME`
- temporary Prefect result directory
- temporary SQLite MLflow backend
- temporary MLflow artifact root
- mock/fake domain stages
- external-network guard

Verify:

- parent run exists
- expected child runs exist
- all successful runs are `FINISHED`
- parent-child linkage is correct
- parameters/tags/metrics are queryable with `MlflowClient`
- summary artifacts exist
- no secrets exist
- no raw analytical files were copied
- Prefect analytical result remains correct

## 25. Acceptance Criteria

- [x] MLflow is an optional, explicit local tracking layer.
- [x] Tracking is disabled by default.
- [x] Tracking-disabled execution remains behaviorally unchanged.
- [x] Local paths are explicit and repository-relative in committed config.
- [ ] MLflow state is fully ignored by Git.
- [x] One parent MLflow run is created per tracked Prefect pipeline run.
- [x] Only executed stages create child runs.
- [x] Parent-child relationships are explicit and queryable.
- [x] MLflow client and run objects never cross Prefect boundaries.
- [x] No global active-run state leaks between tasks or tests.
- [x] Dataset identity includes safe Git/DVC/hash lineage.
- [x] Raw datasets are not uploaded to MLflow.
- [x] Full analytical CSV outputs are not uploaded to MLflow.
- [x] Provider configuration is represented only through safe allowlisted lineage.
- [x] Nested secrets are absent from tags, parameters, artifacts, logs, and Prefect state.
- [x] Topic and Theme metrics are logged only when reliably derivable.
- [x] Artifact-reference manifests are bounded and deterministic.
- [x] Tracking failures warn and do not change analytical outcomes.
- [x] Analytical failures preserve their original exception semantics.
- [x] Existing Prefect retries, cache policy, and sequential runner remain unchanged.
- [x] Provider fallback remains router-owned.
- [x] DVC remains dataset-version owner.
- [x] Tests do not make external network calls.
- [ ] Local SQLite MLflow integration smoke test passes.
- [ ] Full `make test` passes.
- [ ] `git diff --check` passes.
- [ ] `git show --check HEAD` passes.
- [ ] Exact final commit passes in a detached worktree.
- [ ] Final working tree is clean.
- [ ] Final test counts and commit hashes are recorded in this plan.

## 26. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| MLflow introduces large dependency and lockfile churn | Keep it in an explicit optional `tracking` dependency group and review the lockfile diff. |
| SQLite locking during tests | Use one isolated database per test and preserve sequential execution. |
| MLflow global active-run state leaks | Use explicit `MlflowClient` operations and test that no active run remains. |
| Raw configuration leaks credentials | Build all MLflow payloads from fixed allowlists; never dump raw config. |
| Absolute local paths reduce reproducibility | Normalize to repository-relative references and hash identities. |
| Large outputs are duplicated into MLflow | Log only small summaries and artifact-reference manifests. |
| Tracking failure breaks analysis | Initial failure policy is warning-only and separately tested. |
| Metrics are inferred inaccurately | Log only metrics supported by explicit typed contracts or bounded schema-aware reads. |
| Parameters are logged with conflicting values | Define immutable parameter names and log each once per run. |
| Parent run remains unfinished after failure | Use `try/except/finally` lifecycle handling and explicit status tests. |
| Tests accidentally use a shared developer MLflow database | Every test sets an isolated temporary tracking URI and artifact root. |
| CI exposes MLflow UI or network ports | CI uses SDK against temporary local SQLite only; no server is started. |

## 27. Rollback Plan

The feature must remain removable without affecting analytical execution.

Rollback steps:

1. Disable tracking in configuration.
2. Revert orchestration integration commits.
3. Remove `src/tracking/`.
4. Remove the `tracking` optional dependency and regenerate `uv.lock`.
5. Remove tracking-specific tests and documentation.
6. Leave `.mlflow/` ignored; local state can be deleted independently.

Analytical outputs, DVC data, Prefect state, and provider behavior must remain valid after rollback.

## 28. Deferred Follow-up Work

Potential later plans:

- Remote MLflow tracking server.
- Authentication and multi-user access.
- PostgreSQL backend.
- Cloud artifact storage.
- LLM trace capture with strict privacy review.
- Model Registry.
- Model evaluation and promotion workflows.
- Automated comparison reports.
- Prefect-to-MLflow UI links or Prefect artifacts.
- Resume/reconnect behavior for interrupted runs.
- Retention and cleanup automation.
- Production monitoring.

None of these may be added under Plan 022 without updating scope and acceptance criteria first.

## 29. Validation Commands

### Baseline before implementation

```bash
git status --short
git branch --show-current
git log -5 --oneline --decorate
uv lock --check
make test
```

Expected baseline:

```text
286 passed
1 expected Memgraph skip
0 failures
```

### Focused tracking suite

```bash
PYTHONPATH=. uv run --extra orchestration --extra tracking pytest \
  tests/unit/test_tracking_contracts.py \
  tests/unit/test_tracking_sanitization.py \
  tests/unit/test_mlflow_tracker.py \
  tests/unit/test_tracking_summaries.py \
  tests/integration/test_mlflow_tracking_smoke.py \
  -v
```

### Existing orchestration regression

```bash
PYTHONPATH=. uv run --extra orchestration --extra tracking pytest \
  tests/unit/test_orchestration_tasks.py \
  tests/unit/test_orchestration_topic_tasks.py \
  tests/unit/test_orchestration_theme_tasks.py \
  tests/unit/test_theme_pipeline_provider_batch.py \
  tests/integration/test_orchestration_smoke.py \
  -v
```

### Full suite

```bash
uv lock --check
make test
git diff --check
git status --short
```

### Exact-commit detached verification

```bash
FINAL_COMMIT=$(git rev-parse HEAD)
tmpdir=$(mktemp -d)

git worktree add --detach "$tmpdir" "$FINAL_COMMIT"

(
  cd "$tmpdir"
  uv lock --check
  uv sync --frozen --extra orchestration --extra tracking
  PYTHONPATH=. uv run pytest \
    tests/unit/test_tracking_contracts.py \
    tests/unit/test_tracking_sanitization.py \
    tests/unit/test_mlflow_tracker.py \
    tests/unit/test_tracking_summaries.py \
    tests/integration/test_mlflow_tracking_smoke.py \
    -v
  make test
)

verification_exit=$?
git worktree remove --force "$tmpdir"
echo "DETACHED_VERIFICATION_EXIT=$verification_exit"
exit "$verification_exit"
```

## 30. Final Report Requirements

The implementation agent must return:

### Repository state

- Initial commit.
- Final commit.
- Branch.
- Initial and final status.

### Dependency changes

- Exact MLflow version selected.
- Reason for version choice.
- Optional dependency group.
- Lockfile validation result.

### Tracking topology

- Parent run count.
- Child run count by execution mode.
- Parent-child linkage evidence.

### Lineage evidence

- Dataset ID and hash.
- DVC metadata captured.
- Git commit captured.
- Configuration digest captured.
- Provider summary captured safely.

### Security evidence

- Secret-injection test results.
- Prohibited object boundary results.
- Absolute-path sanitization result.
- External-network guard result.

### Metrics evidence

- Parent metrics.
- Network/community metrics.
- Topic metrics.
- Theme metrics.
- Explicitly unavailable/deferred metrics.

### Artifact evidence

- Logged artifact names.
- Size of each logged artifact.
- Proof raw datasets and full analytical CSVs were not logged.

### Failure behavior

- Tracking backend failure result.
- Analytical failure result.
- Parent and child terminal statuses.

### Tests

For every command:

```text
command
passed
failed
skipped
warnings
exit code
```

### Git verification

- `git diff --check`.
- `git show --check`.
- Commit file inventory.
- Detached-worktree result.
- Final clean status.

## 31. Progress Log

| Date | Update |
|---|---|
| 2026-07-14 | Created Plan 022 from verified Prefect baseline `5a08199e`; scoped the first MLflow phase to local experiment tracking and safe lineage only. |

### 2026-07-14 — implementation snapshot

- Added `src/tracking/` contracts, no-op and MLflow adapters, sanitization, summaries, and factory.
- Integrated one parent run and optional network/community, Topic, and Theme child runs into `run_monthly_analysis_flow`.
- Added safe Git/DVC/dataset lineage, bounded JSON summaries, artifact-reference manifests, and reliable row-count metrics.
- Added warning-only MLflow failure handling and analytical-failure status propagation.
- Added local configuration, `make mlflow-ui`, CI tracking-extra installation, README operations, and unit/integration tests.
- Real MLflow SQLite adapter suite: 22 passed.
- Focused orchestration/tracking suite with a synchronous Prefect-compatible harness: 102 passed.
- Authoritative `uv lock`, full `make test`, real-Prefect integration execution, and detached-worktree verification remain local-repository gates because the uploaded snapshot omitted repository modules used by the full suite and the sandbox package gateway could not complete universal lock resolution.

## 32. Decision Log

| Date | Decision | Reason |
|---|---|---|
| 2026-07-14 | Use explicit local SQLite MLflow backend and file artifact root. | The repository is local-only and currently executes sequentially; explicit configuration avoids relying on changing MLflow defaults. |
| 2026-07-14 | Disable tracking by default. | Preserves existing behavior and makes MLflow an additive capability. |
| 2026-07-14 | Use explicit client operations rather than shared active-run contexts. | Prevents thread-local/global state from leaking across Prefect task boundaries. |
| 2026-07-14 | Create one parent run and optional stage child runs. | Provides run-level comparison while retaining stage-level diagnostics. |
| 2026-07-14 | Log references and small summaries, not analytical datasets. | DVC and existing output directories remain the source of truth for large files. |
| 2026-07-14 | Use warning-only tracking failure policy. | Observability failure must not invalidate otherwise successful thesis analysis. |
| 2026-07-14 | Defer registry, serving, remote server, and tracing. | Keeps the milestone focused, reviewable, and appropriate for a local thesis repository. |

- **Client dependency:** use `mlflow-skinny==3.14.0` for tracked pipeline execution; launch the full pinned MLflow UI on demand with `uvx --from mlflow==3.14.0`.
- **Metrics:** log only values derivable from typed artifact metadata and validated CSV row counts; unavailable algorithm/provider runtime metrics are omitted rather than filled with invented zeros.
- **DVC revision:** accept an explicit revision and, when an adjacent `.dvc` pointer exists, default the revision to the verified Git commit for the pointer state.

## 33. Official Documentation Basis

Implementation must be checked against current official documentation for:

- MLflow Tracking APIs.
- MLflow parent and child runs.
- MLflow local database tracking.
- MLflow backend and artifact-store architecture.
- MLflow tracking server and local SDK behavior.
- Prefect flows, tasks, results, and logging.
- DVC dataset versioning and pointer metadata.

Do not copy example defaults blindly. Validate behavior against the exact locked MLflow and Prefect versions used by the repository.
