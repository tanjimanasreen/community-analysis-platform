# Data Zones

This repository follows a strict data-zone contract to manage reproducible pipelines, caching, and sensitive raw data.

## `data/raw/`
- Contains **immutable, DVC-tracked source data**.
- Raw files **must not** be edited in place under any circumstances.
- Actual raw files are NOT committed to Git. Only the `.dvc` pointer files are tracked in Git.
- **SECURITY WARNING**: Raw datasets contain sensitive social-network information (e.g., user IDs) and **must not be uploaded publicly**.
- `dvc pull` requires a configured private remote (e.g., local external drive or secure cloud bucket).

## `data/interim/`
- For disposable, reproducible intermediate data generated during the pipeline.
- Ignored by Git. Not tracked by DVC.

## `data/processed/`
- Will contain selected canonical analytical assets (e.g., final graph outputs, community mapping).
- Tracked by DVC where datasets are large or expensive to reproduce.

## Generated Outputs
- `outputs/` remains the current location for generated pipeline run-outputs and artifacts.
- These are ignored by Git and generally not tracked by DVC (they will eventually be managed by MLflow or Prefect).

## Testing Data
- Small CI fixtures remain under `tests/fixtures/` and are tracked directly in Git since they are small, anonymized/synthetic, and necessary for tests to run without DVC access.
