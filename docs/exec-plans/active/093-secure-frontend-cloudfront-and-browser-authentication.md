# Plan 093 — Secure Frontend Hosting, CloudFront Routing, and Browser Authentication

## Status
`in-progress` (Local source implementation complete; awaiting human review before deployment)

## Goal
Implement secure, production-quality frontend hosting, CloudFront unified distribution routing, and browser authentication for the `community-analysis` platform on AWS.

The target architecture:
```text
User
  │
  ▼
CloudFront (Unified CDN)
  ├── /*       → Private Frontend S3 Bucket (via Origin Access Control / OAC)
  │             (with CloudFront Function rewriting extensionless routes to /index.html)
  │
  └── /api/*   → Amazon API Gateway HTTP API (Plan 092)
                         │
                         ▼
                  Cognito JWT Authorizer
                         │
                         ▼
                  AWS Lambda Container (Plan 092)
                         │
                         ▼
                 Analytical S3 Bucket (Plan 089)
```

## Frozen Architecture Decisions
1. **Frontend S3 Bucket**:
   - Private S3 bucket with `BlockPublicAccess.BLOCK_ALL`, SSE-S3 encryption (`AES256`), SSL enforced (`enforce_ssl=True`), and zero public access.
   - S3 website hosting is explicitly disabled.

2. **CloudFront CDN & Origin Access Control (OAC)**:
   - Modern S3 Origin Access Control (OAC); legacy Origin Access Identity (OAI) is completely absent.
   - CloudFront Function attached to default viewer-request rewriting extensionless SPA paths (`/communities`, `/evolution`, etc.) to `/index.html` while leaving `/api/*` intact.
   - Default behavior: CachingOptimized, Redirect to HTTPS.
   - `/api/*` behavior: CachingDisabled, `AllViewerExceptHostHeader` Origin Request Policy preserving `Authorization` headers, query strings, and all HTTP methods. Zero CloudFront functions/Lambda@Edge on API routes.

3. **Cognito Browser Authentication**:
   - Reuses existing Plan 092 Cognito User Pool. Zero duplicate User Pools.
   - Dedicated Frontend Cognito App Client with `GenerateSecret=False`, PKCE authorization code grant, and CloudFront domain callback/logout URLs.
   - Dedicated Cognito Managed Login domain prefix.

4. **Frontend Architecture & Auth Modes**:
   - Minimal dependency: `aws-amplify` used for Auth APIs only (no Amplify Hosting / Backend).
   - Explicit `VITE_AUTH_MODE=local` (default for cloud-free local dev) and `VITE_AUTH_MODE=cognito` (for CloudFront deployment).
   - Centralized Axios interceptor automatically injecting Cognito Bearer tokens into API calls when in `cognito` mode.
   - Authenticated report opening and artifact downloading helpers utilizing Bearer auth with Blob URLs.

## Scope & Non-Goals
### Scope (Plan 093):
- CDK `FrontendStack` with private S3, CloudFront OAC, SPA router function, Cognito frontend client, and managed login domain prefix.
- CDK unit tests in `infra/tests/test_frontend_stack.py`.
- Frontend auth subsystem in `frontend/src/auth/` with `AuthProvider`, `useAuth`, and `AuthGate`.
- Centralized Axios auth interceptor in `frontend/src/api/client.ts` and authenticated report/download helpers in `frontend/src/api/reports.ts`.
- Topbar user state & Sign Out controls in `frontend/src/components/Topbar.jsx`.
- Focused frontend unit tests in `frontend/src/auth/__tests__/` and `frontend/src/api/__tests__/`.

### Non-Goals (Future Plans):
- AWS CDK deployment to remote account (deferred to post-review deployment step).
- Frontend static asset synchronization to S3 (`aws s3 sync`).
- CloudFront cache invalidation (`aws cloudfront create-invalidation`).
- Custom domains, Route 53 DNS records, ACM certificates.
- AWS WAF WebACLs.
- Analytical algorithm modifications.

## Security Model
- **Zero Public S3 Access**: Both analytical data and frontend static assets are strictly private.
- **OAC-Only S3 Read**: CloudFront accesses S3 exclusively through SigV4 Origin Access Control.
- **Cognito JWT Route Protection**: Analytical API routes require valid Cognito Bearer JWT tokens.
- **PKCE Browser Auth**: Public SPA client uses authorization code grant with PKCE and no client secrets.
- **Least Privilege**: Read-only access boundaries preserved across all cloud components.

## Files Changed
### Created:
- `infra/community_analysis_infra/frontend_stack.py`
- `infra/tests/test_frontend_stack.py`
- `frontend/src/auth/authConfig.ts`
- `frontend/src/auth/authContext.ts`
- `frontend/src/auth/AuthProvider.tsx`
- `frontend/src/auth/useAuth.ts`
- `frontend/src/auth/AuthGate.tsx`
- `frontend/src/auth/index.ts`
- `frontend/src/auth/__tests__/authConfig.test.ts`
- `frontend/src/auth/__tests__/AuthGate.test.tsx`
- `frontend/src/api/__tests__/authInterceptor.test.ts`
- `docs/exec-plans/active/093-secure-frontend-cloudfront-and-browser-authentication.md`

### Modified:
- `infra/app.py`
- `infra/README.md`
- `ARCHITECTURE.md`
- `Makefile`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/.env.example`
- `frontend/src/App.jsx`
- `frontend/src/api/client.ts`
- `frontend/src/api/reports.ts`
- `frontend/src/components/Topbar.jsx`
- `frontend/src/components/__tests__/Topbar.test.jsx`
- `frontend/src/features/evidence/RunOutputs.tsx`
- `frontend/src/features/evidence/EvidenceRecordDetails.tsx`
- `frontend/src/pages/CommunityTransitions.jsx`

## Verification Matrix
- `make infra-test`: All 51 CDK unit tests passing.
- `make api-smoke-test`: All 10 backend API unit tests passing.
- `make infra-synth INFRA_STAGE=dev IMAGE_TAG=94fa3081`: Synthesis clean.
- `make infra-synth INFRA_STAGE=prod IMAGE_TAG=94fa3081`: Synthesis clean.
- Frontend unit tests: 14 passing tests across auth, interceptor, AuthGate, and Topbar.
- `make frontend-lint`: Oxlint clean (0 errors).
- `make frontend-build`: Vite client production build clean.
- `git diff --check`: Clean (0 whitespace/formatting errors).

## Future Deployment Steps (Post-Approval)
1. `make infra-deploy-frontend INFRA_STAGE=dev IMAGE_TAG=94fa3081`
2. Retrieve outputs (`CloudFrontDomainName`, `FrontendBucketName`, `FrontendCognitoClientId`, `CognitoDomain`).
3. Build production frontend with Cognito environment variables.
4. Upload frontend bundle: `aws s3 sync frontend/dist s3://<FrontendBucketName> --delete`.
5. Invalidate CDN cache: `aws cloudfront create-invalidation --distribution-id <CloudFrontDistributionId> --paths "/*"`.
6. Live end-to-end browser verification of Cognito login, analytical dashboard navigation, and authenticated downloads.

## Progress Log
- **2026-08-31**: Authored Plan 093 execution plan.
- **2026-08-31**: Implemented CDK `FrontendStack` with private S3, CloudFront OAC, SPA routing function, Cognito frontend app client, and managed login domain.
- **2026-08-31**: Wired `FrontendStack` into `infra/app.py` and added CDK unit tests in `infra/tests/test_frontend_stack.py`.
- **2026-08-31**: Installed `aws-amplify` and implemented frontend auth module with local and Cognito modes.
- **2026-08-31**: Centralized API Bearer token injection and authenticated downloads in `frontend/src/api/client.ts` and `reports.ts`.
- **2026-08-31**: Integrated `AuthProvider`, `AuthGate`, and `Topbar` user auth controls.
- **2026-08-31**: Verified all CDK tests, API smoke tests, synthesis, frontend unit tests, and production build.
- **2026-08-31**: Remediated frontend Cognito/API audience compatibility by adding a protected /api/{proxy+} route accepting both existing API and frontend App Client IDs; added strict auth-mode validation and strengthened CloudFront API behavior assertions. Local validation only; no AWS resources modified.
