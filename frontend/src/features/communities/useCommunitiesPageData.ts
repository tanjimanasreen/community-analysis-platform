import { useQuery } from '@tanstack/react-query';
import { getCommunities, getCommunity } from '../../api/networks';
import { getCommunityThemes, getCommunityTopics } from '../../api/topics';
import { useDashboardContext } from '../../hooks/useDashboardContext';
import { NETWORK_UI_LIMITS } from '../networks/networkModel';

interface CommunitiesPageOptions {
  offset: number;
  limit: number;
  selectedCommunityId: string | null;
}

export function useCommunitiesPageData({
  offset,
  limit,
  selectedCommunityId,
}: CommunitiesPageOptions) {
  const dashboard = useDashboardContext();
  const { selectedRunId, selectedRun, verification, metric } = dashboard;
  const enabled = Boolean(
    selectedRunId && selectedRun?.status === 'completed' && verification?.ok,
  );

  const communitiesQuery = useQuery({
    queryKey: ['top-communities', selectedRunId, metric, limit, offset],
    queryFn: ({ signal }) => getCommunities(selectedRunId, { metric, limit, offset }, signal),
    enabled,
  });
  const detailQuery = useQuery({
    queryKey: ['top-community-detail', selectedRunId, metric, selectedCommunityId],
    queryFn: ({ signal }) => getCommunity(
      selectedRunId,
      selectedCommunityId as string,
      { metric, max_nodes: NETWORK_UI_LIMITS.maxNodes, max_edges: NETWORK_UI_LIMITS.maxEdges },
      signal,
    ),
    enabled: enabled && Boolean(selectedCommunityId),
  });
  const topicsQuery = useQuery({
    queryKey: ['top-community-topics', selectedRunId, selectedCommunityId],
    queryFn: ({ signal }) => getCommunityTopics(
      selectedRunId,
      selectedCommunityId as string,
      { type: 'matched', limit: 20, offset: 0 },
      signal,
    ),
    enabled: enabled && Boolean(selectedCommunityId),
    retry: false,
  });
  const themesQuery = useQuery({
    queryKey: ['top-community-themes', selectedRunId, selectedCommunityId],
    queryFn: ({ signal }) => getCommunityThemes(
      selectedRunId,
      selectedCommunityId as string,
      { limit: 20, offset: 0 },
      signal,
    ),
    enabled: enabled && Boolean(selectedCommunityId),
    retry: false,
  });

  return {
    ...dashboard,
    communitiesQuery,
    detailQuery,
    topicsQuery,
    themesQuery,
  };
}
