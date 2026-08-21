# Output Artifact Contract

This contract defines the generated analytical outputs and internal handoff
artifacts used by the production and offline sample pipelines. Raw external
relationship inputs remain CSV under `data/raw/**`; generated analytical and
intermediate tabular artifacts are Parquet. Public outputs are compatibility
surfaces for reports, dashboards, APIs, and future object-storage deployment.
Internal outputs are additive stage contracts used by separated CLI commands.

FR-004 explicitly supersedes the earlier generated-CSV compatibility promise.
Do not rename generated Parquet files or remove public columns without a new
migration plan. Internal incompatible changes must bump `schema_version`.

## Generated Analytical Outputs

Path patterns use:

- `<base>`: `output_base_path`
- `<data_type>`: `telegram` or `twitter`
- `<content_type>`: `forward`, `reply`, `retweet_quote`, or related thesis content type
- `<month>`: normalized configured month, such as `03`
- `<year>`: configured year, such as `2017`
- `<theme_output>`: `theme.output_dir`

| Artifact | Path Pattern | Producer | Consumer | Required Columns |
|---|---|---|---|---|
| Normalized network data | `<base>/<data_type>/network_data/<content_type>/<month><year>.parquet` | `run-social-network` | Network/community inspection | `unique_id`, `from_id`, `forwarder_id`, `text`, plus the canonical event timestamp (`forwarded_date` for Telegram forwarding; `created_at` for Twitter workflows) |
| Absolute community graph | `<base>/<data_type>/communities/graphs/absolute/<content_type>/<month>.parquet` | `run-social-network` | Reports/API/frontend | `source`, `target`, `community_number`, `direction`, `weight` |
| Weighted community graph | `<base>/<data_type>/communities/graphs/weighted/<content_type>/<month>.parquet` | `run-social-network` | Reports/API/frontend | `source`, `target`, `community_number`, `direction`, `weight` |
| Matched community summary | `<base>/<data_type>/communities/matched/<content_type>/<month>.parquet` | `run-social-network` | Reports/API/frontend | `month`, `total_matched`, `total_absolute`, `total_weighted` |
| Partially matched communities | `<base>/<data_type>/communities/partially_matched/<content_type>/<month>.parquet` | `run-social-network` | Reports/API/frontend | `month`, `absolute`, `weighted`, `jaccard_score` |
| User centrality | `<base>/<data_type>/user_centrality/<content_type>/<month>.parquet` | `run-social-network` | Reports/API/frontend | `month`, `absolute`, `weighted` |
| User/message counts | `<base>/<data_type>/count_user_messages/<content_type>/<month>.parquet` | `run-social-network` | Reports/API/frontend | `month`, `user`, `messages` |
| Daily message stats | `<base>/<data_type>/daily_messages_stat/<content_type>/<month>.parquet` | `run-social-network` | Reports/API/frontend | `month`, `absolute`, `weighted` |
| LDA scores | `<base>/<data_type>/LDA/scores/<content_type>/<month>.parquet` | `run-topics` | Reports | `month`, `unigram_absolute`, `unigram_weighted`, `bigram_absolute`, `bigram_weighted` |
| Matched LDA topics | `<base>/<data_type>/LDA/matched/<content_type>/<month>_<year>.parquet` | `run-topics` | `run-theme-analysis`, reports | `absolute_community`, `absolute_unigram_topic`, `absolute_unigram_keywords`, `weighted_community`, `weighted_unigram_topic`, `weighted_unigram_keywords`, `absolute_bigram_topic`, `absolute_bigram_keywords`, `weighted_bigram_topic`, `weighted_bigram_keywords`, `members` |
| Partial matched LDA topics | `<base>/<data_type>/LDA/partial_matched/<content_type>/<month>_<year>.parquet` | `run-topics` | Reports | matched LDA columns plus `absolute_members`, `weighted_members`, `jaccard_score`, `common_members`, `uncommon_members` |
| Themed monthly output | `<theme_output>/<month>_<year>_with_themes.parquet` | `run-theme-analysis` | Reports/API/frontend | matched LDA columns plus `all_keywords`, `absolute_keywords`, `weighted_keywords`, `general_theme_gpt`, `general_theme_names`, `absolute_theme_gpt`, `absolute_theme_names`, `weighted_theme_gpt`, `weighted_theme_names` |
| Theme generation provenance | `<theme_output>/theme_generation_provenance.parquet` | `run-theme-analysis` | Research audit/coverage | one row per source assignment with period/community/mode, exact ordered provider keywords, input/prompt hashes, prompt/output contract versions, generation status, safe failure category/stage, configured provider/model, and filter summary |
| Community transitions | `<theme_output>/community_transition.parquet` | `run-theme-analysis` | Sankey, membership changes, reports | `start_month`, `end_month`, `start_month_community`, `end_month_community`, `jaccard_score`, `common_members`, `uncommon_members`, `start_month_members`, `total_start_month_members`, `end_month_members`, `total_end_month_members`, `start_month_absolute_theme`, `end_month_absolute_theme`, `start_month_weighted_theme`, `end_month_weighted_theme`, `start_month_general_theme`, `end_month_general_theme` |
| Artifact index | configured report path, such as `/tmp/community-analysis-artifact-index.md` | `build-report` | Human review | Markdown file |

Partially matched outputs are optional because tiny fixtures may not produce
partial matches. When present, their schemas are verified.

Visualization outputs under `sankey/`, `membership_changes/`, and
`theme_similarity/` are optional. The offline samples keep `render_visuals:
false`, so these files are not required by unit tests or sample contract
verification.

## Internal Intermediate Outputs

### Topic Inputs

Path:

```text
<base>/<data_type>/_intermediate/topic_inputs/<content_type>/<month>_<year>/
```

Producer: `run-social-network`

Consumer: `run-topics`

Files:

| File | Required Columns |
|---|---|
| `absolute_community_messages.parquet` | `community_number`, `messages`, `messages_ids`, `total_messages` |
| `weighted_community_messages.parquet` | `community_number`, `messages`, `messages_ids`, `total_messages` |
| `matched_communities.parquet` | `abs_community`, `per_community`, `jaccard_score`, `members` |
| `partial_matched_communities.parquet` | `abs_community`, `absolute_members`, `per_community`, `weighted_members`, `jaccard_score`, `common_members`, `uncommon_members` |
| `manifest.json` | `schema_version`, `data_type`, `content_type`, `month`, `year`, `files` |

Current `schema_version`: `1`

List-like columns must round-trip as lists when loaded.

### Theme Inputs

Path:

```text
<base>/<data_type>/_intermediate/theme_inputs/<content_type>/<year>/
```

Producer: `run-topics`

Consumer: `run-theme-analysis`

Files:

| File | Required Columns |
|---|---|
| `<month>_<year>.parquet` | same columns as public matched LDA topics |
| `manifest.json` | `schema_version`, `data_type`, `content_type`, `year`, `months`, `filenames`, `hashes`, `created_by`, `lda` |

Current `schema_version`: `1`

Theme input Parquet files are schema-equivalent copies of the generated matched LDA Parquet files. The
manifest stores SHA256 hashes for each copied Parquet, and manifest-mode loading
must fail if a hash changes.

## Verification Commands

One-month sample:

```bash
make run-pipeline-sample
make verify-output-contract
```

Evolution sample:

```bash
make run-evolution-pipeline-test
make verify-evolution-output-contract
```

Verification is read-only. It validates generated artifacts and never reruns
network, community, topic, theme, database, OpenAI, model-download, or
visualization stages.

## Run-Scoped Artifact Bundle

Prefect-orchestrated runs are stored below:

```text
<output_base_path>/runs/<pipeline_run_id>/
```

Each run contains:

- `manifest.json`: versioned run status, lineage, and canonical artifact records;
- `resolved_config.yaml`: recursively secret-free resolved configuration;
- `inputs/datasets.json`: portable dataset identity and DVC metadata;
- `intermediate/`: stage handoffs for topic and theme processing;
- `data/`: published analytical tables for APIs, dashboards, reports, and notebooks;
- `reports/`: human-facing figures and future report bundles;
- `logs/`: reserved run-scoped application logs.

The canonical folders remain additive publication views. Generated analytical
files are Parquet at both the domain-output and canonical run-artifact boundaries;
new runs do not emit generated CSV compatibility copies.

### Run Manifest Lifecycle

The run manifest uses schema version `1.0` and one of these statuses:

- `running`: initialized before analytical stages execute;
- `completed`: written only after canonical artifacts validate successfully;
- `failed`: terminal status containing safe failure type/category metadata.

Each artifact record contains:

- stable artifact key;
- relative canonical path;
- category (`intermediate`, `data`, or `report`);
- producer stage;
- media type and schema version;
- SHA-256 digest;
- byte size;
- row count for tabular Parquet artifacts.

Manifest readers must reject absolute paths, parent traversal, symlink escape,
checksum mismatches, byte-size mismatches, row-count mismatches, and known Parquet
schema violations before loading data.
