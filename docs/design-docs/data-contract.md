# Data Contract

This document defines the data model for the community‑analysis project.  It
describes the **raw graph** imported from external sources (Telegram and
Twitter/X), the **derived interaction graph** used for analysis, the
**analysis results** produced by the pipeline, and the **run/provenance**
metadata.  The goal of this contract is to make explicit the entities,
relationships, and fields so that future developers can implement a new
database backend (e.g. Memgraph) without guessing.  Keep this file in
sync with `database-contract.md` and `metric-contract.md`.

## 1. Raw Graph

The raw graph represents the source‑platform entities and their
relationships.  It preserves provenance and platform‑specific semantics.
Nodes and relationships in the raw graph should never be inferred from
analysis results; they come directly from the original data export.

### 1.1 Telegram

**Node labels and required properties**

| Label               | Properties                 | Notes                                                       |
|---------------------|----------------------------|-------------------------------------------------------------|
| `User`              | `user_id: str`            | Unique Telegram user identifier.                            |
|                     | `username: str`           | Username or `anonymous<user_id>` when missing.              |
|                     | `platform: str`           | Always `'telegram'`.                                        |
| `Channel`           | `channel_id: str`          | Unique channel identifier.                                  |
|                     | `channel_title: str`       | Channel title.                                              |
|                     | `participants_count: int` | Number of channel subscribers if known.                    |
| `Message`           | `unique_id: str`           | Unique ID for an original message in the current export.     |
|                     | `text: str`               | Message body (may be empty for media).                      |
|                     | `created_at: datetime`     | Message creation timestamp.                                 |
|                     | `from_id: str`             | User who authored the message.                              |
|                     | `channel_id: str`          | Channel where the message was posted.                       |
|                     | `to_id: str`              | Destination identifier if different from `channel_id`.      |
| `Forward_Message`   | `unique_id: str`           | Thesis/export label for a forwarded message.                |
|                     | `text: str`               | Forwarded message body.                                     |
|                     | `created_at: datetime`     | Creation timestamp in the forwarding context.               |
|                     | `forwarded_date: datetime` | Thesis/export field for when the message was forwarded.     |
|                     | `from_id: str`             | Original author of the message (creator).                   |
|                     | `forwarder_id: str`        | User who forwarded the message.                             |
|                     | `channel_id: str`          | Channel where the message was forwarded.                    |
|                     | `views: int`              | Number of views if available.                               |

**Relationships and semantics**

| Relationship              | From               | To                 | Meaning                                                                      |
|---------------------------|--------------------|--------------------|------------------------------------------------------------------------------|
| `CREATED`                 | `User`             | `Message`          | A user authored an original message.                                         |
| `SENT_TO`                | `Message`          | `Channel`          | An original message was posted into a channel.                               |
| `PRODUCED`               | `User`             | `Forward_Message` | A forwarded message originated from a user (as the original author).         |
| `ORIGINATED`             | `Channel`          | `Forward_Message` | A forwarded message originated from a channel (as the original author).       |
| `FORWARDED_BY`           | `Forward_Message`  | `User`            | A forwarded message was forwarded by a user.                                 |
| `FORWARDED_TO`           | `Forward_Message`  | `Channel`         | A forwarded message was forwarded into a destination channel.                 |

### 1.2 Twitter/X

**Node labels and required properties**

| Label           | Properties                          | Notes                                                                           |
|-----------------|--------------------------------------|---------------------------------------------------------------------------------|
| `Twitter_User`  | `user_id: str`                      | Thesis/export label for a unique Twitter user identifier.                       |
|                 | `username: str`                     | Screen name.                                                                    |
|                 | `platform: str`                     | Always `'twitter'`.                                                             |
| `Retweet_Quote` | `unique_id: str`                    | Thesis/export label for a retweet or quote.                                     |
|                 | `text: str`                          | Tweet text.                                                                     |
|                 | `created_at: datetime`               | Creation timestamp.                                                             |
|                 | `from_id: str`                       | Author of the original tweet or quote.                                          |
|                 | `tweet_type: str`                    | `'retweet'` or `'quote'`.                                                       |
|                 | `retweet_count: int`                 | Number of retweets if available.                                                |
|                 | `lang: str`                          | ISO language code if available.                                                 |
|                 | `hashtags: List[str]` (optional)     | List of hashtags.                                                               |
| `Reply`         | `unique_id: str`                     | Unique ID for a reply in the current export.                                    |
|                 | `text: str`                          | Reply text.                                                                     |
|                 | `created_at: datetime`               | Reply timestamp.                                                                |
|                 | `from_id: str`                       | Author of the reply.                                                            |
|                 | `lang: str`                          | ISO language code if available.                                                 |

**Relationships and semantics**

| Relationship      | From             | To               | Meaning                                               |
|-------------------|------------------|------------------|-------------------------------------------------------|
| `TWEETED`         | `Twitter_User`   | `Retweet_Quote`  | A user authored a tweet/quote/retweet.                |
| `RETWEETED_BY`    | `Retweet_Quote`  | `Twitter_User`   | A tweet/quote was retweeted or quoted by a user.      |
| `REPLIED_TO`      | `Reply`          | `Twitter_User`   | A reply is directed to a user being replied to.       |
| `REPLIED_BY`      | `Reply`          | `Twitter_User`   | A reply was authored by a user.                       |

### 1.3 Raw Graph Guidelines

- **Immutability:** The raw graph is append‑only.  Do not update or delete
  nodes/edges retroactively; instead, import new data into new snapshots.
- **Unique identifiers:** Use platform‑provided IDs where available.  If an
  ID is missing, generate a deterministic surrogate (e.g. hash of content).
- **Case normalization:** Store all IDs and usernames in lowercase to avoid
  duplication.
- **Timestamp format:** Use ISO 8601 strings or Python `datetime` objects
  for storage.  Do not cast timestamps to integers.

## 2. Derived Interaction Graph

The derived interaction graph is built from the raw graph to support
community detection and comparison.  Each edge represents an interaction
between two users in a given month and content type.  Self‑interactions
are excluded.

### 2.1 Raw-To-Derived Mapping

The production code must preserve the thesis/export labels used by the
legacy `source,target,relation` CSV files.  The derived monthly interaction
edge is always oriented from the original creator/author/replied-to user to
the spreader/forwarder/retweeter/replier.

| Dataset mapping | `content_type` | `creator_relation` | `spreader_relation` | Source user extraction | Target user extraction | Date field | Output interaction edge fields |
|---|---|---|---|---|---|---|---|
| Telegram forwarding | `forward` | `PRODUCED` | `FORWARDED_BY` | `PRODUCED.source.user_id` | `FORWARDED_BY.target.user_id` | `forwarded_date` | `source`, `target`, `total_post`, `shared_post`, `weighted_post`, `data_type`, `content_type`, `month`, `year` |
| Twitter retweet/quote | `retweet_quote` | `TWEETED` | `RETWEETED_BY` | `TWEETED.source.user_id` | `RETWEETED_BY.target.user_id` | `created_at` | `source`, `target`, `total_post`, `shared_post`, `weighted_post`, `data_type`, `content_type`, `month`, `year` |
| Twitter reply | `reply` | `REPLIED_TO` | `REPLIED_BY` | `REPLIED_TO.target.user_id` | `REPLIED_BY.target.user_id` | `created_at` | `source`, `target`, `total_post`, `shared_post`, `weighted_post`, `data_type`, `content_type`, `month`, `year` |

`shared_post` remains the raw interaction count between `source` and
`target`, and `weighted_post` remains `shared_post / total_post` for the
source user in the snapshot.  Rows where `source == target` are excluded
before creating analytical graph edges.

**Node label**

| Label     | Properties                                       | Notes                                 |
|-----------|---------------------------------------------------|---------------------------------------|
| `User`    | `user_id: str`                                   | Same analytical user identity as raw `User`/`Twitter_User`. |

**Relationship label**

| Label                     | From    | To      | Properties                                        | Notes                                                                 |
|--------------------------|---------|---------|--------------------------------------------------|-----------------------------------------------------------------------|
| `USER_INTERACTED_WITH`   | `User`  | `User`  | `data_type: str`                                 | `'telegram'` or `'twitter'`.                                          |
|                          |         |         | `content_type: str`                              | `'forward'`, `'retweet'`, `'reply'`, `'combined'`, etc.               |
|                          |         |         | `month: int`                                     | Month (1–12) of the snapshot.                                         |
|                          |         |         | `year: int`                                      | Year of the snapshot.                                                  |
|                          |         |         | `shared_post: int`                              | Number of posts from source shared by target.                         |
|                          |         |         | `total_post: int`                               | Total posts created by source in the snapshot.                        |
|                          |         |         | `weighted_post: float`                          | `shared_post / total_post`.  When `total_post == 0`, this is `0`.     |

**Derived Graph Guidelines**

- **Snapshot granularity:** Store snapshot metadata (`month`, `year`,
  `data_type`, `content_type`) on the edge.  Do not infer the snapshot
  from file names when querying the database.
- **Self‑edge exclusion:** Do not create edges where the source and target
  are the same user.
- **Edge aggregation:** If the same pair of users appears multiple times
  within a snapshot, aggregate counts into a single edge with updated
  `shared_post` and `total_post` values.

## 3. Analysis Results

Analysis results are produced after running the pipeline.  They may be
stored in the graph database, relational tables, or exported CSVs.  The
schema here is provided to make explicit what information must be
preserved.  Implementers may choose a suitable storage mechanism.

### 3.1 Communities

| Entity                | Properties                                                             | Notes                                                                      |
|-----------------------|------------------------------------------------------------------------|----------------------------------------------------------------------------|
| `Community`           | `community_id: str`                                                    | Unique ID per snapshot and metric.                                         |
|                       | `data_type: str`, `content_type: str`, `month: int`, `year: int`        | Snapshot identifiers.                                                       |
|                       | `affinity_metric: str` (`'if'` or `'wif'`)                             | Which metric was used to detect the community.                             |
|                       | `member_count: int`                                                    | Number of users in the community.                                          |
|                       | `message_count: int`                                                   | Number of messages in the community.                                       |

| Relationship              | From        | To          | Properties                           | Notes                                                                                  |
|---------------------------|-------------|-------------|-------------------------------------|----------------------------------------------------------------------------------------|
| `HAS_MEMBER`              | `Community` | `User`      | None                                | Indicates membership; duplicates user across communities when applicable.              |
| `MATCHED_WITH`            | `Community` | `Community` | `jaccard_score: float`             | Links communities detected using different metrics or across months.                   |

### 3.2 Topics and Themes

Topics are derived from the text of community messages using LDA.  Themes are
generated downstream by GPT or rule‑based systems.

| Entity                   | Properties                                                       | Notes                                                          |
|--------------------------|------------------------------------------------------------------|----------------------------------------------------------------|
| `TopicModelRun`          | `run_id: str`                                                    | Unique per LDA configuration and snapshot.                    |
|                          | `num_topics: int`, `top_n_keywords: int`                        | LDA hyperparameters.                                          |
|                          | `perplexity: float`, `coherence: float`                         | Evaluation metrics.                                           |
| `CommunityTopic`         | `community_id: str`, `topic_id: int`                            | Link between community and topic.                            |
|                          | `keywords: List[str]`                                            | Top keywords for the topic.                                   |
|                          | `weight: float` (optional)                                       | Proportion of the community document belonging to the topic.   |
| `ThemeGenerationRun`     | `run_id: str`                                                    | Unique per GPT configuration and snapshot.                    |
|                          | `model: str`, `temperature: float`, `seed: int`                 | GPT parameters.                                               |
| `CommunityTheme`         | `community_id: str`, `theme_type: str`                          | `'general'`, `'absolute'`, or `'weighted'`.                   |
|                          | `theme_names: List[str]`                                         | Names assigned by GPT.                                        |
|                          | `theme_descriptions: List[str]`                                   | Optional descriptive text.                                    |
| `ThemeEmbedding`          | `embedding_key: str`, `text: str`, `embedding: float32[384]` | Content-addressed clustering or similarity vector; profile, model ID/revision, text/vector hashes, dtype, dimensions, normalization and contract versions are persisted. |
| `MonthlyThemeCluster`     | `period: str`, `monthly_cluster_id: str`                    | HDBSCAN cluster over `general_theme_names`; noise is evidence-only. |
|                          | `representative_theme: str`, `source_theme_labels: List[str]`   | Representative is a deterministic semantic medoid.             |
| `CanonicalTheme`         | `canonical_theme_id: str`, `canonical_theme_label: str`        | Run-local cross-month canonical family; Stage-B noise is singleton. |
|                          | `monthly_cluster_ids: List[str]`, `periods: List[str]`         | Stable linkage across monthly semantic clusters.                |
| `CanonicalThemeMonth`    | `canonical_theme_id: str`, `period: str`                       | Monthly reporting record.                                      |
|                          | `community_count: int`, `community_pairs: List[...]`           | Counts distinct matched IF/WIF pairs.                           |
|                          | `prominent_keywords: List[str]`, `percentage: float`           | General LDA evidence and themed-pair denominator.               |

### 3.3 Transitions and Similarity

| Entity                    | Properties                                                      | Notes                                                          |
|---------------------------|-----------------------------------------------------------------|----------------------------------------------------------------|
| `CommunityTransition`     | `start_month: int`, `start_year: int`, `start_comm_id: str`     | Identifies the start community.                              |
|                           | `end_month: int`, `end_year: int`, `end_comm_id: str`           | Identifies the end community.                                |
|                           | `jaccard_score: float`                                         | Jaccard similarity between community members.                |
| `MembershipChange`        | `transition_id: str`, `user_id: str`, `status: str`             | `status` ∈ {`existing`, `new`, `lost`, `reappearing`}.        |
| `ThemeSimilarity`         | `theme_run_id: str`, `snapshot_id: str`, `matrix: List[List[float]]` | Cosine similarity matrix between themes.                      |

## 4. Run/Provenance Metadata

To enable reproducibility, track metadata for every run.

| Entity             | Properties                                                     | Notes                                                     |
|--------------------|----------------------------------------------------------------|-----------------------------------------------------------|
| `AnalysisRun`      | `run_id: str`                                                  | Unique identifier for each full pipeline run.             |
|                    | `start_time: datetime`, `end_time: datetime`                  | Timestamps for run execution.                            |
|                    | `config_hash: str`                                            | Hash of the configuration file used for the run.          |
|                    | `input_path: str`, `output_path: str`                          | Paths to raw input data and output directory.             |
|                    | `status: str` (`'success'`, `'failed'`, `'partial'`)           | Run status.                                               |

Keep run records in a separate collection or table.  They should not
intermix with graph entities.
