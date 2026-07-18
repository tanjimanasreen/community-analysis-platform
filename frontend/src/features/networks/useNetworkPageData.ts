import { useQuery } from '@tanstack/react-query';
import { getCentrality, getCommunities, getCommunity, getNetwork } from '../../api/networks';
import { getCommunityThemes, getCommunityTopics } from '../../api/topics';
import { useDashboardContext } from '../../hooks/useDashboardContext';
import { NETWORK_UI_LIMITS } from './networkModel';

interface NetworkPageOptions {
  communityId: string | null;
  minWeight: number;
  communityOffset: number;
  communityLimit?: number;
  centralityOffset: number;
  centralityLimit?: number;
}

export function useNetworkPageData({
  communityId,
  minWeight,
  communityOffset,
  communityLimit = 10,
  centralityOffset,
  centralityLimit = 10,
}: NetworkPageOptions) {
  const dashboard = useDashboardContext();
  const { selectedRunId, selectedRun, verification, metric } = dashboard;
  const enabled = Boolean(
    selectedRunId && selectedRun?.status === 'completed' && verification?.ok,
  );
  const graphParams = {
    metric,
    min_weight: minWeight,
    max_nodes: NETWORK_UI_LIMITS.maxNodes,
    max_edges: NETWORK_UI_LIMITS.maxEdges,
  } as const;

  const networkQuery = useQuery({
    queryKey: ['network-page', selectedRunId, metric, minWeight, graphParams.max_nodes, graphParams.max_edges],
    queryFn: ({ signal }) => getNetwork(selectedRunId, graphParams, signal),
    enabled,
  });
  const communitiesQuery = useQuery({
    queryKey: ['network-communities', selectedRunId, metric, communityLimit, communityOffset],
    queryFn: ({ signal }) => getCommunities(
      selectedRunId,
      { metric, limit: communityLimit, offset: communityOffset },
      signal,
    ),
    enabled,
  });
  const centralityQuery = useQuery({
    queryKey: ['centrality', selectedRunId, centralityLimit, centralityOffset],
    queryFn: ({ signal }) => getCentrality(
      selectedRunId,
      { limit: centralityLimit, offset: centralityOffset },
      signal,
    ),
    enabled,
  });
  const detailQuery = useQuery({
    queryKey: ['community-detail', selectedRunId, metric, communityId, minWeight, graphParams.max_nodes, graphParams.max_edges],
    queryFn: ({ signal }) => getCommunity(
      selectedRunId,
      communityId as string,
      graphParams,
      signal,
    ),
    enabled: enabled && Boolean(communityId),
  });
  const topicsQuery = useQuery({
    queryKey: ['community-topics', selectedRunId, communityId, 'matched', 20],
    queryFn: ({ signal }) => getCommunityTopics(
      selectedRunId,
      communityId as string,
      { type: 'matched', limit: 20, offset: 0 },
      signal,
    ),
    enabled: enabled && Boolean(communityId),
    retry: false,
  });
  const themesQuery = useQuery({
    queryKey: ['community-themes', selectedRunId, communityId, 20],
    queryFn: ({ signal }) => getCommunityThemes(
      selectedRunId,
      communityId as string,
      { limit: 20, offset: 0 },
      signal,
    ),
    enabled: enabled && Boolean(communityId),
    retry: false,
  });

  return {
    ...dashboard,
    enabled,
    networkQuery,
    communitiesQuery,
    centralityQuery,
    detailQuery,
    topicsQuery,
    themesQuery,
  };
}
