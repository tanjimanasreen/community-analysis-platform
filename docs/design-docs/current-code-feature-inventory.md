# Current Code Feature Inventory

This file records the implemented features found in the existing thesis codebase. The production rebuild must cover these features unless the human explicitly removes one.

Current `GraphRepository` configuration is environment-driven through `GRAPH_DB_*`.
Analytical YAML `database:` sections are rejected, and backend selection is routed
through the repository resolver; Memgraph is currently implemented/default while
the abstraction remains open to future graph databases.

## Top-Level Scripts

### `neo4j_data_fetcher.py`

Implemented behavior:

- Connects to Neo4j using `neo4j.GraphDatabase`.
- Verifies database connectivity.
- Provides query templates for:
  - Telegram monthly data.
  - Twitter retweet/quote data.
  - Twitter reply data.
- Uses date-bounded Cypher queries with `UNION` across relationship types.
- Exports query records to CSV with columns:
  - `source`
  - `target`
  - `relation`
- Thesis-era credentials and URI were hard-coded; the productionized runtime now
  uses environment-driven `GraphRepository` settings. Memgraph is the current
  default repository backend, while Neo4j remains historical/export-migration
  context.

### `social-network-analysis.py`

Implemented behavior:

- Defines dataset parameters for Twitter reply data.
- Contains commented Telegram parameter block.
- Loads exported relationship CSV.
- Splits relationship rows into creator and spreader dataframes.
- Builds a unique user dataframe.
- Converts Neo4j stringified datetime structures.
- Parses stringified node dictionaries into normalized network dataframe.
- Builds follower-followee edge dataframe.
- Runs language detection for non-Telegram data.
- Saves language-detected network data.
- Builds two NetworkX graphs:
  - absolute graph using `shared_post`
  - weighted graph using `weighted_post`
- Runs Louvain community detection on both graphs.
- Filters prominent communities by minimum member count.
- Extracts community edge dataframes.
- Extracts community messages.
- Computes in-degree and out-degree centrality summaries.
- Computes user/message count summaries.
- Computes daily message statistics inside prominent communities.
- Finds exact and partial matches between absolute and weighted communities.
- Saves matched and partially matched community summaries.
- Preprocesses community message text.
- Runs unigram LDA for absolute and weighted communities.
- Runs bigram LDA for absolute and weighted communities.
- Saves LDA perplexity and coherence scores.
- Extracts matched-community LDA topics and keywords.
- Extracts partially matched-community LDA topics and keywords.
- In the productionized pipeline, the shared Telegram network-analysis boundary
  accepts either legacy `source,target,relation` relationship rows or already
  normalized `from_id,forwarder_id` rows. Legacy rows reuse the canonical
  ingestion mapping before the unchanged follower-followee IF/WIF calculation,
  so direct CLI, debug, Prefect, and programmatic pipeline entry points share the
  same normalization behavior.

### `theme-analysis.py`

Implemented behavior:

- Loads monthly matched LDA Parquet files.
- Sorts months using a predefined month order.
- Parses stringified list columns.
- Combines absolute/weighted unigram/bigram keywords.
- Creates:
  - `all_keywords`
  - `absolute_keywords`
  - `weighted_keywords`
- Generates theme labels through the provider abstraction from ordered LDA keyword lists.
- The provider-facing theme contract uses centrally versioned Prompt V3 and returns theme names
  plus request-bounded, explicitly displayed zero-based keyword indices; exact supporting LDA
  keywords are reconstructed locally without sanitizing or rewriting them. Typed provider safety
  outcomes are recoverable per payload and are recorded in
  `theme_generation_provenance.parquet`; unexpected errors remain fail-fast.
- Current production routing selects `openai:gpt-5-nano` from `configs/providers.yml`;
  the OpenAI adapter uses the Responses API with strict JSON Schema structured output.
- Provider routing belongs to `theme_provider`; run-config validation rejects legacy
  `theme.fallback` and `theme.fallback_chain` keys instead of silently ignoring them.
- Generates:
  - general themes
  - absolute themes
  - weighted themes
- Saves monthly theme Parquet files.
- Loads generated theme Parquet files.
- Matches communities across consecutive months using Jaccard similarity over member lists.
- Requires positive member overlap (`Jaccard > 0`) for every transition.
- Uses threshold `0.0` for `reply` content, so any positive Jaccard score qualifies;
  uses an inclusive `0.5` threshold otherwise.
- Saves `community_transition.parquet`.
- Builds Sankey node/link information.
- Draws and saves community transition Sankey diagrams as PNG and HTML.
- Builds a directed graph from Sankey links.
- Finds all paths from start communities to end communities.
- Calculates new, lost, existing, and reappearing members across paths.
- Draws membership transition diagrams.
- Uses SentenceTransformer `paraphrase-MiniLM-L6-v2`.
- Computes cosine similarity between theme sentences.
- Draws heatmaps for:
  - absolute themes
  - weighted themes
  - general themes

## Utility Modules

### `utils/network_data_extractor.py`

Implemented behavior:

- Converts anonymous usernames into `anonymous<user_id>`.
- Splits creator/spreader relationships.
- Creates unique user dataframe from creator and spreader nodes.
- Converts Neo4j datetime string representations.
- Parses stringified node dictionaries.
- Creates normalized network dataframe.
- Computes follower-followee edge rows.
- Removes self-forward/self-spread rows.
- Calculates:
  - `total_post`
  - `shared_post`
  - `weighted_post = shared_post / total_post`

### `utils/network_graph.py`

Implemented behavior:

- Filters edges before graph construction:
  - `min_total_post = 10`
  - `min_shared_post = 5`
- Builds `nx.MultiDiGraph` absolute graph using `shared_post`.
- Builds `nx.MultiDiGraph` weighted graph using `weighted_post`.
- Prints graph metadata.
- Computes out-degree centrality summary.
- Computes in-degree centrality summary.

### `utils/community_generator.py`

Implemented behavior:

- Runs NetworkX Louvain community detection with:
  - `resolution=1`
  - `seed=123`
  - configurable weight field
- Filters communities by minimum member count.
- Converts prominent community subgraphs into edge dataframes.
- Extracts per-community producer/forwarder message details.
- Aggregates community messages and message IDs.
- Computes centrality over prominent community subgraphs.
- Computes daily message statistics for communities.

### `utils/similarity_detector.py`

Implemented behavior:

- Extracts unique members per community.
- Computes Jaccard similarity.
- Finds exact absolute/weighted community matches where Jaccard score equals `1`.
- Finds partial matches where `0 < Jaccard score < 1`.
- Returns unmatched absolute and weighted communities.

### `utils/text_preprocessor.py`

Implemented behavior:

- Loads custom stopword list from `utils/stopwords-list.txt`.
- Removes usernames, URLs, hashtags, selected punctuation, laughter patterns, non-letter characters, stopwords, and repeated words.
- Removes emojis using `demoji`.
- Cleans HTML with BeautifulSoup.
- Normalizes Unicode.
- Joins community messages into a cleaned text document.

### `utils/lda_analysis.py`

Implemented behavior:

- Loads spaCy `en_core_web_sm`.
- Sets `nlp.max_length = 5000000`.
- Uses `num_topics = 15`.
- Uses `topN_keywords = 50`.
- Lemmatizes tokens.
- Trains Gensim LDA with:
  - `random_state=100`
  - `iterations=100`
  - `chunksize=20`
  - `passes=80`
  - `alpha='auto'`
  - `eta='auto'`
- The current production rebuild intentionally uses Gensim `LdaMulticore` with
  `alpha='symmetric'` and `eta='auto'`: automatic alpha optimization is not
  supported by `LdaMulticore`, while automatic eta remains supported. All other
  thesis-aligned LDA defaults above remain unchanged, and worker selection is
  left to `LdaMulticore` unless explicitly configured.
- Computes perplexity and `c_v` coherence.
- Assigns dominant topic to each community document.
- Builds unigram topic model outputs.
- Builds bigram/trigram-enhanced topic model outputs.
- Uses KneeLocator to choose keyword probability cutoff.
- Produces matched-topic dataframe for absolute/weighted unigram/bigram topics.

### `utils/lang_detector.py`

Implemented behavior:

- Removes URLs.
- Detects English using `langdetect`.
- Uses deterministic `DetectorFactory.seed = 0`.
- Adds `text_translated` and `is_english` columns.

### `utils/lang_translator.py`

Implemented behavior:

- Uses `deep_translator.GoogleTranslator`.
- Translates non-English text to English.
- Adds `is_translated`.
- Sleeps between translation calls.

## Existing Output Categories

The production rebuild preserves these output categories while replacing the
legacy generated CSV serialization with Parquet. Raw `data/raw/**` relationship
inputs remain CSV. Generated tabular categories are:

- `network_data/<content_type>/<month><year>.parquet`
- `user_centrality/<content_type>/<month>.parquet`
- `count_user_messages/<content_type>/<month>.parquet`
- `daily_messages_stat/<content_type>/<month>.parquet`
- `communities/matched/<content_type>/<month>.parquet`
- `communities/partially_matched/<content_type>/<month>.parquet`
- `LDA/scores/<content_type>/<month>.parquet`
- `LDA/matched/<content_type>/<month>_<year>.parquet`
- `LDA/partial_matched/<content_type>/<month>_<year>.parquet`
- `LDA/matched_theme/<content_type>/<month>_theme.parquet`
- `LDA/community_transition/<content_type>/community_transition.parquet`
- `LDA/community_transition/<content_type>/community_transition.png`
- `LDA/community_transition/<content_type>/community_transition.html`
- `LDA/membership_change_graphs/<content_type>/community_changes_<n>.png`
- `LDA/theme_similarity/<content_type>/absolute_theme.png`
- `LDA/theme_similarity/<content_type>/weighted_theme.png`
- `LDA/theme_similarity/<content_type>/general_theme.png`
