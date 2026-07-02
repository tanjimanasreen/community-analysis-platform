# Execution Plan: Frontend Dashboard Integration

Status: complete

Owner: agent

Last updated: 2026-07-02

## Goal

Update the existing Vite/React frontend to consume only the read-only `/api/v1`
artifact API and visualize generated community-analysis outputs.

## Non-Goals

- Do not add pipeline-run actions.
- Do not call OpenAI, Neo4j, Memgraph, Docker, LDA, SentenceTransformer, or
  Kaleido from the frontend.
- Do not change public output schemas or backend API contracts.
- Do not implement old endpoint graph/static iframe rendering in this phase.

## Files Changed

- `frontend/src/api.js`
- `frontend/src/App.jsx`
- `frontend/src/index.css`
- `frontend/.env.example`
- `frontend/vite.config.js`
- `frontend/README.md`
- `Makefile`
- `README.md`
- `code_setup.md`
- `docs/design-docs/pipeline-contract.md`
- `docs/exec-plans/active/012-frontend-dashboard-integration.md`

## Milestones

### Milestone 1: API-Backed Dashboard

Tasks:

- [x] Add frontend API client using `VITE_API_BASE_URL || "/api/v1"`.
- [x] Replace old/demo endpoint calls with `/api/v1`.
- [x] Add run/month selectors, health, verification, summaries, tables, and
  optional file states.
- [x] Keep dashboard read-only.

Validation:

```bash
cd frontend && npm run lint
cd frontend && npm run build
```

### Milestone 2: Local Dev Workflow

Tasks:

- [x] Add Vite `/api` proxy to `http://127.0.0.1:8000`.
- [x] Add frontend Make targets.
- [x] Document workflow.

Validation:

```bash
make api-smoke-test
make frontend-build
```

## Acceptance Criteria

- [x] Backend smoke tests pass.
- [x] Output-contract verifiers still pass.
- [x] Frontend lint passes.
- [x] Frontend build passes without the backend running.
- [x] No old/demo API calls remain in frontend source.

## Progress Log

| Date | Update |
|---|---|
| 2026-07-02 | Added read-only `/api/v1` frontend integration, Vite proxy, dashboard tables, docs, and Make targets. Validation pending. |
| 2026-07-02 | Completed validation: `npm ci`, frontend lint/build, API smoke test, one-month pipeline/verifier, longitudinal pipeline/verifier, and old endpoint source scan all passed. |
