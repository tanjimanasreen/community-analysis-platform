> Replace `<YOUR_DATA_DIR>` with the absolute path to your local data directory,
> e.g. `export DATA_DIR=/path/to/data` and use `$DATA_DIR` in shell commands.

# Retweet 2017 Custom Dataset Runbook

This runbook records the commands for the Jan-April 2017 Twitter
retweet/quote dataset.

## Dataset Files

```text
<YOUR_DATA_DIR>/twitter-neo4j/monthly_retweet/retweet_january_2017.csv
<YOUR_DATA_DIR>/twitter-neo4j/monthly_retweet/retweet_february_2017.csv
<YOUR_DATA_DIR>/twitter-neo4j/monthly_retweet/retweet_march_2017.csv
<YOUR_DATA_DIR>/twitter-neo4j/monthly_retweet/retweet_april_2017.csv
```

## Config Files

```text
configs/my_retweet_january_2017.yml
configs/my_retweet_february_2017.yml
configs/my_retweet_march_2017.yml
configs/my_retweet_april_2017.yml
```

All four configs should share:

```yaml
data_type: twitter
content_type: retweet_quote
output_base_path: outputs/my-retweet-2017/

creator_relation: TWEETED
spreader_relation: RETWEETED_BY
creator_node_column: source
spreader_node_column: target
text_node_column: target
date_column: created_at

theme:
  enable_gpt: false
  output_dir: outputs/my-retweet-2017-theme/
  year: "2017"
  render_visuals: false
```

Use thesis thresholds unless intentionally testing with tiny/debug data:

```yaml
graph_thresholds:
  min_total_post: 10
  min_shared_post: 5
  min_members: 3
```

## Validate Configs

```bash
.venv/bin/python -m src.cli validate-config --config configs/my_retweet_january_2017.yml
.venv/bin/python -m src.cli validate-config --config configs/my_retweet_february_2017.yml
.venv/bin/python -m src.cli validate-config --config configs/my_retweet_march_2017.yml
.venv/bin/python -m src.cli validate-config --config configs/my_retweet_april_2017.yml
```

## January

```bash
.venv/bin/python -m src.cli ingest-interactions \
  --file <LOCAL_PROJECT_PATH>/Projects/Telegram/cleaned_code/data/twitter-neo4j/monthly_retweet/retweet_january_2017.csv \
  --config configs/my_retweet_january_2017.yml \
  --out outputs/my-retweet-2017/interactions_01_2017.parquet \
  --no-db
```

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp \
.venv/bin/python -m src.cli run-social-network --config configs/my_retweet_january_2017.yml
```

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp \
.venv/bin/python -m src.cli run-topics --config configs/my_retweet_january_2017.yml
```

## February

```bash
.venv/bin/python -m src.cli ingest-interactions \
  --file <LOCAL_PROJECT_PATH>/Projects/Telegram/cleaned_code/data/twitter-neo4j/monthly_retweet/retweet_february_2017.csv \
  --config configs/my_retweet_february_2017.yml \
  --out outputs/my-retweet-2017/interactions_02_2017.parquet \
  --no-db
```

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp \
.venv/bin/python -m src.cli run-social-network --config configs/my_retweet_february_2017.yml
```

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp \
.venv/bin/python -m src.cli run-topics --config configs/my_retweet_february_2017.yml
```

## March

```bash
.venv/bin/python -m src.cli ingest-interactions \
  --file <LOCAL_PROJECT_PATH>/Projects/Telegram/cleaned_code/data/twitter-neo4j/monthly_retweet/retweet_march_2017.csv \
  --config configs/my_retweet_march_2017.yml \
  --out outputs/my-retweet-2017/interactions_03_2017.parquet \
  --no-db
```

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp \
.venv/bin/python -m src.cli run-social-network --config configs/my_retweet_march_2017.yml
```

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp \
.venv/bin/python -m src.cli run-topics --config configs/my_retweet_march_2017.yml
```

## April

```bash
.venv/bin/python -m src.cli ingest-interactions \
  --file <LOCAL_PROJECT_PATH>/Projects/Telegram/cleaned_code/data/twitter-neo4j/monthly_retweet/retweet_april_2017.csv \
  --config configs/my_retweet_april_2017.yml \
  --out outputs/my-retweet-2017/interactions_04_2017.parquet \
  --no-db
```

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp \
.venv/bin/python -m src.cli run-social-network --config configs/my_retweet_april_2017.yml
```

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp \
.venv/bin/python -m src.cli run-topics --config configs/my_retweet_april_2017.yml
```

## Theme Analysis

Run theme analysis once after all months have completed `run-topics`.

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp \
.venv/bin/python -m src.cli run-theme-analysis --config configs/my_retweet_april_2017.yml
```

If theme analysis was already run for an earlier month, rerun it with the April
config after April topics finish. It will read the accumulated year-level theme
inputs and regenerate the theme outputs.

## Verify Outputs

```bash
.venv/bin/python -m src.cli verify-output-contract \
  --config configs/my_retweet_april_2017.yml \
  --longitudinal
```

## Dashboard

Start the read-only API:

```bash
COMMUNITY_ANALYSIS_API_CONFIGS=configs/my_retweet_april_2017.yml \
.venv/bin/python -m uvicorn backend.main:app --reload
```

Start the read-only dashboard in a second terminal:

```bash
make demo-frontend
```

## Expected Outputs

Main outputs:

```text
outputs/my-retweet-2017/
```

Theme outputs:

```text
outputs/my-retweet-2017-theme/
```

Theme input files consumed by `run-theme-analysis`:

```text
outputs/my-retweet-2017/twitter/_intermediate/theme_inputs/retweet_quote/2017/
```

Expected monthly theme files:

```text
outputs/my-retweet-2017-theme/01_2017_with_themes.parquet
outputs/my-retweet-2017-theme/02_2017_with_themes.parquet
outputs/my-retweet-2017-theme/03_2017_with_themes.parquet
outputs/my-retweet-2017-theme/04_2017_with_themes.parquet
outputs/my-retweet-2017-theme/community_transition.parquet
```

## Current Theme Input Counts

After running topics for Jan-April, the saved theme inputs contained:

| Month | Rows passed to theme analysis |
|---|---:|
| 01 | 112 |
| 02 | 184 |
| 03 | 86 |
| 04 | 18 |

These counts are based on files in:

```text
outputs/my-retweet-2017/twitter/_intermediate/theme_inputs/retweet_quote/2017/
```
