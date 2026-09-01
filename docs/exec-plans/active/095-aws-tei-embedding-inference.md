# Plan 095 — AWS TEI Embedding Inference (ARM64 Fargate)

## 1. Objective & Scope

Implement a production-grade, additive AWS Batch job definition for real Text Embeddings Inference (TEI) on AWS Fargate ARM64. The workload executes a multi-container task consisting of the primary analytical container alongside two dedicated TEI sidecars (similarity on port 8080, clustering on port 8081) communicating strictly over `localhost`. The existing Plan 094 mock/offline analytical Batch job remains completely intact and operational.

**STRICT DEPLOYMENT GATE**: This iteration covers implementation design, execution plan remediation, and local verification planning ONLY.
- **NO AWS resources will be modified, created, or deleted.**
- **NO Docker images will be pushed to remote ECR.**
- **NO AWS Batch jobs will be submitted.**
- **NO git commits or pushes will be performed.**
- **All changes remain local until explicit human review and authorization.**

---

## 2. Mandatory Documentation Review Evidence

The repository documentation was read and verified in the exact required sequence:
1. `HARNESS.md` — Affirmed production pipeline principles, non-negotiable metric baselines, and test gates.
2. `ARCHITECTURE.md` — Verified module structure, CLI entry point, Prefect orchestration, and read-only API boundaries.
3. `docs/design-docs/current-code-feature-inventory.md` — Confirmed full inventory of thesis and modern production additions.
4. `docs/product-specs/project-spec.md` — Confirmed user stories, functional requirements, and strict out-of-scope boundaries.
5. `docs/design-docs/data-contract.md` — Confirmed entity models, relationship schemas, and graph export shapes.
6. `docs/design-docs/database-contract.md` — Confirmed `GRAPH_DB_*` environment-only contract and Memgraph default.
7. `docs/design-docs/metric-contract.md` — Confirmed `shared_post` and `weighted_post` formulas and self-spread exclusions.
8. `docs/design-docs/pipeline-contract.md` — Confirmed end-to-end pipeline stages: ingestion → network → topic → theme → evolution.
9. `docs/design-docs/theme-intelligence-contract.md` — Confirmed Stage A HDBSCAN (contract 3.0), Stage B canonicalization (contract 4.0), and TEI embedding profiles.
10. `docs/verification/quality-gates.md` — Confirmed verification gates 1 through 10.
11. `docs/verification/test-matrix.md` — Confirmed test requirements by module and no-network unit test rules.
12. `docs/exec-plans/active/094-aws-batch-analytical-compute.md` — Confirmed accepted Plan 094 AWS Batch architecture, nested manifest publication, and Fargate spot/on-demand queue structure.
13. `docs/exec-plans/active/095-aws-tei-embedding-inference.md` — Current execution plan being amended.

---

## 3. Discovered TEI Contract from Current Source

The current TEI contract was inspected directly from repository code and configuration:

| Contract Property | Similarity Profile | Clustering Profile | Source Reference |
|---|---|---|---|
| **Model Identity** | `sentence-transformers/paraphrase-MiniLM-L6-v2` | `sentence-transformers/all-MiniLM-L6-v2` | `src/config/settings.py:7,9`, `configs/algorithms.yml:37,41` |
| **Model Revision Pin** | `c9a2bfebc254878aee8c3aca9e6844d5bbb102d1` | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | `src/config/settings.py:8,10`, `configs/algorithms.yml:38,42`, `scripts/start_tei.sh:20,21` |
| **Port (Localhost)** | `8080` | `8081` | `src/config/settings.py:33,75`, `scripts/start_tei.sh:16,17`, `.env.example:64,79` |
| **Provider Flag** | `THEME_SIMILARITY_PROVIDER=tei` | `THEME_CLUSTERING_PROVIDER=tei` | `src/config/settings.py:92,104`, `configs/algorithms.yml:40`, `.env.example:88,89` |
| **Config / YAML Keys** | `theme.similarity_model`, `theme.similarity_model_revision` | `theme.clustering_provider`, `theme.clustering_model`, `theme.clustering_model_revision` | `configs/algorithms.yml:37-42` |
| **Env Aliases** | `TEI_SIMILARITY_BASE_URL`, `TEI_BASE_URL` | `TEI_CLUSTERING_BASE_URL` | `src/config/settings.py:34,75` |
| **Client Batch Size** | `32` (`TEI_SIMILARITY_CLIENT_BATCH_SIZE`, `TEI_CLIENT_BATCH_SIZE`) | `32` (`TEI_CLUSTERING_CLIENT_BATCH_SIZE`) | `src/config/settings.py:44,77` |
| **Timeout Seconds** | `60.0` (`TEI_SIMILARITY_TIMEOUT_SECONDS`, `TEI_TIMEOUT_SECONDS`) | `60.0` (`TEI_CLUSTERING_TIMEOUT_SECONDS`) | `src/config/settings.py:51,78` |
| **Normalization** | `normalize=True` in TEI client request | `normalize=False` in TEI client request | `src/themes/theme_similarity.py:68`, `src/themes/theme_clustering.py:104` |
| **Downstream Norm** | Downstream cosine similarity heatmaps consume unit vectors | Downstream Stage A applies in-memory float64 L2 norm for HDBSCAN; raw vectors saved for medoids/Stage B | `docs/design-docs/theme-intelligence-contract.md:286-291`, `src/themes/theme_clustering.py:365` |
| **Output Dimension** | `384` | `384` | `src/themes/theme_similarity.py:70`, `src/themes/tei_health.py` |
| **Failure Policy** | `fail` (`THEME_SIMILARITY_FAILURE_POLICY=fail`) | Fail-fast (`ValueError` / `RuntimeError`) | `src/config/settings.py:105`, `src/themes/theme_similarity.py:106-110` |
| **Auth / API Key** | Optional Bearer token via `TEI_SIMILARITY_API_KEY` or `TEI_API_KEY` | Optional Bearer token via `TEI_CLUSTERING_API_KEY` | `src/config/settings.py:38,76`, `src/themes/tei_client.py:26` |
| **Readiness Check** | `POST /embed` with `{"inputs": ["health check"], "normalize": true}` | `POST /embed` with `{"inputs": ["health check"], "normalize": false}` | `src/themes/tei_health.py:7-40`, `scripts/check_tei.py:8-12` |

---

## 4. Model Revision Provenance

Both proposed revision pins are **already established production contracts** within the repository. Neither hash is newly invented:

1. **Similarity Model Revision** (`c9a2bfebc254878aee8c3aca9e6844d5bbb102d1`):
   - `src/config/settings.py:8`: `DEFAULT_SIMILARITY_MODEL_REVISION = "c9a2bfebc254878aee8c3aca9e6844d5bbb102d1"`
   - `configs/algorithms.yml:38`: `similarity_model_revision: c9a2bfebc254878aee8c3aca9e6844d5bbb102d1`
   - `scripts/start_tei.sh:20`: `SIMILARITY_REVISION=${TEI_SIMILARITY_REVISION:-c9a2bfebc254878aee8c3aca9e6844d5bbb102d1}`
   - `tests/unit/test_start_tei.sh:40, 66`: Verified in automated shell test suite.
   - `frontend/src/pages/__tests__/CommunityEvolution.test.jsx:40`: Verified in dashboard test fixtures.
   - `scripts/build_dashboard_fixture.py:742, 775`: Used for immutable test fixture generation.
   - **Provenance Status**: **CURRENT ESTABLISHED CONTRACT**.

2. **Clustering Model Revision** (`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`):
   - `src/config/settings.py:10`: `DEFAULT_CLUSTERING_MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"`
   - `configs/algorithms.yml:42`: `clustering_model_revision: 1110a243fdf4706b3f48f1d95db1a4f5529b4d41`
   - `scripts/start_tei.sh:21`: `CLUSTERING_REVISION=${TEI_CLUSTERING_REVISION:-1110a243fdf4706b3f48f1d95db1a4f5529b4d41}`
   - `tests/unit/test_start_tei.sh:44, 67`: Verified in automated shell test suite.
   - **Provenance Status**: **CURRENT ESTABLISHED CONTRACT**.

No new revision hashes are introduced.

---

## 5. Explicit TEI Batch Config Wiring

In the new TEI Batch Job Definition (`community-analysis-<stage>-analytics-tei-job`), the analytics container receives explicit environment variables directing embedding traffic to localhost sidecars while preserving existing application defaults:

```python
environment={
    # Storage & logging configuration (Plan 094 preserved)
    "COMMUNITY_ANALYSIS_STORAGE_BACKEND": "s3",
    "COMMUNITY_ANALYSIS_S3_BUCKET": bucket.bucket_name,
    "LOG_FORMAT": "json",
    "LOG_LEVEL": "INFO",
    # Select real TEI providers instead of mock
    "THEME_SIMILARITY_PROVIDER": "tei",
    "THEME_CLUSTERING_PROVIDER": "tei",
    "THEME_SIMILARITY_FAILURE_POLICY": "fail",
    # Point embedding requests to localhost sidecar ports
    "TEI_SIMILARITY_BASE_URL": "http://127.0.0.1:8080",
    "TEI_CLUSTERING_BASE_URL": "http://127.0.0.1:8081",
    # Client timeouts and batching
    "TEI_SIMILARITY_CLIENT_BATCH_SIZE": "32",
    "TEI_CLUSTERING_CLIENT_BATCH_SIZE": "32",
    "TEI_SIMILARITY_TIMEOUT_SECONDS": "60.0",
    "TEI_CLUSTERING_TIMEOUT_SECONDS": "60.0",
}
```

- **Isolation from Mock Job**: The existing single-container Batch job (`community-analysis-<stage>-analytics-job`) does NOT receive these TEI environment variables. It retains its clean environment, running `--theme-provider mock` without TEI containers or network dependencies.
- **No Algorithm Hardcoding**: URLs are injected entirely through standard Pydantic settings (`TEI_SIMILARITY_BASE_URL`, `TEI_CLUSTERING_BASE_URL`). No analytical code in `src/themes/` contains hardcoded endpoints.

---

## 6. Preservation of Accepted Plan 094 Runtime Contract

The new TEI job definition is purely additive and preserves the entire Plan 094 operational foundation:
- **Container Images and Distinct Tags**:
  - Existing Plan 094 single-container job: `community-analysis-<stage>-analytics:<BATCH_IMAGE_TAG>`
  - Plan 095 multi-container job / `analytics` container: `community-analysis-<stage>-analytics:<TEI_ANALYTICS_IMAGE_TAG>`
  - Plan 095 multi-container job / TEI sidecars: `community-analysis-<stage>-tei:<TEI_IMAGE_TAG>`
- **Compute Architecture**: ARM64 Linux on AWS Fargate.
- **Networking**: Dedicated 2-AZ Batch VPC, public subnets only, **0 NAT Gateways**, `assign_public_ip="ENABLED"`, egress-only security group.
- **Compute Environment**: Shared existing prioritized job queue backed by `FARGATE_SPOT` (order 1) and `FARGATE` (order 2) compute environments (`maxv_cpus=16`, scale-to-zero).
- **IAM Roles**: Scoped `execution_role` (ECR pull, CloudWatch logging) and scoped `job_role` (S3 get/put restricted to application bucket only).
- **Ephemeral Storage**: 30 GiB task ephemeral storage.
- **Timeouts & Retries**: 7200-second attempt duration (2 hours), 2 retry attempts.
- **Artifact Publication**: S3 upload preserves intermediate canonical artifacts (including nested `manifest.json` files), verifies manifest status, and uploads the top-level `runs/<run_id>/manifest.json` strictly last as the immutable completion marker.

---

## 7. Container Logging Architecture

All three containers stream structured JSON logs to the existing CloudWatch Log Group:
- **Log Group**: `self.log_group` (`/aws/batch/job/{project_name}-{stage_name}`)
- **Retention**: 1 week for `dev`, 1 month for `prod`.
- **Stream Prefix Strategy**:
  - `analytics` container logs to stream prefix `analytics`
  - `tei-similarity` container logs to stream prefix `tei-similarity`
  - `tei-clustering` container logs to stream prefix `tei-clustering`
- **Permissions**: Log group write access is provided via `BatchExecutionRole` attaching `AmazonECSTaskExecutionRolePolicy`. No broad logging permissions are granted.

---

## 8. Container Lifecycle & Shutdown Semantics

The multi-container Fargate task defines:
1. `analytics`: `essential: true`
2. `tei-similarity`: `essential: false`
3. `tei-clustering`: `essential: false`
4. Container Dependency: `analytics` has `depends_on`:
   - `tei-similarity` with condition `START`
   - `tei-clustering` with condition `START`

### Lifecycle Justification & Exit Guarantees
- **Startup Ordering**: AWS Batch/ECS starts `tei-similarity` and `tei-clustering` before initializing `analytics`.
- **Application Readiness Gate**: Because `START` indicates only that the sidecar container process has started (not that model weights are loaded and HTTP is accepting connections), `batch_runner` executes `wait_for_tei_services()` immediately upon boot. It polls `http://127.0.0.1:8080/embed` and `http://127.0.0.1:8081/embed` with bounded retries (30 attempts, 1.0s interval, 5.0s timeout). If either service fails to become healthy, `batch_runner` raises `RuntimeError` and terminates with exit code 1.
- **Sidecar Crash During Inference**: If either sidecar exits or crashes during pipeline execution, any subsequent HTTP inference request fails immediately. `THEME_SIMILARITY_FAILURE_POLICY=fail` and the clustering provider raise unhandled exceptions. `batch_runner` catches the failure, logs the exception, and terminates with exit code 1. It never falls back to mock embeddings.
- **Normal Task Completion**: When `analytics` finishes successfully (exit code 0), ECS recognizes that the sole essential container has stopped and stops all other containers in the task. It delivers SIGTERM to `tei-similarity` and `tei-clustering`. Because the sidecars are `essential: false`, their stopping (exit code 143) does NOT mark the Batch task as failed. The job finishes with status `SUCCEEDED` (exit code 0).
- **Failure Task Completion**: If `analytics` exits with non-zero code (due to pipeline failure or TEI error), the job finishes with status `FAILED`.

---

## 9. Fail-Closed Guarantees

A run configured for real TEI must **never silently produce mock embeddings or publish partial runs**:
1. **Startup Check**: `wait_for_tei_services()` executes before any pipeline stages run. If TEI is unreachable, the job fails closed immediately.
2. **Inference Check**: `src/themes/theme_similarity.py` enforces `THEME_SIMILARITY_FAILURE_POLICY=fail`, raising `RuntimeError` on TEI connection errors. `src/themes/theme_clustering.py` raises `RuntimeError` on any HTTP status other than 200.
3. **Publication Guard**: If an exception occurs, execution exits before `publish_completed_run_to_s3()`. The top-level `manifest.json` is never uploaded, preventing invalid runs from being served by the API.
4. **Decoupled Mock-GPT and Real-TEI Embedding Behavior**:
   - `THEME_PROVIDER` controls GPT/theme generation.
   - `THEME_SIMILARITY_PROVIDER` independently controls similarity embeddings.
   - `THEME_CLUSTERING_PROVIDER` independently controls clustering embeddings.
   - Plan 094 offline/mock execution has no explicit embedding-provider TEI overrides, so both embedding profiles remain mock and `wait_for_tei_services()` has nothing to check.
   - Plan 095 acceptance intentionally uses:
     - `THEME_PROVIDER=mock`
     - `THEME_SIMILARITY_PROVIDER=tei`
     - `THEME_CLUSTERING_PROVIDER=tei`
   - Therefore GPT remains mock while real TEI readiness checks and embeddings still execute.
   - No silent fallback from TEI to mock is permitted.

---

## 10. Deterministic TEI Container Packaging

File: `Dockerfile.tei`
- **Base Image**: Official TEI ARM64 CPU image pinned by immutable commit and index digest:
  `ghcr.io/huggingface/text-embeddings-inference:cpu-arm64-sha-cc7ca31@sha256:06749852e5edb64a6147e9db5bd1e92c5fb1119a2fe0cb92ce5e313d046d10cd`
  (Direct Linux ARM64 manifest digest: `sha256:46c8f0502c96ae6db8d89cd9299775941a388e706c3e20cfc552bb781038d867`).
- **Builder Stage Dependency Pin**:
  `pip install --no-cache-dir "huggingface_hub==0.29.0"`
  Pinned to exact verified version `0.29.0` to avoid floating dependency drift and ensure deterministic snapshot download behavior.
- **Build-Time Source**: In the model-fetcher builder stage, models are downloaded using `snapshot_download`:
  - `sentence-transformers/paraphrase-MiniLM-L6-v2` at pinned revision `c9a2bfebc254878aee8c3aca9e6844d5bbb102d1`
  - `sentence-transformers/all-MiniLM-L6-v2` at pinned revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`
- **Final Materialized Runtime Paths**:
  - `/models/similarity`
  - `/models/clustering`
  Downloaded snapshots are copied using `shutil.copytree(..., symlinks=False)` so the final image contains fully materialized model files without symlink dependencies.
- **Runtime TEI Commands**:
  - Similarity container: `--model-id /models/similarity --port 8080`
  - Clustering container: `--model-id /models/clustering --port 8081`
  The runtime commands intentionally contain NO Hugging Face repository IDs or revisions. The final image does not store runtime models under `/data` and does not rely on `HUGGINGFACE_HUB_CACHE=/data` or `HF_HOME=/data`.
- **Offline Startup**: Offline baked-model startup was verified with runtime networking disabled.

---

## 11. IAM and Security Architecture

- **Task-Level Role & Shared Boundary**:
  - The AWS Batch `taskRoleArn` is attached at the ECS task level, not independently per container. Consequently, the analytics container and TEI sidecars execute inside the same task IAM trust boundary.
  - The existing narrowly scoped Plan 094 task/job role (`BatchJobRole`) is preserved without modification (S3 Get/Put/List on the application bucket only).
  - TEI introduces **no additional task-role permissions**, **no TEI-specific IAM grants**, and **no broad S3 permissions**.
  - No Secrets Manager or SSM permissions are added for TEI.
  - TEI does not require AWS SDK/API access for its normal operation (purely HTTP on `localhost`).
  - This shared task-role boundary is an accepted tradeoff of the same-task sidecar architecture. A separate ECS service or separate task is NOT introduced solely to isolate IAM, as that would add unnecessary fixed cost, lifecycle complexity, service discovery, and operational scope.
- **Network Isolation**:
  - No public ports exposed for TEI (no `EXPOSE` or inbound security group ingress rules).
  - No ALB, NLB, Cloud Map, or ECS Service.
  - All communication occurs strictly over `127.0.0.1` inside the single Fargate task.
- **Authentication**:
  - No localhost API key required. Optional `TEI_API_KEY` application support remains intact if configured via environment.

---

## 12. Resource Sizing Rationale

### Aggregate Task Shape
- **CPU**: 8 vCPU (8192 units)
- **RAM**: 24 GiB (24576 MiB)
- **Ephemeral Storage**: 30 GiB

### Container Allocation Breakdown
| Container | vCPU | RAM | Rationale |
|---|---|---|---|
| `analytics` | 4 vCPU | 16 GiB (16384 MiB) | Preserves accepted Plan 094 allocation for pandas/NetworkX/LDA multiprocessing. |
| `tei-similarity` | 2 vCPU | 4 GiB (4096 MiB) | MiniLM-L6 (~90MB model). 2 vCPUs provides fast CPU tokenization and batch inference. |
| `tei-clustering` | 2 vCPU | 4 GiB (4096 MiB) | MiniLM-L6 (~90MB model). 2 vCPUs ensures fast unnormalized embedding generation. |

### Fargate Allocation Rationale
AWS Fargate does not support arbitrary vCPU counts (valid tiers: 0.25, 0.5, 1, 2, 4, 8, 16 vCPU). Because the analytics workload alone requires 4 vCPU, adding sidecars requires stepping up to the next valid Fargate allocation tier: **8 vCPU** (16–60 GiB RAM range). An 8 vCPU / 24 GiB task fits within the existing `maxv_cpus=16` Batch compute environments.
*Deployment Checklist Note*: AWS account Fargate vCPU service quota must be verified prior to live deployment to ensure concurrent 8 vCPU capacity.

---

## 13. Test Matrix (Actual Implemented Verifications)

The test suite verifies all Plan 095 architectural, runtime, and failure-mode requirements with actual implemented tests:

1. **Existing Single-Container Batch Job Exists & Retains Properties**: `test_fargate_job_definition` confirms the single-container `AnalyticsJobDefinition` remains in the synthesized template with 4 vCPU, 16 GiB RAM, 30 GiB ephemeral storage, ARM64 Linux, 7200s timeout, 2 retries, and scoped environment variables.
2. **TEI Batch Job Multi-Container Definition**: `test_fargate_tei_multi_container_job_definition` asserts `community-analysis-<stage>-analytics-tei-job` has exactly 3 containers (`analytics`, `tei-similarity`, `tei-clustering`) with `analytics` depending on both sidecars with condition `START`.
3. **ARM64 Fargate Runtime Platform**: `test_fargate_job_definition` and `test_fargate_tei_multi_container_job_definition` assert `RuntimePlatform` has `CpuArchitecture: ARM64` and `OperatingSystemFamily: LINUX`.
4. **Correct Ports & Local Paths**: Asserts `tei-similarity` runs on port 8080 with `--model-id /models/similarity` and `tei-clustering` on port 8081 with `--model-id /models/clustering`. Runtime commands contain only local model paths; model identity and revision provenance (`c9a2bfebc254878aee8c3aca9e6844d5bbb102d1` and `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`) are enforced at build time via `Dockerfile.tei` pins, OCI labels, and image environment metadata.
5. **Decoupled Image Tag Wiring**: `test_distinct_image_tag_wiring_in_batch_stack` verifies `AnalyticsJobDefinition` uses `batch_image_tag`, `AnalyticsTeiJobDefinition`'s `analytics` container uses `tei_analytics_image_tag`, and TEI sidecars use `tei_image_tag`.
6. **Strict Validation on Missing Tags**: `test_batch_stack_fails_when_plan095_tags_missing` asserts omitting `tei_analytics_image_tag` or `tei_image_tag` raises `ValueError`.
7. **Localhost Configuration Wiring**: Asserts `analytics` container receives `TEI_SIMILARITY_BASE_URL: http://127.0.0.1:8080` and `TEI_CLUSTERING_BASE_URL: http://127.0.0.1:8081`.
8. **Provider Environment Precedence**: `test_batch_runner_explicit_env_embedding_providers_override_yaml_mock` verifies explicit environment variables `THEME_SIMILARITY_PROVIDER=tei` and `THEME_CLUSTERING_PROVIDER=tei` override YAML mock settings.
9. **Plan 094 Mock Config Preservation**: `test_batch_runner_plan094_config_remains_mock_without_embedding_env` verifies configs without embedding environment overrides retain mock providers.
10. **TEI Embedder Builder Resolution**: `test_batch_runner_config_resolves_to_tei_embedders` verifies production builders instantiate `TEIClient` when configured for TEI, and offline embedders when mock.
11. **Zero NAT Gateways**: `test_batch_vpc` asserts `NatGatewayCount: 0` in Batch VPC across all stages.
12. **Zero Inbound Security Group Ingress**: `test_batch_security_group` asserts Batch security group has no ingress rules.
13. **No ECS Service / ALB / Cloud Map**: Asserts template contains 0 `AWS::ECS::Service`, 0 `AWS::ElasticLoadBalancingV2::LoadBalancer`, and 0 `AWS::ServiceDiscovery::Service`.
14. **Scoped Job Role**: Asserts `BatchJobRole` policy grants only bucket-scoped S3 permissions.
15. **Preserved Scoped Task Role Boundary**: Asserts the task role policy contains no new TEI-specific grants, no Secrets Manager or SSM permissions, no wildcard actions, and preserves the existing narrowly scoped Plan 094 S3 policy.
16. **CloudWatch Logging for All Containers**: Asserts `analytics`, `tei-similarity`, and `tei-clustering` stream prefixes write to the shared log group.
17. **Preserved Timeout & Retries**: Asserts 7200s timeout and 2 retries on both job definitions.
18. **Preserved Ephemeral Storage**: Asserts 30 GiB ephemeral storage on both job definitions.
19. **Protected Manifest-Last Publication**: Unit tests in `test_batch_runner.py` assert manifest-last publication and nested manifest preservation.
20. **TEI Readiness Gating & Fail-Closed Timeout**: `test_wait_for_tei_services_timeout` in `test_tei_health.py` and `test_run_batch_job_fails_fast_on_tei_timeout` in `test_batch_runner.py` assert health check failure raises `RuntimeError` and exits with code 1.
21. **Automated Tests Do Not Contact External Services**: Asserts mock unit tests run with offline embedders and zero network calls to OpenAI or remote Hugging Face APIs.

---

## 14. Implemented Local TEI Compatibility Validation

Validation is implemented in `scripts/check_tei_compat.py` and executed via `make tei-compat-smoke`:
1. **Docker Prerequisite**: Requires a reachable local Docker daemon (`docker info`).
2. **Container Startup**:
   - Starts one similarity TEI container on port 8080 using `--model-id /models/similarity --port 8080`.
   - Starts one clustering TEI container on port 8081 using `--model-id /models/clustering --port 8081`.
3. **Readiness Gate**: Waits for both services to report ready via `wait_for_tei_services()`.
4. **Embedding Generation**:
   - Sends two representative texts to similarity `TEIClient(base_url="http://127.0.0.1:8080", normalize=True)`.
   - Sends two representative texts to clustering `TEIClient(base_url="http://127.0.0.1:8081", normalize=False)`.
5. **Contract-Based Assertions**:
   - **Similarity TEI**:
     - Verifies shape `(2, 384)` with all finite float values.
     - Verifies `normalize=True` yields unit vectors (L2 norm == 1.0 within numerical tolerance).
     - Checks similarity embeddings through `cosine_similarity`, confirming a valid `(2, 2)` finite matrix.
   - **Clustering TEI**:
     - Verifies shape `(2, 384)` with all finite float values and unnormalized raw output.
     - Verifies Stage A compatibility by feeding clustering embeddings through `_l2_normalize_embeddings` (yielding float64 unit vectors) and `_fit_hdbscan` (`min_cluster_size=2`, `metric="euclidean"`, `cluster_selection_method="leaf"`).
     - Verifies Stage B algorithm compatibility by fitting `AgglomerativeClustering` using the contract constants (`metric="cosine"`, `linkage="complete"`, `distance_threshold=0.65`).
6. **Guaranteed Cleanup**: Cleans up both containers in a `finally` block across all execution paths.

---

## 15. Plan 094 Regression Validation

To guarantee zero regression of the accepted Plan 094 analytical pipeline:
- **Accepted Container Sample Workflow**:
  ```bash
  make analytics-image-sample
  ```
  *(Builds `Dockerfile.analytics` and executes deterministic sample inside container with `-e THEME_PROVIDER=mock --config tests/configs/test_evolution.yml --skip-s3-download --skip-s3-upload`, verifying all 60 canonical artifacts).*
- **Targeted Unit Regression Tests**:
  ```bash
  uv run --frozen --extra orchestration --extra tracking python -m pytest tests/unit/test_batch_runner.py
  ```
- **Verification Criteria**:
  - Offline/mock analytical path functions cleanly.
  - TEI is not contacted.
  - OpenAI is not contacted.
  - Canonical artifact behavior remains unchanged.
  - Nested `manifest.json` files remain preserved.
  - Top-level manifest-last publication behavior remains unchanged.
  - Local/container validation only (no AWS acceptance rerun).

---

## 16. Validation Execution Order

When approved for implementation, validation must be executed in this exact sequence:
1. Targeted TEI/provider unit tests: `uv run pytest tests/unit/test_tei_client.py`
2. Targeted TEI readiness tests: `uv run pytest tests/unit/test_tei_health.py`
3. Targeted batch runner tests: `uv run pytest tests/unit/test_batch_runner.py`
4. Targeted CDK Batch stack tests: `cd infra && uv run pytest tests/test_batch_stack.py`
5. Theme clustering and similarity tests: `uv run pytest tests/unit/test_theme_clustering.py tests/unit/test_theme_similarity.py`
6. Full infrastructure test suite: `cd infra && uv run pytest`
7. Local TEI image build: `make tei-image-build`
8. Local two-model TEI compatibility smoke: `make tei-compat-smoke` (via `scripts/check_tei_compat.py`)
9. Plan 094 offline/mock regression sample: `make analytics-image-sample`
10. Targeted code formatting/linting on Plan 095 files: `uv run pre-commit run --files ...`
11. Whitespace and syntax verification: `git diff --check`
12. Targeted unit and infrastructure test suites: `uv run pytest tests/unit/test_tei_client.py tests/unit/test_tei_health.py tests/unit/test_batch_runner.py` and `make infra-test`
13. CDK synth for `dev`:
    ```bash
    make infra-synth \
      INFRA_STAGE=dev \
      IMAGE_TAG=94fa3081 \
      BATCH_IMAGE_TAG=3adeb1fd \
      TEI_ANALYTICS_IMAGE_TAG=plan095-analytics-review \
      TEI_IMAGE_TAG=plan095-tei-review
    ```
14. CDK synth for `prod`:
    ```bash
    make infra-synth \
      INFRA_STAGE=prod \
      IMAGE_TAG=94fa3081 \
      BATCH_IMAGE_TAG=3adeb1fd \
      TEI_ANALYTICS_IMAGE_TAG=plan095-analytics-review \
      TEI_IMAGE_TAG=plan095-tei-review
    ```
15. Read-only CDK diff:
    ```bash
    make infra-diff-batch \
      INFRA_STAGE=dev \
      IMAGE_TAG=94fa3081 \
      BATCH_IMAGE_TAG=3adeb1fd \
      TEI_ANALYTICS_IMAGE_TAG=plan095-analytics-review \
      TEI_IMAGE_TAG=plan095-tei-review
    ```

---

## 17. Non-Negotiable Analytical Constraints (FROZEN)

- **Metrics**: `shared_post` and `weighted_post` formulas preserved.
- **Graph Thresholds**: `min_total_post=10`, `min_shared_post=5`.
- **Louvain Defaults**: `resolution=1.0`, `seed=123`.
- **LDA Defaults**: `num_topics=15`, `random_state=100`, `iterations=100`, `chunksize=20`, `passes=80`, `alpha='auto'`, `eta='auto'`.
- **Stage A**: `all-MiniLM-L6-v2`, raw TEI embeddings, downstream L2 normalization, Euclidean HDBSCAN (`leaf`, `min_cluster_size=2`, `min_samples=3`, `allow_single_cluster=False`).
- **Stage B**: Raw TEI embeddings, downstream L2 normalization, complete-linkage agglomerative clustering (`metric="cosine"`, `threshold=0.65`, contract v4.0).
- **Run Manifest**: Top-level manifest uploaded strictly last and exactly once. Nested manifests preserved.

---

## 18. Strict Non-Goals (No Scope Creep)
- No Memgraph deployment to AWS.
- No GitHub Actions CI/CD workflows.
- No OIDC / IAM identity provider configuration.
- No ECS Services, ALBs, NLBs, Cloud Map, or Kubernetes/EKS.
- No GPU compute environments.
- No new orchestration engines.
- No frontend or backend API modifications.

---

## 20. Future Deployment and Acceptance Run Specification (NOT EXECUTED)

- **Why a Distinct Plan 095 Analytics Image Is Required**:
  - The Plan 095 multi-container TEI job requires a newly built analytics container image from `Dockerfile.analytics` because Plan 095 modifies runtime Python code (`src/cloud/batch_runner.py` and `src/themes/tei_health.py`) for TEI health readiness polling, fail-closed timeouts, and explicit operator embedding-provider environment precedence.
  - The accepted Plan 094 deployment image tag (`3adeb1fd`) in `community-analysis-dev-analytics` does NOT contain these changes and must remain pinned to the existing single-container `community-analysis-dev-analytics-job` to guarantee zero Plan 094 regression.
  - Therefore, Plan 095 uses three explicit, decoupled image tag variables:
    - `BATCH_IMAGE_TAG`: Pinned immutable tag for existing Plan 094 single-container `AnalyticsJobDefinition` (`3adeb1fd`).
    - `TEI_ANALYTICS_IMAGE_TAG`: Immutable tag for the `analytics` container inside `AnalyticsTeiJobDefinition` (repository `community-analysis-dev-analytics`).
    - `TEI_IMAGE_TAG`: Immutable tag for the two TEI sidecars inside `AnalyticsTeiJobDefinition` (repository `community-analysis-dev-tei`).

- **Symbolic Target Names**:
  - AWS Registry: `<AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com`
  - Analytics Repository: `<AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/community-analysis-dev-analytics`
  - TEI Repository: `<AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/community-analysis-dev-tei`
  - Batch Queue: `community-analysis-dev-queue`
  - Batch Job Definition: `community-analysis-dev-analytics-tei-job`

- **Future Deployment Sequence (DOCUMENT ONLY — NOT EXECUTED)**:
  1. Human approves Plan 095 implementation and source diff.
  2. Create ONE clean Plan 095 commit.
  3. Capture new commit SHA: `PLAN095_SHA=$(git rev-parse HEAD)`.
  4. Build new analytics image: `docker build --platform linux/arm64 -t <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/community-analysis-dev-analytics:${PLAN095_SHA} -f Dockerfile.analytics .`
  5. Build new TEI image: `docker build --platform linux/arm64 -t <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/community-analysis-dev-tei:${PLAN095_SHA} -f Dockerfile.tei .`
  6. Authenticate Docker to ECR:
     ```bash
     aws ecr get-login-password \
       --region us-east-1 \
       --profile community-analysis-dev \
     | docker login \
       --username AWS \
       --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
     ```
  7. Push the new analytics image to the existing ECR repository: `docker push <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/community-analysis-dev-analytics:${PLAN095_SHA}`
  8. Deploy BatchStack with separate immutable tags:
     ```bash
     make infra-deploy-batch \
       INFRA_STAGE=dev \
       IMAGE_TAG=94fa3081 \
       BATCH_IMAGE_TAG=3adeb1fd \
       TEI_ANALYTICS_IMAGE_TAG=${PLAN095_SHA} \
       TEI_IMAGE_TAG=${PLAN095_SHA}
     ```
     *(This creates `TeiRepository` and `AnalyticsTeiJobDefinition` while keeping `AnalyticsJobDefinition` on `3adeb1fd`).*
  9. Push the new TEI image to the newly created ECR repository: `docker push <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/community-analysis-dev-tei:${PLAN095_SHA}`
  10. Read-only verify both image tags exist in ECR and verify job-definition references:
      - Plan 094 job still references `:3adeb1fd`;
      - Plan 095 analytics container references `:${PLAN095_SHA}`;
      - Both TEI sidecars reference `:${PLAN095_SHA}`.
  11. Submit exactly ONE bounded Plan 095 acceptance job.
  12. Verify run manifest, S3 outputs, Lambda API, and CloudFront frontend.
  13. Mark Plan 095 complete.

- **Selected Bounded Acceptance Configuration**:
  - Configuration: `tests/configs/test_evolution.yml`
  - Inputs: `tests/fixtures/longitudinal/twitter_reply_03_2017.csv` and `tests/fixtures/longitudinal/twitter_reply_04_2017.csv`
  - Rationale: Exercises full longitudinal Louvain, LDA, mock GPT theme generation, real TEI similarity (port 8080), real TEI HDBSCAN clustering (port 8081), complete-linkage canonicalization, transitions, and generates complete 60-canonical-artifact bundle in minimal runtime (~17s) without OpenAI API dependency.

- **Multi-Container Acceptance Submit Command (NOT EXECUTED)**:
  ```bash
  aws batch submit-job \
    --job-name "community-analysis-dev-p095-$(date +%Y%m%d%H%M%S)" \
    --job-queue "community-analysis-dev-queue" \
    --job-definition "community-analysis-dev-analytics-tei-job" \
    --region us-east-1 \
    --ecs-properties-override '{
      "taskProperties": [
        {
          "containers": [
            {
              "name": "analytics",
              "environment": [
                {"name": "CONFIG_PATH", "value": "tests/configs/test_evolution.yml"},
                {"name": "THEME_PROVIDER", "value": "mock"},
                {"name": "PIPELINE_COMMAND", "value": "run-evolution-pipeline"},
                {"name": "SKIP_S3_DOWNLOAD", "value": "true"}
              ]
            }
          ]
        }
      ]
    }'
  ```
  *(Overrides target ONLY container `analytics`. Pre-configured `THEME_SIMILARITY_PROVIDER=tei`, `THEME_CLUSTERING_PROVIDER=tei`, and sidecar port/model mappings are preserved. `SKIP_S3_UPLOAD` is intentionally omitted/false so canonical outputs are published to S3 for verification).*

---

## 21. Progress Log

- 2026-09-01: Discovered source of truth for TEI models, revisions, ports, and normalization semantics.
- 2026-09-01: Validated official TEI ARM64 CPU container image availability on GHCR (`cpu-arm64-sha-cc7ca31`).
- 2026-09-01: Offline baked-model startup was verified with runtime networking disabled.
- 2026-09-01: Formulated multi-container Fargate task sizing (8 vCPU / 24 GiB) and essential/non-essential container lifecycle.
- 2026-09-01: Completed mandatory documentation review (13 documents in exact sequence).
- 2026-09-01: Proved provenance of both model revision pins (`c9a2bfebc254878aee8c3aca9e6844d5bbb102d1` and `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`) as pre-existing repository contracts.
- 2026-09-01: Remediation pass 1: Added 21-point test matrix, explicit Batch environment wiring, fail-closed guarantees, and local compatibility smoke test design.
- 2026-09-01: Remediation pass 2: Corrected IAM model to reflect task-level role and shared task trust boundary; updated regression workflow to use existing accepted `make analytics-image-sample`; corrected false "Implemented" test wording to "Planned"; replaced brittle vector-norm assertion with contract checks; removed unsupported 1.2ms startup claim.
- 2026-09-01: Status: `IMPLEMENTED_LOCALLY_VERIFIED`.
- 2026-09-01: Built ARM64 TEI image with pinned models cached in `/data` via `Dockerfile.tei`.
- 2026-09-01: Added `wait_for_tei_services` in `src/themes/tei_health.py` with bounded readiness retries and fail-closed timeout.
- 2026-09-01: Updated `src/cloud/batch_runner.py` to preserve environment embedding providers when `THEME_PROVIDER=mock` and execute `wait_for_tei_services` prior to pipeline flow.
- 2026-09-01: Synthesized additive `AnalyticsTeiJobDefinition` (8 vCPU / 24 GiB RAM) and `TeiRepository` in `infra/community_analysis_infra/batch_stack.py` and wired in `infra/app.py`.
- 2026-09-01: Verification remediation pass: Removed Fargate-unsupported `ipc_mode="task"` from `AnalyticsTeiJobDefinition`; verified structurally that `IpcMode` and `PidMode` are absent from synthesized CloudFormation templates.
- 2026-09-01: Verification remediation pass: Proved `TeiRepository` lifecycle policy strictly expires untagged images after 1 day with no expiration rule for tagged immutable deployment images.
- 2026-09-01: Verification remediation pass: Reconciled accidental whitespace modifications in Plan 090 and 094 from `pre-commit` and restored exact byte-for-byte HEAD contents.
- 2026-09-01: Verification remediation pass: Independently verified offline `--network none` startup for both similarity and clustering baked models.
- 2026-09-01: Verification remediation pass: Integrated real Stage A (`_l2_normalize_embeddings` + `_fit_hdbscan`), Stage B (`AgglomerativeClustering`), and Theme Similarity (`cosine_similarity`) production consumer functions into `scripts/check_tei_compat.py`; validated complete pass.
- 2026-09-01: Verification remediation pass: Performed read-only AWS discovery of deployed Plan 094 analytics image tag (`3adeb1fd`) and Lambda image tag (`94fa3081`); generated exact-tag CDK diff demonstrating zero modifications to existing `AnalyticsJobDefinition`, queue, compute environments, VPC, or job role.
- 2026-09-01: Deterministic runtime remediation pass: Resolved deployment blocker where Batch sidecars used remote Hugging Face repository IDs. Updated `Dockerfile.tei` to materialize fully resolved, dereferenced models into `/models/similarity` and `/models/clustering` at build time with OCI labels and env metadata. Updated `AnalyticsTeiJobDefinition` in `infra/community_analysis_infra/batch_stack.py` and `scripts/check_tei_compat.py` to use local `/models/similarity` and `/models/clustering` paths without remote repository IDs.
- 2026-09-01: Deterministic runtime remediation pass: Proved both exact deployed sidecar commands reach Ready state offline under `--network none`.
- 2026-09-01: Pre-deployment corrections pass: Re-verified Fargate vCPU service quotas in us-east-1 (On-Demand: 30, Spot: 30; both sufficient for 8-vCPU task); sanitized documentation to use symbolic placeholders; defined multi-container `--ecs-properties-override` command targeting `analytics` container only; bounded acceptance to `tests/configs/test_evolution.yml`.
- 2026-09-01: Final source-review remediation pass: Fixed explicit embedding environment variables precedence in `src/cloud/batch_runner.py` so `THEME_SIMILARITY_PROVIDER` and `THEME_CLUSTERING_PROVIDER` override YAML mock values in `tests/configs/test_evolution.yml`; added unit regressions in `tests/unit/test_batch_runner.py` proving `test_evolution.yml` + explicit env overrides resolves to `TEIClient`, and without env overrides remains mock; corrected Batch queue name to `community-analysis-dev-queue`; corrected frozen LDA default to `alpha='auto'`; updated validation commands to use `make tei-compat-smoke` and targeted pre-commit; added `tei-image-build`, `tei-image-smoke`, and `tei-compat-smoke` to `.PHONY` and `help` in `Makefile`; removed self-testing acceptance-override dictionary test from `infra/tests/test_batch_stack.py`.
- 2026-09-01: Final image-wiring remediation pass: Decoupled Plan 095 analytics container image tag (`TEI_ANALYTICS_IMAGE_TAG` / `tei_analytics_image_tag`) from Plan 094 image tag (`BATCH_IMAGE_TAG`), ensuring the Plan 095 job runs newly built runtime code while keeping Plan 094 pinned to `3adeb1fd`; updated `BatchStack` and `app.py` with strict validation (no fallback); updated `Makefile` targets (`infra-diff-batch`, `infra-deploy-batch`); added CDK regression tests proving the three image identities are decoupled; verified local built image contains Plan 095 batch runner under non-networked container inspection; re-verified dev/prod synthesis and read-only CDK diff.
- 2026-09-01: Final operator-command cleanup pass: Updated Makefile `infra-list` to forward `TEI_ANALYTICS_IMAGE_TAG` and updated its usage text; updated documented synth and diff commands in validation section to preferred `make infra-synth` and `make infra-diff-batch` forms with explicit review tags; added explicit ECR authentication step before pushes to future deployment sequence; added `SKIP_S3_DOWNLOAD=true` to future acceptance submit override while ensuring `SKIP_S3_UPLOAD` remains false.
- 2026-09-01: Disclosed test suite status: Plan 095 targeted tests (27 unit tests, 71 infra tests, 4 manifest ordering tests, 32 clustering/similarity tests) all PASS; full `make test` reports 14 pre-existing/environmental failures unrelated to Plan 095.
- 2026-09-01: Verified `git diff --check` passes with zero errors; no commits, no pushes, and no AWS deployment performed. Ready for commit approval.
