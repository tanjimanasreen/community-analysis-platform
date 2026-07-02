# Theme Intelligence Contract

This contract covers the implemented features in `theme-analysis.py`.

## Inputs

Theme analysis starts from monthly matched LDA outputs:

```text
<data_type>/LDA/matched/<content_type>/<month>_<year>.csv
```

Required columns:

- `members`
- `absolute_community`
- `weighted_community`
- `absolute_unigram_keywords`
- `absolute_bigram_keywords`
- `weighted_unigram_keywords`
- `weighted_bigram_keywords`

## Keyword Preparation

The current implementation creates:

- `all_keywords`
- `absolute_keywords`
- `weighted_keywords`

Rules:

- Parse stringified list columns with `ast.literal_eval`.
- Combine unigram and bigram keywords.
- De-duplicate keywords while preserving order.
- Convert keyword lists to comma-separated strings for GPT prompting.

## GPT Theme Generation

Current generated theme types:

- `general_theme_gpt`
- `general_theme_names`
- `absolute_theme_gpt`
- `absolute_theme_names`
- `weighted_theme_gpt`
- `weighted_theme_names`

Current GPT behavior:

- Model: `gpt-4o`
- Temperature: `0`
- Seed: `42`
- Response format: JSON object
- Prompt asks for meaningful themes from keyword lists.

Production requirements:

- Wrap GPT calls behind a provider interface.
- Support cached responses.
- Support offline mocked responses for tests.
- Do not require OpenAI for network/LDA pipeline tests.

## Community Transition

Current behavior:

- Compares consecutive months.
- Uses Jaccard similarity over `members`.
- For `reply`, threshold is `0.0`.
- For all other content types, threshold is `0.5`.
- Writes `community_transition.csv`.

Output columns include:

- `start_month`
- `end_month`
- `start_month_community`
- `end_month_community`
- `jaccard_score`
- `common_members`
- `uncommon_members`
- `start_month_members`
- `total_start_month_members`
- `end_month_members`
- `total_end_month_members`
- theme fields for absolute, weighted, and general themes

## Sankey Transition Diagram

Current behavior:

- Builds source and target indices from transition rows.
- Uses month-specific node colors.
- Uses link intensity based on Jaccard score.
- Saves:
  - `community_transition.png`
  - `community_transition.html`

Production requirements:

- Keep static image export optional because Plotly image export may require Kaleido.
- Always save HTML when visualization succeeds.

## Path Detection

Current behavior:

- Builds a directed graph from Sankey source/target links.
- Finds start nodes with zero in-degree.
- Finds end nodes with zero out-degree.
- Uses DFS to find all start-to-end paths.

This feature must be preserved because membership-change and theme-similarity visualizations depend on it.

## Membership-Change Visualization

Current behavior:

- Calculates existing, new, lost, and reappearing members over each detected path.
- Draws per-path diagrams.
- Saves `community_changes_<n>.png`.

Production requirements:

- Preserve the meaning of color categories:
  - green: existing member
  - red: new member
  - grey: reappearing member
- Add tests for membership-change calculations.
- Do not require rendering tests to inspect image pixels in the first production version.

## Theme Similarity

Current behavior:

- Uses SentenceTransformer `paraphrase-MiniLM-L6-v2`.
- Computes cosine similarity between theme sentences.
- Draws upper-triangle heatmaps for:
  - absolute themes
  - weighted themes
  - general themes

Production requirements:

- Make the embedding model configurable.
- Cache model downloads where possible.
- Add a small deterministic test for sentence similarity shape and diagonal behavior.

