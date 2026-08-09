# Project Spec

## Product Name

Community Analysis Intelligence Platform

## Project Type

Production-ready research engineering rebuild of an existing thesis codebase.

## Current Project Scope

The project analyzes social network interactions from graph-exported relationship data. It supports Telegram-style forwarding networks and Twitter-style reply/retweet/quote networks. It builds weighted directed networks, detects communities, compares absolute and weighted community structures, extracts topics using LDA, generates theme labels using GPT, and analyzes community/theme transitions over time.

## Primary Users

- Researcher who wants to reproduce thesis outputs.
- Developer who wants to modernize and extend the pipeline.
- Portfolio reviewer who wants to see production-quality research engineering.
- Analyst who wants to inspect community and theme changes over time.

## Core User Stories

1. As a researcher, I can reproduce the current network/community/topic/theme outputs from sample data.
2. As a developer, I can run each stage independently through CLI commands.
3. As a reviewer, I can understand the full pipeline from exported graph data to theme transition visualizations.
4. As an analyst, I can compare absolute and weighted communities for the same month.
5. As an analyst, I can compare similar communities across months.
6. As an analyst, I can inspect generated themes and theme similarity over time.
7. As an analyst, I can see all persistent community paths first, then select one path as the shared detail context for structural continuity, member mobility, thematic similarity, and evidence.
8. As a researcher or reviewer, I can understand the thesis aim, exact research questions, methodological workflow, platform network models, and reproducibility contract from one concise visual Methodology page.
9. As an analyst, I can understand how Thematic Analysis results are derived, compare up to five canonical themes per month across variable-length timelines, and navigate from aggregate results through generated-label and LDA evidence without changing analytical outputs.

## Functional Requirements

The system must support:

- Configurable graph export from Neo4j-compatible data.
- Local graph database migration path using Memgraph.
- CSV-based compatibility with the current `source`, `target`, `relation` export format.
- Telegram relationship patterns:
  - `CREATED`
  - `SENT_TO`
  - `PRODUCED`
  - `FORWARDED_BY`
  - `FORWARDED_TO`
  - `ORIGINATED`
- Twitter relationship patterns:
  - `TWEETED`
  - `RETWEETED_BY`
  - `REPLIED_TO`
  - `REPLIED_BY`
- Creator/spreader dataframe extraction.
- User dataframe construction.
- Network dataframe construction from stringified graph nodes.
- Follower-followee edge construction.
- `shared_post` and `weighted_post` metrics.
- Absolute and weighted directed multigraph construction.
- Louvain community detection.
- Prominent community filtering.
- Community message extraction.
- In-degree and out-degree centrality summaries.
- User/message count summaries.
- Daily community message statistics.
- Exact and partial community matching using Jaccard similarity.
- Text preprocessing.
- Unigram LDA.
- Bigram/trigram LDA.
- Perplexity and coherence scoring.
- Matched and partially matched topic comparison.
- GPT theme generation from LDA keyword sets.
- Month-to-month community transition detection.
- Sankey transition diagrams.
- Membership-change diagrams.
- SentenceTransformer theme similarity heatmaps.
- A Community Evolution master-detail dashboard that presents the complete persistent-path landscape before a single URL-backed path selection drives mobility, thematic similarity, and evidence views.
- A thesis-led Methodology dashboard that presents Aim & Scope, the exact four research questions, the structural/semantic/temporal workflow, current system architecture, Telegram/Twitter network architecture, Method → RQ traceability, and collapsed reproducibility/run provenance without rerunning analysis.
- A Thematic Analysis dashboard with a concise LDA-to-canonical-theme methodology overview, navigation-only section rail, sparse monthly rankings of up to five canonical themes, horizontally scrollable variable-length aggregate progression, and a canonical-theme → generated-label → LDA evidence drill-down.

## Non-Functional Requirements

The system should be:

- Locally runnable.
- Reproducible.
- Configurable without editing source code.
- Safe with credentials and API keys.
- Testable with small fixtures.
- Backward-compatible with existing CSV exports.
- Able to run offline for all non-GPT stages.

## Out Of Scope For First Production Version

- Real-time scraping.
- Hosted multi-user web application.
- Paid managed graph database.
- Changing thesis algorithms without an experiment label.
- Replacing LDA topics with only GPT summaries.
- Mandatory OpenAI calls in CI or unit tests.

## Acceptance Criteria

The project is acceptable when:

- Sample data can run through the social network pipeline.
- Sample data can run through LDA topic comparison.
- Theme analysis can run with a mocked or cached GPT provider.
- Existing output categories are preserved.
- Metrics and thresholds are covered by tests.
- Hard-coded local paths and credentials are removed.
- README explains setup, data preparation, and each pipeline command.
