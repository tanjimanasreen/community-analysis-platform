# Execution Plan 094: AWS Batch Analytical Compute

**Status**: in-progress
**Milestones**:
- [x] Pre-change verification (Git branch `dev`, clean working tree, HEAD at `b36dc50b`)
- [x] Verified canonical analytical CLI entry points and orchestration contracts (`run-evolution-pipeline` and `run-all`)
- [x] Implemented dedicated AWS Batch analytical container definition (`Dockerfile.analytics`) for ARM64 Graviton2 with bundled spaCy model
- [x] Implemented production Batch analytical wrapper in `src/cloud/batch_runner.py` with S3 sync, workspace redirection, manifest-last publication, and error boundaries
- [x] Added `boto3` direct dependency to `pyproject.toml` and updated `uv.lock`
- [x] Added unit tests for Batch runner wrapper in `tests/unit/test_batch_runner.py` (10 passing unit tests)
- [x] Implemented `BatchStack` in `infra/community_analysis_infra/batch_stack.py` with dedicated ECR (no explicit scan-on-push), 2-AZ public VPC (0 NAT Gateways), Fargate Spot & On-Demand compute environments (maxv_cpus=16), prioritized queue, and 4 vCPU / 16 GiB / 30 GiB ephemeral storage job definition (timeout 7200s, retry 2)
- [x] Added CDK infrastructure tests in `infra/tests/test_batch_stack.py` (66 passing infra unit tests)
- [x] Wired `BatchStack` into `infra/app.py` with isolated context (existing stacks synthesize without `batch_image_tag`)
- [x] Added Makefile targets for local analytics container build (`ANALYTICS_LOCAL_IMAGE`), smoke test, real sample run (`analytics-image-sample`), and Batch deployment tooling
- [x] Local validation across infra tests, batch runner tests, and CDK synthesis (dev & prod)
- [x] Container image build, smoke validation, and real sample execution verification
- [ ] Human review and approval
- [ ] Tagged image push and AWS deployment (future human steps)

---

## 1. Goal & Context

Plan 094 introduces scalable, isolated, scale-to-zero **AWS Batch analytical compute** for the existing heavy Python analytical pipeline (`src/` package). It establishes an asynchronous, offline execution layer on AWS Fargate (ARM64) that pulls inputs from S3, executes the unchanged thesis pipeline, verifies output manifest integrity, and publishes immutable run bundles to the Plan-089 S3 bucket (`s3://<bucket>/runs/<run_id>/`). Once published, the existing Plan-090/092 read-only Lambda API and Plan-093 CloudFront frontend automatically discover and serve the verified run artifacts without changes to serving code.

---

## 2. Verified Analytical Contracts

- **Primary Pipeline CLI**: `python -m src.cli run-evolution-pipeline --config <config_path>` (longitudinal multi-month runs) and `python -m src.cli run-all --config <config_path>` (single-month runs).
  - *Source Evidence*: `src/cli.py:194`, `src/cli.py:1052`, `src/orchestration/composition_flow.py:566`.
- **Input Paths**: Configured via YAML (`data/raw/**` or `${DATA_ROOT}/**`) mapping S3 `raw/` to local `<workspace>/data/raw/`.
  - *Source Evidence*: `configs/telegram/forwarded_message_evolution.yml:54`, `src/config/loader.py:32`.
- **Output Paths**: Canonical immutable run bundles output to `<workspace>/output/runs/<run_id>/` and validated against `output-artifact-contract.md`.
  - *Source Evidence*: `src/artifacts/run_manifest.py:36`, `docs/design-docs/output-artifact-contract.md:14`.
- **Run ID Generation**: Generated inside `src/orchestration/composition_flow.py` as a UUID v4 string (`pipeline_run_id`), binding all manifest records, intermediate handoffs, stage caches, and tracking tags.
  - *Source Evidence*: `src/orchestration/composition_flow.py:578`.
- **Offline / Mock Provider**: Deterministic offline embeddings via `DeterministicThemeEmbeddingModel` / `OfflineThemeEmbeddingModel`; zero OpenAI or live TEI calls during tests or offline executions.
  - *Source Evidence*: `src/themes/theme_clustering.py:79`, `src/themes/theme_similarity.py:34`.

---

## 3. Architecture & Infrastructure Design

### Compute & Networking Architecture
```text
Operator / Make
      ↓
AWS Batch Job Queue (Priority 1)
      ├── FARGATE_SPOT (Order 1, MaxvCpus=16)
      └── FARGATE      (Order 2, MaxvCpus=16)
            ↓
ARM64 Analytics Container (Dockerfile.analytics)
(4 vCPUs / 16 GiB RAM / 30 GiB Ephemeral Storage / AssignPublicIp=ENABLED)
            ↓
S3 Input (s3://<bucket>/raw/)
            ↓
Local Workspace (/app/workspace)
            ↓
Existing Analytical Pipeline (NetworkX, Louvain, Gensim, HDBSCAN, Agglomerative)
            ↓
Completed Run Bundle (runs/<run_id>/manifest.json + data/*.parquet)
            ↓
S3 Publication (s3://<bucket>/runs/<run_id>/)
            ↓
Discovered by Plan 092 Lambda API & Plan 093 CloudFront Frontend
```

### Key CDK Components (`BatchStack`)
1. **Analytics ECR Repository**: `community-analysis-<stage>-analytics` with tag immutability, AES-256 encryption, and 1-day untagged image expiry (no explicit `image_scan_on_push`).
2. **Dedicated VPC**: `community-analysis-<stage>-batch-vpc` with 2 AZs and public subnets only. **0 NAT Gateways** ($0.00 fixed monthly NAT cost).
3. **Security Group**: 0 inbound rules; outbound HTTPS/internet egress enabled.
4. **Compute Environments**: Fargate Spot (order 1) and Fargate On-Demand (order 2), strictly scale-to-zero (`maxv_cpus=16`, `minv_cpus` absent).
5. **Job Queue**: `community-analysis-<stage>-queue` (Priority 1).
6. **Job Definition**: `community-analysis-<stage>-analytics-job` on ARM64 Linux, 4 vCPUs, 16 GiB RAM, 30 GiB ephemeral storage, 7200s timeout (initial conservative operational upper bound; not an analytical expectation), 2 retry attempts.
7. **IAM Roles**:
   - Execution Role: ECR image pull + CloudWatch logs (`service-role/AmazonECSTaskExecutionRolePolicy`).
   - Job Role: Strictly scoped S3 read (`raw/*`, `cache/*`) and write (`runs/*`, `reports/*`, `cache/*`) on the Plan-089 bucket. `s3:ListBucket` granted on bucket ARN with prefix condition `StringLike` on `raw/*` and `cache/*`. Zero broad `s3:*` or `*` actions. No bucket-admin permissions (`s3:DeleteBucket`, `s3:PutBucketPolicy`, `s3:DeleteObject`).
8. **CloudWatch Log Group**: `/aws/batch/job/community-analysis-<stage>` with 7-day dev retention and 30-day prod retention.

### Image Variable Separation & Context Rules
- `API_LOCAL_IMAGE` (default `community-analysis-api:dev`): Local Docker tag name for API container build/smoke.
- `IMAGE_TAG` (NO default): Required immutable ECR/CDK tag for API deployment (`ApiStack`).
- `ANALYTICS_LOCAL_IMAGE` (default `community-analysis-analytics:dev`): Local Docker tag name for analytical container build/smoke/sample.
- `BATCH_IMAGE_TAG` (NO default): Required immutable ECR/CDK tag for Batch deployment (`BatchStack`).
- Root S3 prefixes frozen to: `raw/`, `cache/`, `runs/`, `reports/`. Arbitrary root prefixes unsupported. `configs/*` read access is not granted.

---

## 4. Container Strategy & Batch Wrapper

- **`Dockerfile.analytics`**:
  - Multi-stage build with `ghcr.io/astral-sh/uv:0.10.0` and `python:3.11-slim-bookworm`.
  - Full analytical dependencies installed (`orchestration`, `tracking`, `boto3`).
  - Pre-downloads spaCy `en_core_web_sm` model at build time.
  - Dedicated non-root user `community` (UID 10001) with writable `/app/workspace`.
  - Entrypoint: `ENTRYPOINT ["python", "-m", "src.cloud.batch_runner"]` with NO default `--help` CMD.
- **`src/cloud/batch_runner.py`**:
  - Validates Batch parameters and environment variables (`CONFIG_PATH`, `COMMUNITY_ANALYSIS_S3_BUCKET`, `WORKSPACE_DIR`, `THEME_PROVIDER`).
  - Downloads raw inputs from `s3://<bucket>/raw/` to `<workspace>/data/raw/`.
  - Downloads stage cache from `s3://<bucket>/cache/` to `<workspace>/output/.stage_cache/`.
  - Loads YAML configuration into memory and redirects `output_base_path` to `<workspace>/output` without mutating source config files.
  - Executes canonical pipeline flow (`run_evolution_analysis_flow` or `run_monthly_analysis_flow`).
  - Verifies completed `manifest.json` status before publishing.
  - Publishes artifacts to S3 with `manifest.json` uploaded **LAST**:
    1. Uploads all `runs/<run_id>/` artifacts *except* `manifest.json`
    2. Uploads updated `reports/` if present
    3. Uploads updated `cache/` if present
    4. Uploads `manifest.json` as the final completion marker
  - If any upload fails before `manifest.json`, the manifest is never uploaded and the job exits non-zero.

---

## 5. Non-Goals

- No TEI service deployment on ECS/EKS (deferred to Plan 095).
- No GPU compute environments (deferred to Plan 095).
- No Memgraph EC2/EBS infrastructure (deferred to Plan 096).
- No Step Functions state machines.
- No NAT Gateway or private subnet architecture ($0 fixed networking cost).
- No GitHub Actions / CI/CD pipeline (deferred to Plan 097).
- No frontend or API modifications.

---

## 6. Progress Log

- 2026-08-31: Completed Plan 094 discovery and finalized frozen architecture.
- 2026-08-31: Added `boto3>=1.28.0` to `pyproject.toml` and updated `uv.lock`.
- 2026-08-31: Implemented `src/cloud/batch_runner.py` with S3 sync, workspace redirection, manifest-last validation, and error boundaries.
- 2026-08-31: Created unit test suite in `tests/unit/test_batch_runner.py` (10 passing unit tests).
- 2026-08-31: Implemented `Dockerfile.analytics` for ARM64 with pre-bundled spaCy model and no default help CMD.
- 2026-08-31: Implemented `BatchStack` in `infra/community_analysis_infra/batch_stack.py` with ECR, VPC (0 NAT), Fargate Spot/On-Demand compute, job queue, job definition, and scoped IAM roles.
- 2026-08-31: Created CDK test suite in `infra/tests/test_batch_stack.py` (66 total infra unit tests passing).
- 2026-08-31: Updated `infra/app.py` with context isolation (existing stacks synthesize without `batch_image_tag`).
- 2026-08-31: Updated `Makefile` with targets for `analytics-image-build` (`ANALYTICS_LOCAL_IMAGE`), `analytics-image-smoke`, `analytics-image-sample`, `infra-diff-batch`, `infra-deploy-batch`, and `submit-batch-run`.
- 2026-08-31: Verified local CDK synthesis for `dev` and `prod` stages with separate image contexts.
- 2026-08-31: Validated local ARM64 Docker container with `--help`, `--dry-run`, and real sample execution (`analytics-image-sample` passed in 14.2s verifying 60 artifacts).
