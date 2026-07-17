# Plan 024 — Artifact and Run Contract

> Roadmap note: this work was requested as “Plan 023”, but this repository
> already contains `023-experiment-quality-reporting.md`. It is recorded as
> Plan 024 to preserve the existing execution-plan history.

## Goal

Standardize pipeline output storage so later stages, the read-only API, the
analytical dashboard, and report generation can consume one validated,
self-contained run bundle without knowing legacy CSV folder conventions.

This plan is additive. It does not rename or remove any frozen thesis output,
change analytical metrics, change algorithm defaults, or require Parquet.

## Scope

- Store orchestrated runs below `<output_base_path>/runs/<run_id>/`.
- Persist an atomic lifecycle manifest with `running`, `completed`, and `failed`
  states.
- Persist a secret-free resolved configuration and dataset identity file.
- Publish canonical copies into `intermediate/`, `data/`, and `reports/`.
- Preserve original CSV outputs and their schemas as compatibility artifacts.
- Validate path containment, checksums, byte sizes, row counts, schema versions,
  and known CSV columns.
- Prevent failed runs from appearing completed.

## Run Layout

```text
<output_base_path>/
└── runs/
    └── <run_id>/
        ├── manifest.json
        ├── resolved_config.yaml
        ├── inputs/
        │   └── datasets.json
        ├── intermediate/
        │   ├── topic_inputs/
        │   └── theme_inputs/
        ├── data/
        │   ├── network/
        │   ├── communities/
        │   ├── metrics/
        │   ├── topics/
        │   └── themes/
        ├── reports/
        │   ├── tables/
        │   └── figures/
        └── logs/
```

Legacy thesis paths remain inside the same run directory. Canonical copies are
additive and are the paths recorded in `manifest.json` for future API and
report consumers.

## Implementation

- `src/artifacts/models.py`
  - `RunManifest`
  - `ArtifactRecord`
  - `RunStatus`
  - `ArtifactCategory`
- `src/artifacts/run_manifest.py`
  - run layout creation
  - atomic JSON/YAML writes
  - canonical artifact publication
  - checksum, row-count, schema, and path validation
  - completed and failed lifecycle handling
- Orchestration flows initialize a running manifest and atomically finalize it.
- The existing `ArtifactReference` handoff remains unchanged for Prefect stage
  boundaries.

## Acceptance Criteria

- A successful orchestrated run has one self-contained run directory.
- Every dashboard-facing analytical or visualization artifact is in the run
  manifest.
- A consumer can verify every manifest path, hash, byte size, row count, and
  known schema before reading.
- Existing public CSV paths, columns, and values remain unchanged.
- Canonical report figures are separated from intermediate stage inputs.
- A failed stage writes a `failed` manifest and never leaves `completed` status.
- Manifest and metadata writes are atomic.

## Progress Log

### 2026-07-16

- Added the approved artifact
  and run contract.
- Added the `src.artifacts` package and versioned manifest models.
- Added `<output_base_path>/runs/<run_id>` layout creation.
- Added atomic `manifest.json`, `resolved_config.yaml`, and
  `inputs/datasets.json` persistence.
- Added canonical publication for intermediate, analytical-data, and report
  artifacts while preserving legacy CSV paths.
- Added checksum, byte-size, row-count, path-containment, JSON schema-version,
  and frozen CSV-column validation.
- Integrated running/completed/failed manifest lifecycle handling into both
  monthly orchestration flows.
- Added focused unit coverage in `tests/unit/test_run_manifest.py`.

## Validation Record

### 2026-07-16

Passed in the available offline environment:

```bash
python -m compileall -q src tests
python -m pytest -q \
  tests/unit/test_run_manifest.py \
  tests/unit/test_orchestration_models.py \
  tests/unit/test_output_artifact_contract.py \
  tests/unit/test_artifact_index.py \
  tests/unit/test_tracking_summaries.py
```

Result: `30 passed`.

Additional local checks covered Python compilation, YAML/TOML parsing, trailing
whitespace, conflict markers, success lifecycle finalization, failed lifecycle
finalization, source-metadata consistency, and secret-free resolved
configuration. The protected thesis-default and no-absolute-source-path tests
also passed (`8 passed`).

The full Prefect integration suite was not executable in this sandbox because
Prefect was not installed and the environment could not download locked
packages. The existing Prefect integration tests were updated for the new
`runs/<run_id>` root and canonical manifest assertions and must be run with:

```bash
make format
make lint
make test
```

in the repository's normal dependency-complete development environment.
