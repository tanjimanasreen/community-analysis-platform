# Execution Plan: Data Versioning and Lineage Foundation with DVC

## 1. Goal
Introduce a safe DVC foundation that protects the existing 11 GB raw dataset from accidental Git commits. Migrate the generic `dataset/` directory to the project’s standardized `data/raw/` structure, version the immutable raw monthly Twitter datasets with DVC, and update configuration and code references to the new paths. Preserve the current pipeline behavior, add reproducible dataset identity for future Prefect and MLflow integration, and ensure no premature tracking of generated outputs.

## 2. Current-State Findings
- The `dataset/` directory contains ~11 GB of raw relationship CSVs, and `outputs/` contains ~3.9 GB.
- The `twitter/` directory contains 37 MB.
- Active dataset configuration exists under `configs/datasets/`.
- `src/cli.py` is the active CLI; legacy scripts (`social-network-analysis.py`, `theme-analysis.py`) are deleted.
- Large untracked directories (`dataset/` and `twitter/`) exist in the working tree and are not protected by `.gitignore`.

## 3. Data Inventory and Classification Table

| Location / Path | Category | Mutable | Sensitive | DVC Track | Retention Policy | Proposed Target Path |
| --- | --- | --- | --- | --- | --- | --- |
| `dataset/` | Raw immutable inputs | No | Yes (user IDs) | Yes (file-level) | Keep versioned permanently | `data/raw/twitter/retweet_quote/2017/` |
| `outputs/` | Generated outputs | Yes | No | No | Ignored by Git/DVC | (Ignored) |
| `twitter/` | Legacy generated outputs | Yes | No | No | Ignored by Git/DVC | (Ignored) |
| `tests/fixtures/` | Benchmark fixtures | No | No | No (Git tracked) | Track via Git | `tests/fixtures/` |

## 4. Confirmed Dataset Sizes and Locations
- `dataset/retweet_february_2017.csv`: 7.4 GB
- `dataset/retweet_march_2017.csv`: 2.9 GB
- `dataset/retweet_april_2017.csv`: 404 MB
- `dataset/retweet_january_2017_sampled.csv`: 388 KB
- **Total `dataset/`**: ~11 GB

## 5. Current Git and Ignore Findings
- `.gitignore` explicitly ignores `outputs/`, `reports/`, `artifacts/`, and `data/generated/`.
- **Critical Risk**: `dataset/` and `twitter/` are completely untracked and **not** listed in `.gitignore`.

## 6. Proposed Target Data Layout
The raw files will be restructured as follows:
```text
data/
  README.md
  raw/
    twitter/
      retweet_quote/
        2017/
          retweet_january_2017_sampled.csv
          retweet_february_2017.csv
          retweet_march_2017.csv
          retweet_april_2017.csv
```

## 7. Proposed DVC Target Boundaries
Each monthly raw file is tracked as an independent DVC target to avoid massive monolithic pulls:
- `data/raw/twitter/retweet_quote/2017/retweet_january_2017_sampled.csv.dvc`
- `data/raw/twitter/retweet_quote/2017/retweet_february_2017.csv.dvc`
- `data/raw/twitter/retweet_quote/2017/retweet_march_2017.csv.dvc`
- `data/raw/twitter/retweet_quote/2017/retweet_april_2017.csv.dvc`

## 8. DVC versus Prefect Responsibility Boundary
- **DVC**: Owns raw dataset versioning, content hashes, restoration, remote synchronization, and dataset identity.
- **Prefect (Future)**: Will own runtime dependencies, task execution, retries, scheduling, parallelism, and asset materialization. We will not create a `dvc.yaml` pipeline.

## 9. DVC versus MLflow Responsibility Boundary
- **MLflow (Future)**: Will own experiment runs, benchmarking, and tracing.
- **Handoff**: We will define a future lineage contract capable of supplying:
```json
{
  "dataset_name": "twitter_retweet_quote_2017_02",
  "dataset_version": "<content-derived-or-declared-version>",
  "dvc_target": "data/raw/twitter/retweet_quote/2017/retweet_february_2017.csv.dvc",
  "dvc_hash": "<hash-from-dvc-metadata>",
  "git_commit": "<git-sha>",
  "source_path": "data/raw/twitter/retweet_quote/2017/retweet_february_2017.csv",
  "schema_version": "<current-data-contract-version>"
}
```

## 10. Milestones with Exact Files Expected to Change

**Milestone 1: Immediate Git protection**
- Update `.gitignore` with `/dataset/`, `/twitter/`, and `.dvc/config.local`.

**Milestone 2: Add DVC as development tooling**
- Update `pyproject.toml` to include `dvc` in the `dev` dependency group.
- Run `uv sync`.

**Milestone 3: Initialize DVC**
- Initialize DVC (`uv run dvc init`).

**Milestone 4: Create a migration manifest**
- Generate `docs/verification/dvc-migration-manifest.md` containing hashes, byte sizes, and migration status.

**Milestone 5: Pilot the small dataset first**
- Move `retweet_january_2017_sampled.csv` to its target path.
- Validate hashes and size.
- Run `dvc add`, verify `dvc status` and perform a safe restoration checkout test.

**Milestone 6: Migrate the remaining raw files**
- Migrate `retweet_february_2017.csv`, `retweet_march_2017.csv`, and `retweet_april_2017.csv` sequentially.
- Perform size/hash equality checks and `dvc add` for each file individually.

**Milestone 7: Update active path references**
- Update configuration files in `configs/datasets/` and core modules (`src/config/defaults.py`, etc.) with the new paths.

**Milestone 8: Add data-zone documentation**
- Create `data/README.md` to document the new structure.

**Milestone 9: Remote configuration behavior**
- If `DVC_REMOTE_URL` is set, add local remote and push. Otherwise, skip remote backup.

**Milestone 10: Testing and validation**
- Run `make test` or `uv run pytest`.
- Verify Git clean state and DVC status.

## 11. Validation Commands and Expected Outcomes
- `git status --short`: clean or only updated files, no raw CSVs.
- `git check-ignore -v dataset/retweet_february_2017.csv`: must be ignored.
- `dvc version` & `dvc doctor`: Verify reflinks and cache.
- `dvc status`: Should report up-to-date.
- `uv run pytest`: Existing pipeline and benchmark tests pass without error.

## 12. Risks and Mitigations
- **Risk**: Moving 11 GB exhausts disk space if fallback to `copy` is triggered.
  - **Mitigation**: Verify filesystem supports reflinks. Move files one by one. Stop before moving large files if disk capacity is insufficient.

## 13. Rollback Plan
- Restore raw files to their original locations from DVC or backups.
- Revert configuration path updates.
- Revert `.gitignore` changes and DVC initialization via Git.

## 14. Decision Log
- **Decision**: Monthly raw file targets over a monolithic `data/raw/twitter.dvc`.
- **Decision**: No `dvc.yaml` pipeline. Prefect handles orchestration.
- **Decision**: Fixtures remain in Git; generated outputs remain completely unversioned and ignored.

## 15. Progress Log
- [x] Local DVC initialization.
- [x] Raw file migration.
- [x] Checksum verification.
- [x] Local checkout validation.
- [x] Git safety (data ignored, .dvc tracked).
- [ ] Full regression-test status (blocked: 11 test failures. Apparently unrelated to DVC/paths, but not conclusively pre-existing because no pre-Phase-5A test baseline was captured).
- [ ] Remote configuration (pending user configuration).
- [ ] Remote push/pull validation (blocked).
- [ ] Clean-clone restoration (blocked until remote push succeeds).
