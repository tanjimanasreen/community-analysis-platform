# Release And Demo Checklist

Use this checklist before packaging, sharing, or demoing the project from a
fresh checkout.

## Fresh Checkout Setup

```bash
make install-dev
make frontend-install
```

- Python dependencies are installed from `pyproject.toml`.
- `requirements.txt` is a compatibility wrapper and should stay small.
- Frontend dependencies are installed with `npm ci` from
  `frontend/package-lock.json`.

## Offline Demo Proof

```bash
make demo
make frontend-lint
make frontend-build
```

`make demo` runs:

- one-month offline sample pipeline
- one-month output-contract verification
- longitudinal offline sample pipeline
- longitudinal output-contract verification
- artifact index generation
- read-only API smoke tests

The default demo must not require Neo4j, Memgraph, Docker, OpenAI, model
downloads, or Kaleido.

## Manual Read-Only Demo

Terminal 1:

```bash
make demo-api
```

Terminal 2:

```bash
make demo-frontend
```

Confirm in the browser:

- API health is visible.
- sample and longitudinal runs are listed.
- verification status is visible.
- community, topic, theme, transition, and artifact tables load.
- no pipeline-run controls are present.

## Generated File Policy

Commit:

- source code
- tests and fixtures
- configs
- docs
- `frontend/package-lock.json`
- `.env.example` files

Do not commit:

- `.venv/`
- `frontend/node_modules/`
- `frontend/dist/`
- `src/*.egg-info/`
- `__pycache__/`
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- generated sample outputs or report files

Cleanup commands:

```bash
make clean-generated
make clean-cache
```

These targets are intentionally conservative and must not remove `.venv`,
`frontend/node_modules`, or user research outputs.
