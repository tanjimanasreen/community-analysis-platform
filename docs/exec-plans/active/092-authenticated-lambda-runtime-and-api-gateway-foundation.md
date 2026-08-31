# Execution Plan 092: Authenticated Lambda Runtime and API Gateway Foundation

**Status**: complete
**Milestones**:
- [x] Pre-change verification (Git branch `dev`, clean tree, HEAD at `d278a7ad`)
- [x] Added AWS Lambda Web Adapter 1.0.1 to `Dockerfile.api`
- [x] Built local `linux/arm64` image and verified local container functionality (`/api/v1/health`, `/api/v1/ready`)
- [x] Created `ApiStack` (`infra/community_analysis_infra/api_stack.py`) with Cognito User Pool, App Client, Lambda ARM64 Container Function, API Gateway HTTP API v2, JWT Authorizer, least-privilege S3 read IAM, and 7-day CloudWatch log retention
- [x] Wired `ApiStack` into `infra/app.py` under stack name `community-analysis-<stage>-api` with explicit `image_tag` context parameter
- [x] Added comprehensive CDK unit tests in `infra/tests/test_api_stack.py`
- [x] Added deployment and diff targets in `Makefile` and updated `infra/README.md`
- [x] Verified `make infra-test`, `make api-smoke-test`, `make infra-synth`, and `git diff --check`
- [x] Committed implementation changes locally as first commit (`Add authenticated Lambda API foundation` - `94fa3081`)
- [x] Captured commit SHA `PLAN092_IMAGE_SHA` (`94fa3081`), built clean ARM64 image, and pushed immutable image to ECR
- [x] Ran `cdk diff` and deployed `community-analysis-dev-api` to development environment
- [x] Verified live endpoints: public `/api/v1/health` (200), unauthenticated `/api/v1/runs` (401), Cognito authenticated `/api/v1/runs` (200), authenticated `/api/v1/ready` (200)
- [x] Cleaned up temporary test Cognito user
- [x] Benchmarked cold-start and warm-request latencies and memory consumption
- [x] Finalized deployment evidence in documentation and created second commit (`Finalize Plan 092 deployment evidence`)

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
     - `COMMUNITY_ANALYSIS_API_ALLOWED_HOSTS=*`
   - Response mode: default buffered mode (no streaming).

2. **Lambda Compute & Storage Configuration**:
   - Architecture: `ARM_64` (AWS Graviton2).
   - Memory: `1024 MB` (initial benchmark starting point).
   - Timeout: `30 seconds` (maximum HTTP API integration limit).
   - Ephemeral storage: default `512 MB`.
   - VPC: `NONE` (zero database/internal dependencies).
   - Provisioned Concurrency: `NONE` ($0 idle compute cost).

3. **Authentication & Route Security**:
   - Cognito User Pool: self sign-up disabled, email/username sign-in.
   - Cognito App Client: client secret disabled, `USER_SRP_AUTH`, `USER_PASSWORD_AUTH`, and `ADMIN_USER_PASSWORD_AUTH` enabled.
   - API Gateway HTTP API (v2) with `HttpJwtAuthorizer`.
   - Public Route: `GET /api/v1/health` (no JWT required).
   - Protected Route: `$default` route with Cognito JWT authorizer. All analytical routes (`/api/v1/ready`, `/api/v1/runs`, etc.) require valid Cognito Bearer tokens.

4. **S3 IAM & Storage Configuration**:
   - Consumes `StorageStack.bucket` directly.
   - `COMMUNITY_ANALYSIS_STORAGE_BACKEND=s3`
   - `COMMUNITY_ANALYSIS_S3_BUCKET=community-analysis-dev-762738182380-us-east-1-data`
   - `COMMUNITY_ANALYSIS_S3_REGION=us-east-1`
   - Read-only IAM: `s3:GetObject*`, `s3:GetBucket*`, `s3:List*` on bucket and bucket objects. Zero write/delete permissions.

5. **CloudWatch Logs & Observability**:
   - Dedicated log group: `/aws/lambda/community-analysis-dev-api`.
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

## Files Changed
- `docs/exec-plans/active/092-authenticated-lambda-runtime-and-api-gateway-foundation.md` [NEW]
- `Dockerfile.api` [MODIFY]
- `infra/community_analysis_infra/api_stack.py` [NEW]
- `infra/app.py` [MODIFY]
- `infra/tests/test_api_stack.py` [NEW]
- `Makefile` [MODIFY]
- `infra/README.md` [MODIFY]

## Verification Evidence
1. **CDK Unit Tests**: 44 passed in 2.09s (`make infra-test`).
2. **FastAPI Smoke Tests**: 10 passed in 3.52s (`make api-smoke-test`).
3. **Multi-Stage Synthesis**: `cdk synth -c stage=dev -c image_tag=94fa3081` and `cdk synth -c stage=prod -c image_tag=94fa3081` succeeded.
4. **Local Docker Smoke**: Container smoke test passed on `community-analysis-api:dev`.
5. **ECR Image Deployment**:
   - Repository: `community-analysis-dev-api`
   - Tag: `94fa3081` (immutable)
   - Digest: `sha256:0d2dddc3c9d247dd553242970e0733d25c537b4d3da10464b4ad5a8a1f24cb14`
   - Compressed size: 348,705,181 bytes (~348.7 MB)
6. **Live AWS Deployment**:
   - Stack: `community-analysis-dev-api` (16 resources created in 75s)
   - ApiEndpoint: `https://4gyy7676jb.execute-api.us-east-1.amazonaws.com`
   - CognitoUserPoolId: `us-east-1_axR1Wox61`
   - CognitoAppClientId: `6j0m0h1mqk5pbig32hho281tcf`
   - LambdaFunctionName: `community-analysis-dev-api`
   - LogGroupName: `/aws/lambda/community-analysis-dev-api` (7-day retention)
7. **Live Security & Route Verification**:
   - Public `GET /api/v1/health` -> `HTTP/2 200` (`{"status":"ok","read_only":true,"schema_version":"1.0"}`)
   - Unauthenticated `GET /api/v1/runs` -> `HTTP/2 401` (`{"message":"Unauthorized"}`)
   - Authenticated `GET /api/v1/runs` with valid Cognito Bearer JWT -> `HTTP/2 200` (`{"runs":[],"total":0}`)
   - Authenticated `GET /api/v1/ready` with valid Cognito Bearer JWT -> `HTTP/2 200` (`{"status":"ready","read_only":true,"artifact_root_ready":true,"discovered_runs":0}`)
8. **Live Performance Benchmarking**:
   - Cold Start: Init Duration: 3164.41 ms, Duration: 5.87 ms, Billed Duration: 3171 ms, Max Memory Used: 216 MB
   - Warm Requests (5 invocations):
     - Request 1: 0.3137s (internal duration: 4.27 ms, billed: 5 ms)
     - Request 2: 0.3109s (internal duration: 22.86 ms, billed: 23 ms)
     - Request 3: 0.2832s (internal duration: 4.12 ms, billed: 5 ms)
     - Request 4: 0.2849s (internal duration: 3.96 ms, billed: 4 ms)
     - Request 5: 0.3234s (internal duration: 3.94 ms, billed: 4 ms)
     - Average end-to-end warm latency: 0.3032s (~303 ms)
     - Max Memory Used across warm requests: 219 MB / 1024 MB
9. **IAM Least-Privilege Verification**:
   - `s3:GetObject*`, `s3:GetBucket*`, `s3:List*` scoped strictly to `arn:aws:s3:::community-analysis-dev-762738182380-us-east-1-data` and its contents.
   - Zero write/delete permissions (`0 PutObject`, `0 DeleteObject`, `0 s3:*`).
10. **Networking Invariants**:
   - 0 VPC, 0 Subnets, 0 NAT Gateways, 0 Security Groups, 0 VPC Endpoints, 0 EC2 instances.

## Progress Log
- 2026-08-30: Initialized Plan 092 execution plan with frozen architecture decisions.
- 2026-08-30: Integrated AWS Lambda Web Adapter 1.0.1 into `Dockerfile.api`.
- 2026-08-30: Implemented `ApiStack` in `infra/community_analysis_infra/api_stack.py` with Cognito User Pool, App Client, Lambda ARM64 Container Function, API Gateway HTTP API v2, JWT Authorizer, and CloudWatch Log Group.
- 2026-08-30: Added CDK unit tests in `infra/tests/test_api_stack.py` (44 tests passing).
- 2026-08-30: Committed implementation changes locally as first commit (`94fa3081`).
- 2026-08-30: Built clean ARM64 container image `94fa3081` and pushed to ECR repository `community-analysis-dev-api`.
- 2026-08-30: Deployed `community-analysis-dev-api` stack to AWS dev stage.
- 2026-08-30: Verified live endpoints (public health 200, unauthorized 401, authenticated 200, S3 readiness 200).
- 2026-08-30: Completed cold/warm benchmarking and cleaned up temporary Cognito validation user.
- 2026-08-30: Finalized Plan 092 deployment evidence.
- 2026-08-31: Final review remediation removed the unsafe default API image tag, added explicit IMAGE_TAG guards, corrected Plan 092 documentation text, and strengthened the S3 read-only IAM regression test. Local validation passed; no AWS resources were modified.
