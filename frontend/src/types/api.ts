export type MetricName = 'if' | 'wif';
export type NetworkView = 'users' | 'communities';
export type SamplingStrategy = 'community_balanced' | 'strongest_edges' | 'full_graph';
export type TopicType = 'matched' | 'partial';
export type RunStatus = 'pending' | 'running' | 'completed' | 'failed' | string;

export interface HealthResponse {
  status: string;
  read_only: boolean;
  schema_version: string;
}

export interface RunSummary {
  run_id: string;
  status: RunStatus;
  platform: string | null;
  content_type: string | null;
  date_start: string | null;
  date_end: string | null;
  year: number | null;
  month: number | null;
  started_at: string | null;
  completed_at: string | null;
  artifact_count: number;
}

export interface RunsResponse {
  runs: RunSummary[];
  total: number;
}

export interface RunDetail {
  run_id: string;
  status: RunStatus;
  dataset: Record<string, unknown>;
  code: Record<string, unknown>;
  pipeline: Record<string, unknown>;
  artifact_count: number;
  failure: Record<string, unknown> | null;
}

export interface ArtifactMetadata {
  key: string;
  path: string;
  category: string;
  media_type: string;
  schema_version: string;
  sha256: string;
  rows: number | null;
  byte_size: number | null;
  stage: string | null;
}

export interface ArtifactsResponse {
  run_id: string;
  artifacts: ArtifactMetadata[];
  total: number;
}

export interface VerificationResponse {
  run_id: string;
  ok: boolean;
  status: string;
  checked_artifacts: number;
  error_code: string | null;
  error: string | null;
}

export interface TopTheme {
  name: string;
  count: number;
}

export interface OverviewPeriod {
  period: string;
  if_users: number | null;
  wif_users: number | null;
  if_messages: number | null;
  wif_messages: number | null;
  interaction_records: number | null;
  if_community_count: number | null;
  wif_community_count: number | null;
  matched_community_count: number | null;
  matched_percentage: number | null;
}

export interface OverviewRunSummary {
  interaction_records: number | null;
  persistent_community_count: number | null;
  month_count: number;
}

export interface OverviewResponse {
  run_id: string;
  platform: string | null;
  content_type: string | null;
  date_start: string | null;
  date_end: string | null;
  total_users: number | null;
  total_messages: number | null;
  total_interactions: number | null;
  if_users: number | null;
  wif_users: number | null;
  if_messages: number | null;
  wif_messages: number | null;
  if_community_count: number | null;
  wif_community_count: number | null;
  matched_community_count: number | null;
  matched_percentage: number | null;
  persistent_community_count: number | null;
  available_periods: string[];
  periods: OverviewPeriod[];
  run_summary: OverviewRunSummary;
  top_themes: TopTheme[];
  model_metadata: Record<string, unknown>;
  config_metadata: Record<string, unknown>;
}

export interface NetworkNode {
  id: string;
  community_ids: string[];
  node_type?: 'user' | 'community';
  community_id?: string | null;
  member_count?: number | null;
  internal_edge_count?: number | null;
  internal_weight?: number | null;
  inbound_cross_community_weight?: number | null;
  outbound_cross_community_weight?: number | null;
  cross_community_neighbor_count?: number | null;
  x?: number | null;
  y?: number | null;
}

export interface NetworkEdge {
  source: string;
  target: string;
  community_id: string | null;
  direction: string | null;
  weight: number;
  edge_count?: number | null;
  user_pair_count?: number | null;
  interaction_count?: number | null;
  source_user_count?: number | null;
  target_user_count?: number | null;
}

export interface NetworkCoverage {
  is_complete: boolean;
  scope: string;
  completeness_reason: string | null;
  available_users: number;
  represented_users: number;
  available_edges: number;
  represented_edges: number;
  available_communities: number;
  represented_communities: number;
  available_weight: number;
  represented_weight: number;
  weight_coverage_ratio: number | null;
  cross_community_edges_available: boolean;
  cross_community_edges_reason?: string | null;
}

export interface NetworkSampling {
  strategy: SamplingStrategy;
  deterministic: boolean;
  max_nodes: number;
  max_edges: number;
}

export interface NetworkResponse {
  run_id: string;
  metric: MetricName;
  period: string | null;
  community_id: string | null;
  view?: NetworkView;
  sampling_strategy?: SamplingStrategy | null;
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  available_nodes: number;
  available_edges: number;
  returned_nodes: number;
  returned_edges: number;
  sampled: boolean;
  coverage?: NetworkCoverage | null;
  sampling?: NetworkSampling | null;
}

export interface CentralityActor {
  user_id: string;
  display_user_id: string;
  centrality: number;
  community_id: string | null;
  community_assignment_status: 'available' | 'unavailable';
}

export interface CentralityLeadersPeriod {
  period: string;
  spreader: CentralityActor | null;
  influencer: CentralityActor | null;
  average_in_degree_centrality: number | null;
  average_out_degree_centrality: number | null;
}

export interface CentralityLeadersResponse {
  run_id: string;
  metric: MetricName;
  periods: CentralityLeadersPeriod[];
  methodology_note: string;
}

export interface TablePage {
  run_id: string;
  artifact_key: string;
  records: Record<string, unknown>[];
  total: number;
  limit: number;
  offset: number;
}

export interface CommunitySummary {
  community_id: string;
  node_count: number;
  edge_count: number;
  total_weight: number;
  inbound_cross_community_weight?: number | null;
  outbound_cross_community_weight?: number | null;
  cross_community_neighbor_count?: number | null;
}

export interface CommunitiesResponse {
  run_id: string;
  metric: MetricName;
  period: string | null;
  communities: CommunitySummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface CommunityDetail {
  run_id: string;
  metric: MetricName;
  period: string | null;
  community: CommunitySummary;
  graph: NetworkResponse;
}

export interface TopicRecord {
  absolute_community: string | number | null;
  absolute_unigram_topic: unknown;
  absolute_unigram_keywords: unknown;
  weighted_community: string | number | null;
  weighted_unigram_topic: unknown;
  weighted_unigram_keywords: unknown;
  absolute_bigram_topic: unknown;
  absolute_bigram_keywords: unknown;
  weighted_bigram_topic: unknown;
  weighted_bigram_keywords: unknown;
  members: unknown;
  absolute_members: unknown;
  weighted_members: unknown;
  jaccard_score: number | null;
  common_members: unknown;
  uncommon_members: unknown;
}

export interface TopicsResponse {
  run_id: string;
  topic_type: TopicType;
  records: TopicRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface ThemeRecord {
  month: string | null;
  absolute_community: string | number | null;
  absolute_unigram_topic: unknown;
  absolute_unigram_keywords: unknown;
  weighted_community: string | number | null;
  weighted_unigram_topic: unknown;
  weighted_unigram_keywords: unknown;
  absolute_bigram_topic: unknown;
  absolute_bigram_keywords: unknown;
  weighted_bigram_topic: unknown;
  weighted_bigram_keywords: unknown;
  members: unknown;
  general_theme_gpt: unknown;
  general_theme_names: unknown;
  absolute_theme_gpt: unknown;
  absolute_theme_names: unknown;
  weighted_theme_gpt: unknown;
  weighted_theme_names: unknown;
  all_keywords: unknown;
  absolute_keywords: unknown;
  weighted_keywords: unknown;
}

export interface ThemesResponse {
  run_id: string;
  records: ThemeRecord[];
  total: number;
  limit: number;
  offset: number;
  provider_metadata: Record<string, unknown> | null;
}

export interface TransitionRecord {
  start_month: string;
  end_month: string;
  start_month_community: string | number;
  end_month_community: string | number;
  jaccard_score: number;
  common_members: unknown;
  uncommon_members: unknown;
  start_month_members: unknown;
  total_start_month_members: number | null;
  end_month_members: unknown;
  total_end_month_members: number | null;
  start_month_absolute_theme: unknown;
  end_month_absolute_theme: unknown;
  start_month_weighted_theme: unknown;
  end_month_weighted_theme: unknown;
  start_month_general_theme: unknown;
  end_month_general_theme: unknown;
}

export interface TransitionsResponse {
  run_id: string;
  records: TransitionRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface PersistentCommunity {
  persistent_id: string;
  communities: string[];
  months: string[];
  transition_count: number;
  average_jaccard: number;
}

export interface PersistentCommunitiesResponse {
  run_id: string;
  communities: PersistentCommunity[];
  total: number;
}

export interface MembershipChange {
  start_month: string;
  end_month: string;
  start_community: string;
  end_community: string;
  retained_count: number;
  joined_count: number;
  exited_count: number;
  start_count: number;
  end_count: number;
}

export interface MembershipChangesResponse {
  run_id: string;
  records: MembershipChange[];
  total: number;
}

export interface SimilarityArtifact {
  artifact_key: string;
  media_type: string;
  path: string;
}

export interface ThemeSimilarityResponse {
  run_id: string;
  matrix: number[][] | null;
  labels: string[];
  artifacts: SimilarityArtifact[];
}

export interface ApiErrorEnvelope {
  code: string;
  message: string;
  run_id?: string;
  artifact_key?: string;
  details?: Record<string, unknown>;
}
