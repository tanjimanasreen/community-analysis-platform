# Execution Plan: Read-Only Backend/API For Generated Outputs

Status: complete

Owner: agent

Last updated: 2026-07-02

## Goal

Create a read-only FastAPI API that serves verified generated pipeline
artifacts for future dashboard and report UI work.

## Non-Goals

- Do not run or mutate ingestion, network, community, LDA, theme, visualization,
  database, model, or output-generation stages from the API.
- Do not call Neo4j, Memgraph, Docker, OpenAI, SentenceTransformer, or Kaleido.
- Do not implement or modify the frontend/dashboard in this phase.

## Files Changed

- `backend/main.py`
- `backend/artifact_service.py`
- `backend/schemas.py`
- `src/reporting/output_contract.py`
- `pyproject.toml`
- `requirements.txt`
- `Makefile`
- `tests/unit/test_backend_api.py`
- `README.md`
- `code_setup.md`
- `docs/design-docs/pipeline-contract.md`
- `docs/exec-plans/active/011-read-only-backend-api.md`

## Milestones

### Milestone 1: Read-Only Artifact Service

Tasks:

- [x] Register runs from default paths, env override, or injected configs.
- [x] Resolve only known output-contract artifact paths.
- [x] Normalize CSV values for JSON responses.
- [x] Add pagination and optional-missing behavior.

Validation:

```bash
.venv/bin/python -m pytest tests/unit/test_backend_api.py
```

### Milestone 2: FastAPI V1 Endpoints

Tasks:

- [x] Add `create_app(config_paths=None, configs=None)`.
- [x] Keep `app = create_app()` for uvicorn.
- [x] Add `/api/v1` health, runs, facets, verification, artifacts, community,
  topic, theme, transition, and file metadata endpoints.
- [x] Avoid absolute local paths in default API metadata responses.

Validation:

```bash
make api-smoke-test
```

### Milestone 3: Docs And Local Commands

Tasks:

- [x] Add FastAPI/uvicorn/httpx dependencies.
- [x] Add `api-smoke-test` and `run-api` Make targets.
- [x] Document read-only API usage.

Validation:

```bash
make help
```

## Acceptance Criteria

- [x] Unit tests pass.
- [x] API smoke test passes.
- [x] One-month and longitudinal sample verification still pass.
- [x] API endpoints remain read-only and avoid pipeline/model imports.
- [x] No frontend/dashboard implementation is included.

## Progress Log

| Date | Update |
|---|---|
| 2026-07-02 | Added read-only artifact service, FastAPI app factory, `/api/v1` endpoints, backend tests, dependencies, Make targets, and docs. Validation pending. |
| 2026-07-02 | Full validation passed: unit suite, one-month sample and contract verification, longitudinal sample and contract verification, and API smoke test. |

## Risks

| Risk | Mitigation |
|---|---|
| Existing backend demo endpoints used mock fallbacks. | New real endpoints live under `/api/v1` and return no fabricated analysis data. |
| Optional visualization and partial-match artifacts are not always present. | API returns explicit optional-missing metadata or empty optional tables. |
