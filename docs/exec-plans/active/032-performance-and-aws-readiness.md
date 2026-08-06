# Plan 032 — Dashboard production hardening and AWS readiness

## Goal

Make the existing read-only dashboard render the completed Retweet/Quote
longitudinal run correctly, safely display heterogeneous artifact values, and
prepare the frontend and `src/api` runtime boundary for a later AWS deployment.
This plan does not change analytical metrics, algorithms, defaults, or output
categories.

## Source of truth

- `community_analysis_repository.zip` supplied on 2026-07-24.
- `dashboard_reproduction_bundle.zip` supplied on 2026-07-24.
- Completed reproduction run:
  `739866ba-8f59-4784-a083-d64888b24ffd`.

## Tasklist

### 1. Reproduce and protect the graph failure

- [x] Verify the graph endpoint contains valid nodes and edges.
- [x] Confirm edge endpoints exist in the returned node set.
- [x] Identify the graph-container height feedback loop.
- [x] Add graph transformation tests for malformed and parallel edges.
- [x] Add a component regression test for fixed canvas height.

### 2. Repair graph rendering and interaction

- [x] Measure only graph-stage width with `ResizeObserver`.
- [x] Give the canvas a fixed, explicit stage height.
- [x] Add deterministic initial node positions.
- [x] Curve parallel links and preserve their individual weights.
- [x] Add valid fullscreen behavior, resize, fit, reset, pan, and zoom controls.
- [x] Surface sampled, parallel-edge, and malformed-edge diagnostics.

### 3. Render heterogeneous artifact data safely

- [x] Add one reusable `ArtifactValue` renderer.
- [x] Format JSON arrays as readable chips and expandable lists.
- [x] Format maps as nested key/value structures.
- [x] Preserve ordinary and non-JSON text without evaluation.
- [x] Use the renderer in Data Explorer, centrality, methodology, provider
      metadata, comparison, thematic details, and run-history metadata.
- [x] Display artifact byte sizes in human-readable binary units.

### 4. Harden the API for a reverse-proxy/container runtime

- [x] Add request IDs, duration logs, and `Server-Timing`.
- [x] Add security response headers and no-store API caching.
- [x] Add gzip compression.
- [x] Add configurable trusted hosts, CORS origins, root path, docs exposure,
      and compression threshold.
- [x] Add `/api/v1/ready` without exposing filesystem paths.
- [x] Add readiness and response-header tests.
- [x] Add a dedicated non-root `Dockerfile.api`.

### 5. Harden the frontend container boundary

- [x] Add nginx proxy/request headers, compression, and security headers.
- [x] Document build-time API base URL and request timeout.
- [x] Preserve a same-origin `/api/v1` default suitable for ALB/CloudFront.
- [x] Include backend request IDs in frontend technical error details.

### 6. Validate and hand off

- [x] Compile Python source and tests.
- [x] Validate YAML and JSON resources.
- [x] Run repository whitespace validation.
- [ ] Run the full Python suite in a dependency-complete local environment.
- [ ] Run frontend typecheck, lint, unit tests, build, and bundle gate with
      installed `node_modules`.
- [ ] Run Playwright against the supplied completed run and inspect every page.
- [ ] Build and smoke-test `Dockerfile.api` and `frontend/Dockerfile`.

## Acceptance criteria

- The sampled graph is visible at a stable height and remains visible after
  resize, metric changes, selection, reset, and fullscreen transitions.
- Arrays, maps, JSON strings, numbers, booleans, long text, and normal text are
  readable without evaluating artifact content.
- API errors include a request ID usable in CloudWatch logs.
- Liveness and readiness endpoints support container health checks.
- API and frontend images run as read-only services with configuration supplied
  through environment variables.
- Thesis metrics and protected algorithm defaults are unchanged.

## Progress log

| Date | Update |
|---|---|
| 2026-07-24 | Inspected the supplied repository and reproduction bundle as the only source of truth. The graph payload contained 200 nodes and 343 valid edges, while the screenshot showed an expanding blank stage. Traced the failure to a `ResizeObserver` child/container height feedback loop. |
| 2026-07-24 | Added stable graph sizing, deterministic node positions, parallel-edge curvature, fullscreen/fit behavior, safe heterogeneous artifact rendering, API request diagnostics/readiness/security/compression, nginx hardening, API container support, and focused regression tests. |
| 2026-07-24 | Sandbox validation was limited by unavailable package registries and missing installed frontend dependencies. Dependency-complete local validation remains explicitly open. |

## Rollback

All changes are presentation, API-runtime, tests, and documentation. Revert this
plan's patch as one unit. Do not restore the previous height-observer behavior or
remove artifact verification to make the dashboard appear operational.
