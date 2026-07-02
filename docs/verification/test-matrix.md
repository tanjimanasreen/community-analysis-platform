# Test Matrix

## Required Tests By Feature

| Feature | Current code | Required tests |
|---|---|---|
| Neo4j export CSV | `neo4j_data_fetcher.py` | Query config, output columns, no hard-coded credentials. |
| Creator/spreader split | `get_creator_spreader` | Correct relation filtering. |
| User dataframe | `create_user_df` | Unique users, anonymous username normalization. |
| Neo4j datetime conversion | `convert_neo4j_datetime_strings` | Converts string pattern safely. |
| Network dataframe parsing | `create_network_df` | Parses stringified node dictionaries. |
| Follower-followee edges | `get_follower_followee_network` | `shared_post`, `total_post`, `weighted_post`, self-exclusion. |
| Graph construction | `get_network_graph` | Threshold filtering and `MultiDiGraph` output. |
| Centrality summaries | `show_hightest_out_degree`, `show_hightest_in_degree` | Max/min/average values on small graph. |
| Louvain communities | `get_louvain_community` | Uses stable seed and weight column. |
| Prominent community filter | `detect_promiment_communities` | Filters by `min_members`. |
| Community messages | `get_community_messages` | Aggregates messages, IDs, and counts. |
| Daily message stats | `get_overall_community_messages_stat` | Min/max/avg/std by day. |
| Community matching | `find_matching_communities` | Exact, partial, unmatched cases. |
| Language detection | `lang_detection` | URL removal, English flag, empty text behavior. |
| Translation | `lang_translate` | Mock translator, non-English update behavior. |
| Text preprocessing | `message_preprocess` | Emoji removal, HTML cleaning, Unicode normalization, stopword removal. |
| LDA defaults | `get_lda` | Parameters match contract. |
| Unigram LDA | `get_unigram_lda` | Output schema on small corpus. |
| Bigram LDA | `get_bigram_lda` | Bigram token handling and output schema. |
| Keyword cutoff | `get_cutoff_probability` | Knee and fallback behavior. |
| Matched topic export | `get_matched_topic_df` | Absolute/weighted unigram/bigram columns. |
| Theme data loading | `load_prepare_data` | Month sorting and keyword column parsing. |
| GPT theme generation | `generate_gpt_theme` | Mocked provider, JSON parsing, output columns. |
| Month transition | `get_community_transition` | Reply threshold and non-reply threshold. |
| Sankey path info | `get_path_info` | Correct source/target indices. |
| Sankey path detection | `find_all_sankey_paths` | Finds all start-to-end paths. |
| Membership changes | `calculate_membership_changes` | New/lost/existing/reappearing behavior. |
| Theme similarity | `calculate_sentence_similarity` | Matrix shape and similarity bounds. |

## Fixture Strategy

Create tiny fixtures:

- 4 users.
- 2 months.
- 2 content types: `reply` and non-`reply`.
- One exact absolute/weighted community match.
- One partial absolute/weighted community match.
- One unmatched community.
- One self-spread row to verify exclusion.
- Enough repeated rows to test graph thresholds.

## No-Network Test Rules

Unit tests must not:

- Call Neo4j.
- Call Memgraph unless marked integration.
- Call OpenAI.
- Download SentenceTransformer models unless marked slow/integration.
- Depend on external drive paths.

Use mocks or cached fixtures for those cases.

