import { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { getCommunities, getCommunity, getNetwork } from '../../api/networks';
import { getOverview } from '../../api/overview';
import { getCommunityThemes, getCommunityTopics } from '../../api/topics';
import {
  COMMUNITY_PARAM,
  PERIOD_PARAM,
  updateDashboardSearchParams,
} from '../../app/dashboardSearchParams';
import { useDashboardContext } from '../../hooks/useDashboardContext';
import { NETWORK_UI_LIMITS } from '../networks/networkModel';

const COMMUNITY_CONTEXT_NODES = 1000;
const COMMUNITY_CONTEXT_EDGES = 5000;

interface CommunitiesWorkspaceOptions {
  offset: number;
  limit: number;
  minWeight: number;
}

export function useCommunitiesWorkspaceData({
  offset,
  limit,
  minWeight,
}: CommunitiesWorkspaceOptions) {
  const dashboard = useDashboardContext();
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    selectedRunId,
    selectedRun,
    verification,
    metric,
  } = dashboard;
  const enabled = Boolean(
    selectedRunId && selectedRun?.status === 'completed' && verification?.ok,
  );

  const overviewQuery = useQuery({
    queryKey: ['communities-workspace-overview', selectedRunId],
    queryFn: ({ signal }) => getOverview(selectedRunId, signal),
    enabled,
  });

  const requestedPeriod = searchParams.get(PERIOD_PARAM);
  const periods = overviewQuery.data?.available_periods ?? [];
  const selectedPeriod = requestedPeriod && periods.includes(requestedPeriod)
    ? requestedPeriod
    : periods.at(-1) ?? '';
  const requestedCommunityId = searchParams.get(COMMUNITY_PARAM);
  const periodEnabled = enabled && Boolean(selectedPeriod);
  const partitionRef = useRef<string | null>(null);
  const partition = selectedPeriod ? `${selectedRunId}:${selectedPeriod}:${metric}` : '';
  const partitionChanged = Boolean(
    partition && partitionRef.current && partitionRef.current !== partition,
  );
  const selectedCommunityId = partitionChanged ? null : requestedCommunityId;

  useEffect(() => {
    if (!overviewQuery.data || !selectedPeriod || requestedPeriod === selectedPeriod) return;
    setSearchParams(
      updateDashboardSearchParams(searchParams, { period: selectedPeriod }),
      { replace: true },
    );
  }, [overviewQuery.data, requestedPeriod, searchParams, selectedPeriod, setSearchParams]);

  useEffect(() => {
    if (!partition) return;
    const previous = partitionRef.current;
    partitionRef.current = partition;
    if (requestedCommunityId && previous && previous !== partition) {
      setSearchParams(
        updateDashboardSearchParams(searchParams, { communityId: null }),
        { replace: true },
      );
    }
  }, [partition, requestedCommunityId, searchParams, setSearchParams]);

  const communitiesQuery = useQuery({
    queryKey: ['communities-workspace-directory', selectedRunId, selectedPeriod, metric, limit, offset],
    queryFn: ({ signal }) => getCommunities(
      selectedRunId,
      { metric, period: selectedPeriod, limit, offset },
      signal,
    ),
    enabled: periodEnabled,
  });

  const detailQuery = useQuery({
    queryKey: [
      'communities-workspace-detail',
      selectedRunId,
      selectedPeriod,
      metric,
      selectedCommunityId,
      minWeight,
      NETWORK_UI_LIMITS.maxNodes,
      NETWORK_UI_LIMITS.maxEdges,
    ],
    queryFn: ({ signal }) => getCommunity(
      selectedRunId,
      selectedCommunityId as string,
      {
        metric,
        period: selectedPeriod,
        min_weight: minWeight,
        max_nodes: NETWORK_UI_LIMITS.maxNodes,
        max_edges: NETWORK_UI_LIMITS.maxEdges,
      },
      signal,
    ),
    enabled: periodEnabled && Boolean(selectedCommunityId),
  });

  const communityContextQuery = useQuery({
    queryKey: [
      'communities-workspace-community-context',
      selectedRunId,
      selectedPeriod,
      metric,
      COMMUNITY_CONTEXT_NODES,
      COMMUNITY_CONTEXT_EDGES,
    ],
    queryFn: ({ signal }) => getNetwork(
      selectedRunId,
      {
        metric,
        period: selectedPeriod,
        view: 'communities',
        max_nodes: COMMUNITY_CONTEXT_NODES,
        max_edges: COMMUNITY_CONTEXT_EDGES,
      },
      signal,
    ),
    enabled: periodEnabled && Boolean(selectedCommunityId),
  });

  const topicsQuery = useQuery({
    queryKey: ['communities-workspace-topics', selectedRunId, selectedPeriod, selectedCommunityId, 100],
    queryFn: ({ signal }) => getCommunityTopics(
      selectedRunId,
      selectedCommunityId as string,
      { type: 'matched', period: selectedPeriod, limit: 100, offset: 0 },
      signal,
    ),
    enabled: periodEnabled && Boolean(selectedCommunityId),
    retry: false,
  });

  const themesQuery = useQuery({
    queryKey: ['communities-workspace-themes', selectedRunId, selectedPeriod, selectedCommunityId, 100],
    queryFn: ({ signal }) => getCommunityThemes(
      selectedRunId,
      selectedCommunityId as string,
      { period: selectedPeriod, limit: 100, offset: 0 },
      signal,
    ),
    enabled: periodEnabled && Boolean(selectedCommunityId),
    retry: false,
  });

  const selectedPeriodSummary = overviewQuery.data?.periods.find(
    (period) => period.period === selectedPeriod,
  ) ?? null;

  const updateSelection = (communityId: string | null) => {
    setSearchParams(updateDashboardSearchParams(searchParams, { communityId }));
  };

  return {
    ...dashboard,
    enabled,
    overviewQuery,
    periods,
    selectedPeriod,
    selectedPeriodSummary,
    selectedCommunityId,
    setSelectedPeriod: (period: string) => setSearchParams(
      updateDashboardSearchParams(searchParams, { period, communityId: null }),
    ),
    selectCommunity: (communityId: string) => updateSelection(communityId),
    clearCommunity: () => updateSelection(null),
    communitiesQuery,
    detailQuery,
    communityContextQuery,
    topicsQuery,
    themesQuery,
  };
}
