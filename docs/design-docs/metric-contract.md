# Metric And Algorithm Contract

This file protects implemented thesis behavior from accidental drift.

## Edge Metrics

The existing code calculates two edge metrics in `utils/network_data_extractor.py`.

### `shared_post`

Meaning:

- Number of posts/messages from a source user that were shared, forwarded, replied to, retweeted, or otherwise spread by a target user within the configured dataset/month.

Current calculation:

```text
shared_post = count(rows where from_id == source_user and forwarder_id == target_user)
```

Current function:

```text
extract_network_structure(df_network, followee_id)
```

### `weighted_post`

Meaning:

- Share of the source user's total posts that were spread by a specific target user.

Current calculation:

```text
total_post = count(rows where from_id == source_user)
weighted_post = shared_post / total_post
```

Current function:

```text
extract_network_structure(df_network, followee_id)
```

### Self-Spread Exclusion

Current behavior:

```text
target != followee_id
```

The production rebuild must preserve this exclusion unless a documented experiment changes it.

## Graph Filtering Thresholds

Current implementation location:

```text
utils/network_graph.py
```

Current defaults:

```text
min_total_post = 10
min_shared_post = 5
```

Filtering rule:

```text
keep edge when total_post >= 10 and shared_post >= 5
```

The production version may make these configurable, but the defaults must remain the same.

## Graph Types

Current graph construction:

```text
G_absolute = nx.from_pandas_edgelist(data, "source", "target", ["shared_post"], create_using=nx.MultiDiGraph())
G_percentage = nx.from_pandas_edgelist(data, "source", "target", ["weighted_post"], create_using=nx.MultiDiGraph())
```

Required production naming:

| Current name | Meaning | Stable production alias |
|---|---|---|
| `G_absolute` | Graph weighted by `shared_post` | `absolute_graph` |
| `G_percentage` | Graph weighted by `weighted_post` | `weighted_graph` |

Do not rename output columns without compatibility mapping.

## Louvain Community Detection

Current implementation:

```text
nx.community.louvain_communities(G, weight=weight, resolution=1, seed=123)
```

Required defaults:

| Parameter | Value |
|---|---|
| `resolution` | `1` |
| `seed` | `123` |
| absolute weight | `shared_post` |
| weighted weight | `weighted_post` |

## Prominent Community Filter

Current default in `social-network-analysis.py`:

```text
min_members = 3
```

The production version may expose this in config, but the default must remain `3`.

## Community Similarity

Current exact/partial comparison between absolute and weighted communities:

- Exact match: Jaccard score equals `1`.
- Partial match: `0 < Jaccard score < 1`.

Current transition comparison across months in `theme-analysis.py`:

- For `reply`: threshold is `0.0`.
- For other content types: threshold is `0.5`.

## LDA Parameters

The thesis-era `utils/lda_analysis.py` configuration used `alpha='auto'` and
`eta='auto'`. The production rebuild retains Gensim `LdaMulticore`; because
`LdaMulticore` cannot optimize `alpha='auto'`, the approved production contract
uses a fixed symmetric alpha prior while preserving supported `eta='auto'`.
No default worker count is declared, so `LdaMulticore` retains its existing
worker-selection behavior unless an experiment explicitly configures `workers`.

Required production defaults:

| Parameter | Value |
|---|---|
| `implementation` | `ldamulticore` |
| `num_topics` | `15` |
| `topN_keywords` | `50` |
| `random_state` | `100` |
| `iterations` | `100` |
| `chunksize` | `20` |
| `passes` | `80` |
| `alpha` | `symmetric` |
| `eta` | `auto` |
| coherence | `c_v` |
| spaCy model | `en_core_web_sm` |
| `nlp.max_length` | `5000000` |

## Topic Keyword Cutoff

Current matched-topic keyword extraction uses KneeLocator:

- curve: `convex`
- direction: `decreasing`
- `S=3`
- fallback: top 10 percent cutoff

Preserve this behavior in the production rebuild.

## GPT Theme Parameters

Current implementation:

```text
theme-analysis.py
```

Required defaults:

| Parameter | Value |
|---|---|
| model | `gpt-4o` |
| seed | `42` |
| temperature | `0` |
| response format | JSON object |

OpenAI calls must be optional in tests and local offline runs.
