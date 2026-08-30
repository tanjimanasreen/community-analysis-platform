# Execution Plan 091: API Containerization and ECR Foundation

**Status**: in-progress
**Milestones**:
- [x] Pre-change verification (Git branch `dev`, clean tree, HEAD at `e4a03b7a`)
- [x] Hardened `.dockerignore` against infrastructure, test, and build cache collateral
- [x] Validated `Dockerfile.api` for portable `linux/arm64` container builds with standard locked dependencies
- [x] Created `RegistryStack` (`infra/community_analysis_infra/registry_stack.py`) with private ECR repository, immutable tags, untagged image cleanup, and DEV destroy policy
- [x] Wired `RegistryStack` into `infra/app.py` under stack name `community-analysis-<stage>-registry`
- [x] Added comprehensive CDK unit tests in `infra/tests/test_registry_stack.py` (33/33 total infra tests passing)
- [x] Added developer Make targets (`api-image-build`, `api-image-smoke`) in `Makefile`
- [x] Built `linux/arm64` container image locally and validated smoke tests (`/api/v1/health`, `/api/v1/ready`, non-root execution, mounted sample artifact read, zero AWS credentials required)
- [x] Recorded actual container image dimensions and metadata (arm64, 1.14 GB uncompressed, Python 3.11.16, UID 10001)
- [x] Verified full CDK synthesis (`stage=dev`, `stage=prod`), infrastructure unit tests, and API smoke tests
- [x] Updated infrastructure documentation and progress log

## Context & Objectives
Package the read-only FastAPI serving layer (`src/api/`) into a portable, reproducible, non-root Docker container image and define a private development ECR repository using AWS CDK. ECR has been explicitly approved as a metered storage resource.

## Architecture Decisions
1. **Container Architecture & Base Image**:
   - Starting point: existing `Dockerfile.api`.
   - Base image: `python:3.11-slim-bookworm` (multi-stage build using `uv` with `--frozen --no-dev`).
   - Standardized build target: `linux/arm64` for native developer execution on Apple Silicon and future cost-effective Graviton2 Lambda execution.
   - Runtime user: dedicated non-root user `community` (UID 10001, GID 10001).
   - Startup command: Uvicorn ASGI server on port 8000.
   - Healthcheck: standard library `urllib.request` probing `/api/v1/health`.
   - Logging: structured JSON logging via `LOG_FORMAT=json`.

2. **Dependency Boundary**:
   - Preserves the locked runtime dependency graph from `pyproject.toml` and `uv.lock`.
   - No runtime analytical code is invoked during API serving.
   - Dependency isolation is deferred as a future optimization.

3. **Build Context Hygiene (`.dockerignore`)**:
   - Excludes `.venv/`, `infra/.venv/`, `infra/cdk.out/`, `cdk.out/`, `frontend/node_modules/`, `frontend/dist/`, `.stage_cache/`, `.pytest_cache/`, `.ruff_cache/`, `.coverage`, `htmlcov/`, `scratch/`, `.env*`, and local datasets.

4. **ECR Repository Design (`RegistryStack`)**:
   - Dedicated CDK stack: `RegistryStack` (`community-analysis-<stage>-registry`).
   - Repository name: `community-analysis-<stage>-api` (e.g. `community-analysis-dev-api`).
   - Tag Mutability: `IMMUTABLE` (enforces Git-SHA deployment tags; prevents tag collisions).
   - Encryption: ECR-managed / AES256 (no customer KMS key).
   - Lifecycle rule: automatically expire untagged images older than 1 day.
   - No repository-level scan-on-push added (deprecated property avoided; account-level scanning is managed separately).
   - No tagged image count expiration rule in Plan 091 (tagged retention deferred to Plan 092 Lambda versioning).
   - Removal policy: `cdk.RemovalPolicy.DESTROY` with `empty_on_delete=True` on `dev` to prevent orphaned storage charges on teardown.
   - CloudFormation Outputs: `RepositoryName`, `RepositoryArn`, `RepositoryUri`.
   - Standard resource tags applied.

## Scope & Non-Goals
### Scope (Plan 091):
- Portable API Docker image buildable for `linux/arm64`.
- `.dockerignore` hardening.
- Local container smoke testing (health, ready, artifact mount, non-root, zero credentials).
- ECR repository CDK construct and stack definition with lifecycle and cost controls.
- CDK unit tests and synthesis validation.
- Developer workflow tooling (`Makefile` targets).

### Explicit Non-Goals (Deferred to Plan 092+):
- NO AWS Lambda function deployment.
- NO API Gateway HTTP API deployment.
- NO Lambda Web Adapter or Mangum integration.
- NO IAM execution roles or S3 read policy grants.
- NO automated or manual image push to AWS ECR.
- NO AWS resource deployment (`cdk deploy`).
- NO frontend / CloudFront deployment.
- NO Batch / TEI / Memgraph cloud deployment.

## Files Expected to Change
- `docs/exec-plans/active/091-api-containerization-and-ecr-foundation.md` [NEW]
- `.dockerignore` [MODIFY]
- `Dockerfile.api` [MODIFY / VERIFY]
- `infra/community_analysis_infra/registry_stack.py` [NEW]
- `infra/app.py` [MODIFY]
- `infra/tests/test_registry_stack.py` [NEW]
- `Makefile` [MODIFY]
- `infra/README.md` [MODIFY]

## Container Evidence
```text
Image:
community-analysis-api:dev

Architecture:
linux/arm64

Local Docker image size:
1,147,793,315 bytes (approximately 1.14 GB uncompressed)

Python:
3.11.16

Runtime UID/GID:
10001 / 10001

Default empty artifact root:
HTTP 200
artifact_root_ready=true
discovered_runs=0

Nonexistent artifact root:
HTTP 503
artifact_root_ready=false
discovered_runs=0

Valid mounted artifact root:
HTTP 200
artifact_root_ready=true
discovered_runs=1

Credentials:
No AWS credentials are required for local artifact serving.
No external service credentials are required for local artifact serving.
```

## Final Validation
```text
Command:
make infra-test

Result:
33 passed

---

Command:
make api-smoke-test

Result:
10 passed

---

Command:
uv run --frozen --extra orchestration --extra tracking python -m pytest tests/unit/test_run_manifest.py tests/unit/test_artifact_storage.py tests/unit/test_api_storage_integration.py tests/unit/test_backend_api.py tests/unit/test_output_artifact_contract.py -v

Result:
77 passed

---

Command:
make infra-synth INFRA_STAGE=dev

Result:
PASS

---

Command:
make infra-synth INFRA_STAGE=prod

Result:
PASS

---

Command:
make api-image-smoke

Result:
PASS

---

Command:
git diff --check

Result:
PASS
```

## Progress Log
- 2026-08-29: Created Plan 091 execution plan and verified clean working tree at commit `e4a03b7a`.
- 2026-08-29: Hardened `.dockerignore` to exclude `infra/.venv/`, `infra/cdk.out/`, `frontend/node_modules/`, `frontend/dist/`, `.stage_cache/`, test caches, and coverage artifacts.
- 2026-08-29: Implemented `RegistryStack` in `infra/community_analysis_infra/registry_stack.py` with private ECR repository, immutable tags, untagged lifecycle cleanup (1 day), AES256 encryption, and DEV destroy policy.
- 2026-08-29: Wired `RegistryStack` into `infra/app.py` and added comprehensive unit tests in `infra/tests/test_registry_stack.py`.
- 2026-08-29: Added `api-image-build` and `api-image-smoke` targets to `Makefile`.
- 2026-08-29: Successfully built local `linux/arm64` image (`community-analysis-api:dev`, ID `1c027161d6663a23...`, 1.14 GB uncompressed) and validated unmounted and mounted container smoke tests against `/api/v1/health`, `/api/v1/ready`, and `/api/v1/runs`.
- 2026-08-29: Verified CDK synthesis for `dev` and `prod`, `make api-smoke-test`, `make infra-test`, and `git diff --check`.
- 2026-08-30: Plan 091 Ultra-Surgical Remediation:
  - Restored unrelated Plan 090 cosmetic diff in `docs/exec-plans/active/090-cloud-artifact-storage-abstraction-and-s3-read-foundation.md` to `HEAD` with explicit authorization.
  - Strengthened ECR lifecycle test in `infra/tests/test_registry_stack.py` to parse structured JSON rules (`tagStatus=untagged`, `countType=sinceImagePushed`, `countUnit=days`, `countNumber=1`, `action.type=expire`) and assert absence of tagged image expiry or count caps.
  - Added explicit tests for `EmptyOnDelete=True` on dev and `EmptyOnDelete=False` on prod.
  - Added explicit test verifying absence of deprecated `ImageScanningConfiguration` on dev and prod templates.
  - Empirically verified all 3 container readiness scenarios: default empty root (200, 0 discovered runs), nonexistent root (503, not ready), and valid mounted root (200, 1 discovered run).
  - Re-ran `make infra-test` (33 passed in 1.48s), `make api-smoke-test` (10 passed), CDK synthesis, `make api-image-smoke`, and 77-test regression suite.
- 2026-08-30: Plan 091 Final Evidence Cleanup:
  - Strengthened ECR encryption assertion in `infra/tests/test_registry_stack.py` to assert `EncryptionConfiguration` is absent or `AES256`, `KmsKey` is absent, and `AWS::KMS::Key` count is 0.
  - Formatted authoritative `## Final Validation` section clearly separating the 10 API smoke tests from the 77 focused regression tests.
  - Documented exact container facts, 3-state readiness behavior, and credential-independence statements.
  - Verified `make infra-test` (33 passed) and `git diff --check` (clean).
  - Status: implementation complete, remediation complete, final evidence cleanup complete; awaiting final independent review.
