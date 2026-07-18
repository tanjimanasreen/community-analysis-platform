export const API_ROUTES = {
  health: '/health',
  runs: '/runs',
  runDetail: '/runs/{run_id}',
  artifacts: '/runs/{run_id}/artifacts',
  verification: '/runs/{run_id}/verification',
  overview: '/runs/{run_id}/overview',
  network: '/runs/{run_id}/network',
  centrality: '/runs/{run_id}/centrality',
  communities: '/runs/{run_id}/communities',
  communityDetail: '/runs/{run_id}/communities/{community_id}',
  topics: '/runs/{run_id}/topics',
  communityTopics: '/runs/{run_id}/topics/{community_id}',
  themes: '/runs/{run_id}/themes',
  communityThemes: '/runs/{run_id}/themes/{community_id}',
  transitions: '/runs/{run_id}/transitions',
  persistentCommunities: '/runs/{run_id}/persistent-communities',
  membershipChanges: '/runs/{run_id}/membership-changes',
  themeSimilarity: '/runs/{run_id}/theme-similarity',
  report: '/runs/{run_id}/report',
  download: '/runs/{run_id}/downloads/{artifact_key}',
} as const;

export const API_QUERY_KEYS = {
  runs: ['platform', 'content_type', 'year', 'month', 'status'],
  network: ['metric', 'community_id', 'max_nodes', 'max_edges', 'min_weight'],
  centrality: ['limit', 'offset'],
  communities: ['metric', 'limit', 'offset'],
  communityDetail: ['metric', 'max_nodes', 'max_edges', 'min_weight'],
  topics: ['type', 'community_id', 'limit', 'offset'],
  communityTopics: ['type', 'limit', 'offset'],
  themes: ['month', 'community_id', 'limit', 'offset'],
  communityThemes: ['month', 'limit', 'offset'],
  transitions: ['limit', 'offset'],
} as const;

export function fillRoute(
  template: string,
  values: Record<string, string>,
): string {
  return Object.entries(values).reduce(
    (path, [key, value]) => path.replace(`{${key}}`, encodeURIComponent(value)),
    template,
  );
}
