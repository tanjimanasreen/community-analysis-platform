# Execution Plan: Reproducible Release And Demo Workflow

Status: complete

Owner: agent

Last updated: 2026-07-02

## Goal

Make the project easy to run from a fresh checkout and safe to package or demo
without changing thesis behavior, public output schemas, API contracts, or
dashboard functionality.

## Non-Goals

- Do not add research features.
- Do not change metrics, algorithm defaults, or output schemas.
- Do not add pipeline-run API actions or dashboard controls.
- Do not require Neo4j, Memgraph, Docker, OpenAI, model downloads, or Kaleido
  for the default demo.

## Files Changed

- `Makefile`
- `.gitignore`
- `pyproject.toml`
- `requirements.txt`
- `frontend/package.json`
- `frontend/package-lock.json`
- `README.md`
- `code_setup.md`
- `frontend/README.md`
- `docs/verification/release-checklist.md`
- `docs/exec-plans/active/013-reproducible-release-demo-workflow.md`
- `tests/unit/test_release_hygiene.py`

## Milestones

### Milestone 1: Install And Demo Targets

Tasks:

- [x] Add `install` and `install-dev`.
- [x] Add `demo`, `demo-api`, and `demo-frontend`.
- [x] Keep `frontend-install` lockfile-backed with `npm ci`.

Validation:

```bash
make install-dev
make frontend-install
make demo
```

### Milestone 2: Dependency And Generated-File Hygiene

Tasks:

- [x] Treat `pyproject.toml` as canonical.
- [x] Replace historical `requirements.txt` dump with a compatibility wrapper.
- [x] Remove unused frontend dependencies after source scan.
- [x] Add conservative `clean-generated` and `clean-cache` targets.
- [x] Ensure ignore rules cover generated files and caches.

Validation:

```bash
make clean-cache
make clean-generated
make frontend-lint
make frontend-build
```

### Milestone 3: Release Documentation And Tests

Tasks:

- [x] Add release checklist.
- [x] Update setup/demo docs.
- [x] Add offline release-hygiene tests.

Validation:

```bash
make test
make api-smoke-test
```

## Acceptance Criteria

- [x] Fresh checkout setup commands are documented.
- [x] `make demo` runs the full offline proof.
- [x] Output-contract verifiers pass.
- [x] API smoke tests pass.
- [x] Frontend lint and build pass.
- [x] Generated file cleanup is conservative.
- [x] No thesis metrics/defaults, schemas, API contracts, or dashboard behavior changed.

## Progress Log

| Date | Update |
|---|---|
| 2026-07-02 | Added release/demo Make targets, dependency cleanup, generated-file hygiene, docs, and static release tests. Validation pending. |
| 2026-07-02 | Completed validation: `make clean-cache`, `make clean-generated`, `make install-dev`, `make frontend-install`, `make test`, `make demo`, `make frontend-lint`, `make frontend-build`, and `make api-smoke-test` passed. `make install-dev` required network approval after sandbox DNS blocked PyPI. |
