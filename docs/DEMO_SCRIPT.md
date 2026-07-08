# Demo Script

This script is for a local, offline-safe project demo. It shows the separated
pipeline, output verification, read-only API, and read-only dashboard without
requiring Neo4j, Memgraph, Docker, OpenAI, model downloads, or Kaleido.

## 1. Setup

From a fresh checkout:

```bash
make install-dev
make frontend-install
```

Explain:

- Python dependencies are installed from `pyproject.toml`.
- Frontend dependencies are installed from `frontend/package-lock.json`.
- Generated folders such as `.venv/`, `frontend/node_modules/`, and
  `frontend/dist/` are not committed.

## 2. Generate And Verify Demo Artifacts

Run:

```bash
make demo
```

Explain:

- The one-month sample is generated from checked-in fixtures.
- The longitudinal sample generates March and April 2017 artifacts.
- Output-contract verification checks public CSV schemas, internal manifests,
  and theme-input hashes.
- The API smoke test proves the read-only artifact API can browse generated
  outputs.

Expected output locations:

```text
/tmp/community-analysis-sample/
/tmp/community-analysis-theme-sample/
/tmp/community-analysis-artifact-index.md
/tmp/community-analysis-longitudinal-sample/
/tmp/community-analysis-longitudinal-theme-sample/
/tmp/community-analysis-longitudinal-artifact-index.md
```

## 3. Start The Read-Only API

Terminal 1:

```bash
make demo-api
```

Explain:

- The API serves generated artifacts under `/api/v1`.
- It does not run ingestion, network analysis, LDA, theme generation,
  visualization rendering, database clients, or external services.

Useful endpoint to show:

```text
http://127.0.0.1:8000/api/v1/health
```

## 4. Start The Dashboard

Terminal 2:

```bash
make demo-frontend
```

Open the Vite URL printed by the command.

Explain:

- The dashboard consumes only `/api/v1`.
- It is read-only and has no pipeline-run buttons.
- During local development, Vite proxies `/api` to the FastAPI server.

## 5. Dashboard Walkthrough

Show these areas in order:

1. API status badge: confirms the dashboard can reach the read-only backend.
2. Run selector: switch between the one-month sample and the longitudinal run.
3. Month selector: show exact backend month values such as `03` and `04`.
4. Output Contract card: explain that generated artifacts are schema-checked.
5. Summary cards: show high-level community artifact counts.
6. Communities table: switch between matched and partial modes.
7. LDA Topics table: show matched topics and explain that LDA remains the
   source of topic keywords.
8. GPT Themes table: explain that GPT themes are downstream of LDA keywords and
   are mocked/offline-safe in the demo.
9. Community Transitions table: show longitudinal month-to-month transition
   rows from generated artifacts.
10. Artifact Metadata table: show known generated files and relative paths.
11. Optional Visualization Files: explain that missing optional files are
    expected when visual rendering is disabled.

## 6. How To Explain The Outputs

- Network/community outputs come from monthly user-user interaction graphs.
- `shared_post` is the raw interaction count, and `weighted_post` is
  `shared_post / total_post`.
- `run-social-network` produces public network/community CSVs and internal
  topic inputs.
- `run-topics` is topic-only: it loads saved topic inputs and writes LDA
  outputs plus internal theme inputs.
- `run-theme-analysis` is theme-only: it loads saved LDA/theme inputs and
  writes theme and transition outputs.
- `verify-output-contract` is read-only and checks that generated artifacts
  match the frozen contract.

## 7. Cleanup

After the demo:

```bash
make clean-generated
make clean-cache
```

These commands remove known generated demo outputs and caches. They do not
remove `.venv/` or `frontend/node_modules/`.
