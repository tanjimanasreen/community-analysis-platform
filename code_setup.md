# Community Analysis Setup

This document describes how to set up and run the modernized project locally.
The default workflow is offline and does not require Neo4j, Memgraph, Docker,
OpenAI, Hugging Face model downloads, or Kaleido.

## 1. Create The Python Environment

From the project root:

```bash
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
```

The Makefile uses `.venv/bin/python` by default, so keep the virtual
environment at `.venv` unless you also override `PYTHON`.

## 2. Validate The Local Install

Run the unit tests and sample config validation:

```bash
make test
make validate-config
```

The same commands can be run directly:

```bash
.venv/bin/python -m pytest tests/unit
.venv/bin/python -m src.cli validate-config --config configs/sample_twitter_reply.yml
```

## 3. Run The Offline Sample Pipeline

Run the full fixture-backed sample:

```bash
make run-pipeline-sample
```

This runs:

- raw `source,target,relation` CSV to derived interaction CSV conversion
- social network/community analysis
- topic modeling
- theme intelligence with GPT disabled
- artifact index generation

Generated sample outputs are written to:

```text
/tmp/community-analysis-sample/
/tmp/community-analysis-theme-sample/
/tmp/community-analysis-sample-interactions.csv
/tmp/community-analysis-artifact-index.md
```

Run the two-month longitudinal sample with:

```bash
make run-longitudinal-sample
```

Longitudinal sample outputs are written to:

```text
/tmp/community-analysis-longitudinal-sample/
/tmp/community-analysis-longitudinal-theme-sample/
/tmp/community-analysis-longitudinal-artifact-index.md
```

## 4. Run Individual Offline Stages

```bash
make ingest-sample
make run-network-sample
make run-topic-sample
make run-theme-sample
make run-longitudinal-sample
make verify-output-contract
make verify-longitudinal-output-contract
make build-report
```

`run-network-sample` stops after network/community outputs and writes internal
topic-input prerequisites. `run-topic-sample` loads those saved prerequisites
and runs only LDA/topic modeling. `run-theme-sample` loads saved theme-input
prerequisites created by `run-topic-sample` and runs only theme intelligence.
Run the stages in order, or use `run-pipeline-sample`.

After generating outputs, freeze-check the artifact contracts with:

```bash
make verify-output-contract
make verify-longitudinal-output-contract
```

These commands are read-only. They validate public CSV schemas, internal
topic/theme-input manifests, theme-input SHA256 hashes, and longitudinal
transition output without rerunning pipeline stages.

The default sample stages use tiny checked-in fixtures:

- `tests/fixtures/sample_relationships.csv`
- `tests/fixtures/theme_lda/january_2017.csv`
- `tests/fixtures/theme_lda/february_2017.csv`
- `configs/sample_twitter_reply.yml`

## 5. Direct CLI Commands

```bash
.venv/bin/python -m src.cli ingest-interactions \
  --file tests/fixtures/sample_relationships.csv \
  --config configs/sample_twitter_reply.yml \
  --out /tmp/community-analysis-sample-interactions.csv \
  --no-db

.venv/bin/python -m src.cli run-social-network --config configs/sample_twitter_reply.yml
.venv/bin/python -m src.cli run-topics --config configs/sample_twitter_reply.yml
.venv/bin/python -m src.cli run-theme-analysis --config configs/sample_twitter_reply.yml
.venv/bin/python -m src.cli verify-output-contract --config configs/sample_twitter_reply.yml
.venv/bin/python -m src.cli build-report \
  --config configs/sample_twitter_reply.yml \
  --out /tmp/community-analysis-artifact-index.md
```

`run-topics` expects topic-input artifacts under:

```text
<output_base_path>/<data_type>/_intermediate/topic_inputs/<content_type>/<month>_<year>/
```

Those artifacts are produced by `run-social-network`.

`run-theme-analysis` expects theme-input artifacts under:

```text
<output_base_path>/<data_type>/_intermediate/theme_inputs/<content_type>/<year>/
```

Those artifacts are produced by `run-topics`. You can still set
`theme.input_dir` in a config for manual fixture runs.

## 6. Optional Memgraph Commands

Use these only when Docker is available and you intentionally want the local
graph database path:

```bash
.venv/bin/python -m src.cli db-up
.venv/bin/python -m src.cli db-check --config configs/sample_twitter_reply.yml
```

## 7. Optional Legacy Neo4j Export

The thesis code originally exported relationships from Neo4j. That workflow is
now treated as a migration path rather than the default local sample path.

Configure Neo4j connection values before running export commands. Do not commit
real credentials.

```bash
.venv/bin/python -m src.cli export-graph --config path/to/your_config.yml --output path/to/export.csv
```

The exported CSV must preserve the legacy compatibility columns:

```text
source,target,relation
```

Those files can then be converted into derived interaction metrics with
`ingest-interactions --no-db` for offline use or imported into the configured
graph repository when database integration is intentionally enabled.
