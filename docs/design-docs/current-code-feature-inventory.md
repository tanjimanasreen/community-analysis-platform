# Current Code Feature Inventory

This file records the implemented features found in the existing thesis codebase. The production rebuild must cover these features unless the human explicitly removes one.

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
- Current credentials and URI are hard-coded and must be moved to environment/config.

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

### `theme-analysis.py`

Implemented behavior:

- Loads monthly matched LDA CSV files.
- Sorts months using a predefined month order.
- Parses stringified list columns.
- Combines absolute/weighted unigram/bigram keywords.
- Creates:
  - `all_keywords`
  - `absolute_keywords`
  - `weighted_keywords`
- Calls OpenAI Chat Completions to generate JSON theme labels from keyword lists.
- Uses model `gpt-4o`, `seed=42`, `temperature=0`, and JSON response format.
- Generates:
  - general themes
  - absolute themes
  - weighted themes
- Saves monthly theme CSV files.
- Loads generated theme CSV files.
- Matches communities across consecutive months using Jaccard similarity over member lists.
- Uses threshold `0.0` for `reply` content and `0.5` otherwise.
- Saves `community_transition.csv`.
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

The production rebuild must preserve or explicitly replace these outputs:

- `network_data/<content_type>/<month><year>.csv`
- `user_centrality/<content_type>/<month>.csv`
- `count_user_messages/<content_type>/<month>.csv`
- `daily_messages_stat/<content_type>/<month>.csv`
- `communities/matched/<content_type>/<month>.csv`
- `communities/partially_matched/<content_type>/<month>.csv`
- `LDA/scores/<content_type>/<month>.csv`
- `LDA/matched/<content_type>/<month>_<year>.csv`
- `LDA/partial_matched/<content_type>/<month>_<year>.csv`
- `LDA/matched_theme/<content_type>/<month>_theme.csv`
- `LDA/community_transition/<content_type>/community_transition.csv`
- `LDA/community_transition/<content_type>/community_transition.png`
- `LDA/community_transition/<content_type>/community_transition.html`
- `LDA/membership_change_graphs/<content_type>/community_changes_<n>.png`
- `LDA/theme_similarity/<content_type>/absolute_theme.png`
- `LDA/theme_similarity/<content_type>/weighted_theme.png`
- `LDA/theme_similarity/<content_type>/general_theme.png`

