# Execution Plan 094: AWS Batch Analytical Compute

**Status**: complete
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
## Final AWS acceptance evidence

Plan 094 was deployed and validated end-to-end in the `dev` environment.

### Initial deployment

- Foundation commit: `677def7d` — `Add AWS Batch analytical compute foundation`.
- AWS Batch stack deployed successfully.
- Analytical ECR repository:
  `community-analysis-dev-analytics`.
- Batch job definition:
  `community-analysis-dev-analytics-job`.
- Batch queue:
  `community-analysis-dev-queue`.
- Compute environments:
  - `FARGATE_SPOT`
  - `FARGATE`
- Job definition runtime:
  - Linux ARM64
  - 4 vCPU
  - 16 GiB memory
  - 30 GiB ephemeral storage
  - public IP enabled
- No NAT Gateway is used.

The first live mock acceptance job completed successfully at the AWS
Batch level with exit code `0`, but strict API/frontend verification
exposed an incomplete published run bundle.

Initial acceptance run:

- Run ID: `5543dbaf-4367-49c9-8586-4a0d4d8e506e`
- Batch status: `SUCCEEDED`
- Exit code: `0`
- Top-level manifest status: `completed`
- Canonical artifacts: `60`

The frontend correctly rejected the run with `INVALID_MANIFEST` because
nested canonical artifacts such as:

`_intermediate/topic_inputs/reply/03_2017/manifest.json`

were absent from `runs/<run_id>/`.

### Nested-manifest publication remediation

Root cause:

`publish_completed_run_to_s3()` excluded artifacts using a
filename-only `manifest.json` check. This unintentionally skipped every
nested artifact named `manifest.json`, rather than only withholding the
top-level run manifest used as the final publication marker.

Remediation commit:

`3adeb1fd` — `Fix nested manifest Batch publication`

The publication logic now:

- uploads nested `manifest.json` artifacts normally;
- skips only `<run_dir>/manifest.json` during ordinary artifact
  publication;
- uploads the top-level run manifest exactly once and strictly last.

A regression test was added proving nested manifests are uploaded while
top-level manifest-last semantics remain intact.

### Final live acceptance

The remediated ARM64 analytical image was pushed using immutable tag:

`3adeb1fd`

The Batch stack was updated to job-definition revision `2`, pointing to:

`community-analysis-dev-analytics:3adeb1fd`

Final acceptance job completed successfully.

Final run:

- Run ID: `53305127-f53d-44c9-86b9-21c4e1ae52ad`
- Batch status: `SUCCEEDED`
- Exit code: `0`
- Manifest status: `completed`
- Canonical artifacts: `60`

The previously missing nested artifacts were verified directly in S3:

- `_intermediate/topic_inputs/reply/03_2017/manifest.json`
- `_intermediate/topic_inputs/reply/04_2017/manifest.json`

Both were present in the final `runs/<run_id>/` bundle.

The deployed API/frontend subsequently loaded the final run successfully
and displayed `Run verified`.

### Plan 094 acceptance result

Plan 094 is complete.

Validated path:

AWS Batch Fargate
→ analytical container
→ existing analytical pipeline
→ canonical run bundle
→ S3
→ Lambda API
→ strict manifest verification
→ CloudFront frontend.

No thesis analytical metric definitions, algorithm defaults, Stage A,
Stage B, manifest schema, or artifact schema were changed by Plan 094.

---

## 6. Progress Log

7. Progress Log
- 2026-08-31: Completed Plan 094 discovery and finalized the frozen AWS Batch architecture.
- 2026-08-31: Added boto3>=1.28.0 to pyproject.toml and updated uv.lock.
- 2026-08-31: Implemented src/cloud/batch_runner.py with S3 synchronization, workspace redirection, completed-manifest verification, manifest-last publication, and error boundaries.
- 2026-08-31: Added the initial Batch runner unit-test suite.
- 2026-08-31: Implemented S3 download path-containment protection against absolute paths and parent traversal.
- 2026-08-31: Created Dockerfile.analytics for ARM64 with pre-bundled spaCy model and no default help command.
- 2026-08-31: Implemented BatchStack with analytical ECR, dedicated 2-AZ VPC with 0 NAT Gateways, Fargate Spot/On-Demand compute, queue, ARM64 job definition, scoped IAM roles, and bounded CloudWatch retention.
- 2026-08-31: Added Batch CDK infrastructure tests and validated the full infra test suite.
- 2026-08-31: Updated infra/app.py with Batch context isolation so existing API/frontend stacks continue to synthesize without batch_image_tag.
- 2026-08-31: Updated the Makefile with analytical image build/smoke/sample targets, Batch diff/deploy targets, and explicit Batch submission requiring INFRA_STAGE, CONFIG, and THEME_PROVIDER.
- 2026-08-31: Verified local CDK synthesis for dev and prod.
- 2026-08-31: Validated the local ARM64 analytics image with smoke, dry-run, and deterministic sample execution; the sample produced 60 canonical artifacts.
- 2026-08-31: Committed the Plan 094 analytical compute foundation as 677def7d.
- 2026-08-31: Deployed community-analysis-dev-batch successfully. Both FARGATE_SPOT and FARGATE compute environments reported ENABLED / VALID, and the Batch queue reported ENABLED / VALID.
- 2026-08-31: Built and pushed immutable ARM64 analytical image 677def7d to community-analysis-dev-analytics.
- 2026-08-31: Executed the first live mock Batch acceptance job. AWS Batch completed with SUCCEEDED and exit code 0; run 5543dbaf-4367-49c9-8586-4a0d4d8e506e produced a completed top-level manifest containing 60 canonical artifacts.
- 2026-08-31: API/frontend strict verification exposed an incomplete publication bundle because nested canonical files named manifest.json were excluded by filename-only publication logic.
- 2026-08-31: Added a focused nested-manifest publication regression test, reproduced the defect locally, and fixed publish_completed_run_to_s3() so only the top-level run manifest is withheld from ordinary publication.
- 2026-08-31: Completed remediation validation with 15 Batch runner tests passing, targeted lint passing, compile validation passing, API smoke tests passing, and git diff --check clean.
- 2026-08-31: Committed the publication remediation as 3adeb1fd.
- 2026-08-31: Built and pushed corrected immutable ARM64 analytical image 3adeb1fd.
- 2026-08-31: Reviewed the remediation CDK diff; only the Batch job-definition image changed from 677def7d to 3adeb1fd.
- 2026-08-31: Deployed Batch job-definition revision 2 successfully with no storage, VPC, compute-environment, queue, ECR, or IAM architecture changes.
- 2026-08-31: Executed the final live mock Batch acceptance job successfully.
- 2026-08-31: Verified final run 53305127-f53d-44c9-86b9-21c4e1ae52ad with Batch SUCCEEDED, exit code 0, top-level manifest status completed, and 60 canonical artifacts.
- 2026-08-31: Verified nested 03_2017/manifest.json and 04_2017/manifest.json canonical artifacts directly in the final S3 run bundle.
- 2026-08-31: Verified the final run end-to-end through the deployed Lambda API and CloudFront frontend; the UI displayed Run verified and rendered the Community Evolution analysis successfully.
- 2026-08-31: Marked Plan 094 complete.