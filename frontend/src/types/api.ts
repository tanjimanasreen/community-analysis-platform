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


export interface ThemeCommunityPairEvidence {
  absolute_community: string | null;
  weighted_community: string | null;
  keywords: string[];
}

export interface ThemeTrendItem {
  name: string;
  community_count: number;
  percentage: number;
  keywords: string[];
  community_pairs: ThemeCommunityPairEvidence[];
}

export interface MonthlyThemeTrendSummary {
  period: string;
  source_record_count: number;
  excluded_records_without_pair: number;
  total_themed_community_pairs: number;
  distinct_exact_theme_count: number;
  themes: ThemeTrendItem[];
}

export interface MonthlyThemeTrendResponse extends MonthlyThemeTrendSummary {
  run_id: string;
  scope: string;
  complete: boolean;
}

export interface ThemeTrendSeriesPoint {
  period: string;
  community_count: number;
  total_themed_community_pairs: number;
  percentage: number;
}

export interface DominantThemeTrend {
  name: string;
  total_community_month_count: number;
  months_present: number;
  peak_period: string;
  peak_month_count: number;
  series: ThemeTrendSeriesPoint[];
  keywords: string[];
}

export interface ThemeTimelineResponse {
  run_id: string;
  scope: string;
  available_periods: string[];
  periods: string[];
  complete: boolean;
  source_record_count: number;
  excluded_records_without_pair: number;
  monthly_summaries: MonthlyThemeTrendSummary[];
  most_discussed_theme: DominantThemeTrend | null;
}

export interface ClusteredThemeCommunityPairEvidence {
  absolute_community: string | null;
  weighted_community: string | null;
  source_labels: string[];
  keywords: string[];
}

export interface ClusteredThemeItem {
  theme_id: string;
  name: string;
  community_count: number;
  percentage: number;
  keywords: string[];
  monthly_cluster_ids: string[];
  monthly_representative_themes: string[];
  source_theme_labels: string[];
  community_pairs: ClusteredThemeCommunityPairEvidence[];
  mean_membership_probability: number | null;
}

export interface MonthlyClusteredThemeSummary {
  period: string;
  source_observation_count: number;
  excluded_records_missing_general_theme: number;
  excluded_records_ambiguous_general_theme_serialization: number;
  monthly_noise_observation_count: number;
  total_themed_community_pairs: number;
  distinct_clustered_theme_count: number;
  themes: ClusteredThemeItem[];
  embedding_provider: string | null;
  embedding_model: string | null;
  monthly_cluster_contract_version: string | null;
  canonicalization_contract_version: string | null;
}

export interface MonthlyClusteredThemeResponse extends MonthlyClusteredThemeSummary {
  run_id: string;
  scope: string;
  complete: boolean;
}

export interface ClusteredThemeSeriesPoint {
  period: string;
  community_count: number;
  total_themed_community_pairs: number;
  percentage: number;
}

export interface DominantClusteredTheme {
  theme_id: string;
  name: string;
  total_community_month_count: number;
  months_present: number;
  peak_period: string;
  peak_month_count: number;
  series: ClusteredThemeSeriesPoint[];
  keywords: string[];
}

export interface ClusteredThemeTimelineResponse {
  run_id: string;
  scope: string;
  available_periods: string[];
  periods: string[];
  complete: boolean;
  source_observation_count: number;
  excluded_records_missing_general_theme: number;
  excluded_records_ambiguous_general_theme_serialization: number;
  monthly_noise_observation_count: number;
  distinct_canonical_theme_count: number;
  monthly_summaries: MonthlyClusteredThemeSummary[];
  most_discussed_theme: DominantClusteredTheme | null;
}

export interface ClusteredThemeEvidenceRecord {
  period: string;
  canonical_theme_id: string | null;
  canonical_theme_label: string | null;
  monthly_cluster_id: string | null;
  monthly_representative_theme: string | null;
  source_general_theme_label: string;
  absolute_community: string | null;
  weighted_community: string | null;
  keywords: string[];
  membership_probability: number | null;
}

export interface ClusteredThemeEvidenceResponse {
  run_id: string;
  period: string;
  canonical_theme_id: string;
  records: ClusteredThemeEvidenceRecord[];
  total: number;
  limit: number;
  offset: number;
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


export interface EvolutionMethodology {
  content_type: string;
  transition_threshold: number | null;
  similarity_provider: string | null;
  similarity_model: string | null;
  similarity_model_revision: string | null;
}

export interface EvolutionPathStep {
  step_index: number;
  month: string;
  community_key: string;
  community_id: string;
  member_count: number;
  members: string[];
  previous_month: string | null;
  previous_community_key: string | null;
  previous_community_id: string | null;
  jaccard_from_previous: number | null;
  retained_count: number | null;
  absolute_theme: string;
  weighted_theme: string;
  general_theme: string;
}

export interface EvolutionPath {
  path_id: string;
  display_order: number;
  duration: number;
  transition_count: number;
  average_jaccard: number;
  total_retained_members: number;
  months: string[];
  steps: EvolutionPathStep[];
}

export interface EvolutionPathsResponse {
  run_id: string;
  paths: EvolutionPath[];
  total: number;
  methodology: EvolutionMethodology;
}

export interface PathMembershipRecord {
  path_id: string;
  display_order: number;
  step_index: number;
  month: string;
  community_key: string;
  community_id: string;
  member_count: number;
  size_delta: number | null;
  existing_count: number;
  new_count: number;
  lost_count: number;
  reappearing_count: number;
  members: string[];
  existing_members: string[];
  new_members: string[];
  lost_members: string[];
  reappearing_members: string[];
}

export interface PathMembershipResponse {
  run_id: string;
  path_id: string;
  records: PathMembershipRecord[];
}

export type EvolutionThemeType = 'general' | 'absolute' | 'weighted';

export interface PathThemeSimilarityResponse {
  run_id: string;
  path_id: string;
  theme_type: EvolutionThemeType;
  months: string[];
  communities: string[];
  themes: string[];
  matrix: number[][];
  embedding_provider: string | null;
  embedding_model: string | null;
  embedding_model_revision: string | null;
}
