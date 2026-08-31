# Execution Plan 092: Authenticated Lambda Runtime and API Gateway Foundation

**Status**: in-progress
**Milestones**:
- [ ] Pre-change verification (Git branch `dev`, clean tree, HEAD at `d278a7ad`)
- [ ] Added AWS Lambda Web Adapter 1.0.1 to `Dockerfile.api`
- [ ] Built local `linux/arm64` image and verified local container functionality (`/api/v1/health`, `/api/v1/ready`)
- [ ] Created `ApiStack` (`infra/community_analysis_infra/api_stack.py`) with Cognito User Pool, App Client, Lambda ARM64 Container Function, API Gateway HTTP API v2, JWT Authorizer, least-privilege S3 read IAM, and 7-day CloudWatch log retention
- [ ] Wired `ApiStack` into `infra/app.py` under stack name `community-analysis-<stage>-api` with explicit `image_tag` context parameter
- [ ] Added comprehensive CDK unit tests in `infra/tests/test_api_stack.py`
- [ ] Added deployment and diff targets in `Makefile` and updated `infra/README.md`
- [ ] Verified `make infra-test`, `make api-smoke-test`, `make infra-synth`, and `git diff --check`
- [ ] Committed implementation changes locally as first commit (`Add authenticated Lambda API foundation`)
- [ ] Captured commit SHA `PLAN092_IMAGE_SHA`, built clean ARM64 image, and pushed immutable image to ECR
- [ ] Ran `cdk diff` and deployed `community-analysis-dev-api` to development environment
- [ ] Verified live endpoints: public `/api/v1/health` (200), unauthenticated `/api/v1/runs` (401), Cognito authenticated `/api/v1/runs` (200), authenticated `/api/v1/ready` (200)
- [ ] Cleaned up temporary test Cognito user
- [ ] Benchmarked cold-start and warm-request latencies and memory consumption
- [ ] Finalized deployment evidence in documentation and created second commit (`Finalize Plan 092 deployment evidence`)

## Context & Objectives
Deploy the read-only FastAPI serving layer (`src/api/`) to AWS Lambda (ARM64) behind API Gateway HTTP API with Cognito JWT authentication for analytical endpoints and public process health. S3 artifact access remains read-only.

## Architecture Decisions
1. **Lambda Web Adapter**:
   - Pinned image: `public.ecr.aws/awsguru/aws-lambda-adapter:1.0.1`.
   - Extends container via `/opt/extensions/lambda-adapter`.
   - Zero modifications to application Python code (`src/api/`).
   - Environment variables:
     - `AWS_LWA_PORT=8000`
     - `AWS_LWA_READINESS_CHECK_PATH=/api/v1/health`
     - `AWS_LWA_READINESS_CHECK_HEALTHY_STATUS=200-399`
   - Response mode: default buffered mode (no streaming).

2. **Lambda Compute & Storage Configuration**:
   - Architecture: `ARM_64` (AWS Graviton2).
   - Memory: `1024 MB` (initial benchmark starting point).
   - Timeout: `30 seconds` (maximum HTTP API integration limit).
   - Ephemeral storage: default `512 MB`.
   - VPC: `NONE` (zero database/internal dependencies).
   - Provisioned Concurrency: `NONE` (zsh idle compute cost).

3. **Authentication & Route Security**:
   - Cognito User Pool: self sign-up disabled, email/username sign-in.
   - Cognito App Client: client secret disabled, `USER_SRP_AUTH` and `USER_PASSWORD_AUTH` enabled.
   - API Gateway HTTP API (v2) with `HttpJwtAuthorizer`.
   - Public Route: `GET /api/v1/health` (no JWT required).
   - Protected Route: `` route with Cognito JWT authorizer. All analytical routes (`/api/v1/ready`, `/api/v1/runs`, etc.) require valid Cognito Bearer tokens.

4. **S3 IAM & Storage Configuration**:
   - Consumes `StorageStack.bucket` directly.
   - `COMMUNITY_ANALYSIS_STORAGE_BACKEND=s3`
   - `COMMUNITY_ANALYSIS_S3_BUCKET=<bucket_name>`
   - `COMMUNITY_ANALYSIS_S3_REGION=<region>`
   - Read-only IAM: `s3:GetObject` on bucket objects, `s3:ListBucket` on bucket ARN. Zero write/delete permissions.

5. **CloudWatch Logs & Observability**:
   - Dedicated log group: `/aws/lambda/community-analysis-<stage>-api`.
   - Retention: `7 days` (`RetentionDays.ONE_WEEK`) for dev.
   - Removal policy: `DESTROY` for dev.

## Scope & Non-Goals
### Scope (Plan 092):
- Lambda Web Adapter 1.0.1 container integration.
- ARM64 ECR image build and immutable push.
- CDK `ApiStack` with Cognito User Pool, App Client, Lambda, API Gateway HTTP API, JWT Authorizer, and CloudWatch Log Group.
- CDK unit tests and multi-stage synthesis.
- Dev deployment, live authentication testing, and cold/warm latency benchmarking.

### Explicit Non-Goals:
- NO frontend hosting or CloudFront CDN (deferred to Plan 093).
- NO custom domain or Route 53.
- NO VPC, NAT Gateways, or subnets.
- NO AWS Batch, TEI, or Memgraph EC2.
- NO Provisioned Concurrency.
- NO production deployment.

## Files Expected to Change
- `docs/exec-plans/active/092-authenticated-lambda-runtime-and-api-gateway-foundation.md` [NEW]
- `Dockerfile.api` [MODIFY]
- `infra/community_analysis_infra/api_stack.py` [NEW]
- `infra/app.py` [MODIFY]
- `infra/tests/test_api_stack.py` [NEW]
- `Makefile` [MODIFY]
- `infra/README.md` [MODIFY]

## Verification Plan
1. **CDK Unit Tests**: `PYTHONPATH=infra infra/.venv/bin/pytest infra/tests` (verifies baseline, storage, registry, and api stacks).
2. **CDK Synthesis**: `cdk synth -c stage=dev -c image_tag=test1234` and `cdk synth -c stage=prod -c image_tag=test1234`.
3. **Local Docker Smoke**: Local container build and health/ready verification.
4. **Live Dev Deployment**:
   - `cdk diff community-analysis-dev-api -c stage=dev -c image_tag=<SHA>`
   - `cdk deploy community-analysis-dev-api -c stage=dev -c image_tag=<SHA>`
5. **Live Endpoint & Security Verification**:
   - Public `/api/v1/health` returns 200 without token.
   - Protected `/api/v1/runs` returns 401 without token.
   - Protected `/api/v1/runs` returns 200 with valid Cognito JWT.
   - Protected `/api/v1/ready` returns 200 with valid Cognito JWT.
6. **Latency Benchmarking**: Capture cold-start Init Duration and 5 consecutive warm requests.

## Progress Log
- 2026-08-30: Initialized Plan 092 execution plan with frozen architecture decisions.
