# Future Backend Integration TODOs

This dashboard uses mock data for some of the advanced visualizations to match the premium mockup. A backend agent should implement the following endpoints or extend existing ones to provide this data dynamically:

## 1. Evolution Chart Data
- **Component**: `EvolutionChart.jsx` (Used in Overview, EvolutionOverTime, ComparativeAnalysis)
- **Data Needed**: Time-series data of total communities, Twitter/X communities, and Telegram communities over the past N months.
- **Action**: Create an API endpoint `/api/community-evolution` that returns an array of objects: `{ name: 'Month \'YY', total: number, twitter: number, telegram: number }`.

## 2. Platform Comparison Data
- **Component**: `PlatformComparison.jsx` (Used in Overview, EvolutionOverTime)
- **Data Needed**: Aggregated metrics split by platform (Message Volume, Persistence Score, Thematic Diversity).
- **Action**: Create an API endpoint `/api/platform-comparison` that calculates these specific averages across platforms for the selected month/run.

## 3. Network Graph Details
- **Component**: `NetworkGraph.jsx` (Used in Overview, CommunityNetwork)
- **Data Needed**: Detailed node-link data representing the "Community Network (WIF)".
- **Action**: Ensure the existing backend graph endpoints return a structured `{ nodes: [], links: [] }` format compatible with `react-force-graph-2d`. Nodes should have `id`, `group`, and `val` (size). Links should have `source`, `target`, and `value` (weight).

## 4. Transitions Sankey Data
- **Component**: `TransitionsSankey.jsx` (Used in Overview)
- **Data Needed**: Month-to-month member overlap percentages aggregated by Dominant Theme.
- **Action**: Extend the `/api/transitions` endpoint or create a new one that computes the Sankey flows (source node, target node, flow value) to represent percentage of members retained across themes month-over-month.

## 5. Right Sidebar & Trend Notes Insights
- **Component**: `RightSidebar.jsx`, `EvolutionOverTime.jsx`, `ComparativeAnalysis.jsx`
- **Data Needed**: Dynamic text generation for "Key Insights", "Trend Notes", and "Key Findings" based on current data anomalies or trends.
- **Action**: Integrate an LLM call or statistical thresholding on the backend to dynamically generate these text bullets instead of hardcoding them.

## 6. Comparative Analysis - Theme Overlap
- **Component**: `ComparativeAnalysis.jsx` (Venn Diagram)
- **Data Needed**: Percentage of message volume that is exclusive to Twitter/X, exclusive to Telegram, and shared between both for a specific theme.
- **Action**: Create `/api/theme-overlap` returning `{ twitterExclusive: 32, telegramExclusive: 22, shared: 46 }`.

## 7. Reports Library
- **Component**: `Reports.jsx`
- **Data Needed**: A list of generated or scheduled reports.
- **Action**: Create a CRUD backend for managing reports, returning `{ name, desc, type, status, date }`.
