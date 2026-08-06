import { useEffect, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { getTransitions } from '../../api/evolution';
import {
  getCentralityLeaders,
  getCommunities,
  getCommunity,
  getNetwork,
} from '../../api/networks';
import { getOverview } from '../../api/overview';
import { getArtifacts } from '../../api/runs';
import { getThemes, getTopics } from '../../api/topics';
import {
  COMMUNITY_PARAM,
  NETWORK_VIEW_PARAM,
  PERIOD_PARAM,
  SAMPLING_PARAM,
  resolveSamplingStrategy,
  updateDashboardSearchParams,
} from '../../app/dashboardSearchParams';
import { useDashboardContext } from '../../hooks/useDashboardContext';
import type { NetworkView, SamplingStrategy } from '../../types/api';

const OVERVIEW_USER_GRAPH_NODES = 180;
const OVERVIEW_USER_GRAPH_EDGES = 350;
const OVERVIEW_COMMUNITY_GRAPH_NODES = 1000;
const OVERVIEW_COMMUNITY_GRAPH_EDGES = 5000;
const OVERVIEW_COMMUNITY_DETAIL_NODES = 240;
const OVERVIEW_COMMUNITY_DETAIL_EDGES = 500;

export function useOverviewData(communityOffset: number, communityLimit = 5) {
  const dashboard = useDashboardContext();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    selectedRunId,
    selectedRun,
    selectedRunDetail,
    verification,
    metric,
  } = dashboard;
  const enabled = Boolean(
    selectedRunId && selectedRun?.status === 'completed' && verification?.ok,
  );

  const overviewQuery = useQuery({
    queryKey: ['overview', selectedRunId],
    queryFn: ({ signal }) => getOverview(selectedRunId, signal),
    enabled,
  });

  const requestedPeriod = searchParams.get(PERIOD_PARAM);
  const periods = overviewQuery.data?.available_periods ?? [];
  const selectedPeriod = requestedPeriod && periods.includes(requestedPeriod)
    ? requestedPeriod
    : periods.at(-1) ?? '';
  const networkView: NetworkView = 'communities';
  const samplingStrategy = resolveSamplingStrategy(searchParams.get(SAMPLING_PARAM));
  const selectedCommunityId = searchParams.get(COMMUNITY_PARAM);
  const partitionRef = useRef<string | null>(null);
  const periodEnabled = enabled && Boolean(selectedPeriod);
  const graphNodeLimit = networkView === 'communities'
    ? OVERVIEW_COMMUNITY_GRAPH_NODES
    : OVERVIEW_USER_GRAPH_NODES;
  const graphEdgeLimit = networkView === 'communities'
    ? OVERVIEW_COMMUNITY_GRAPH_EDGES
    : OVERVIEW_USER_GRAPH_EDGES;

  useEffect(() => {
    if (!overviewQuery.data || !selectedPeriod || requestedPeriod === selectedPeriod) return;
    setSearchParams(
      updateDashboardSearchParams(searchParams, { period: selectedPeriod }),
      { replace: true },
    );
  }, [
    overviewQuery.data,
    requestedPeriod,
    searchParams,
    selectedPeriod,
    setSearchParams,
  ]);

  useEffect(() => {
    if (!selectedPeriod) return;
    const partition = `${metric}:${selectedPeriod}`;
    const previousPartition = partitionRef.current;
    partitionRef.current = partition;
    if (
      selectedCommunityId
      && previousPartition
      && previousPartition !== partition
    ) {
      setSearchParams(
        updateDashboardSearchParams(searchParams, { communityId: null }),
        { replace: true },
      );
    }
  }, [
    metric,
    searchParams,
    selectedCommunityId,
    selectedPeriod,
    setSearchParams,
  ]);

  useEffect(() => {
    const requestedView = searchParams.get(NETWORK_VIEW_PARAM);
    const requestedSampling = searchParams.get(SAMPLING_PARAM);
    if (requestedView === networkView && requestedSampling === samplingStrategy) return;
    setSearchParams(
      updateDashboardSearchParams(searchParams, {
        networkView,
        sampling: samplingStrategy,
      }),
      { replace: true },
    );
  }, [
    networkView,
    samplingStrategy,
    searchParams,
    setSearchParams,
  ]);

  const networkQuery = useQuery({
    queryKey: [
      'overview-network',
      selectedRunId,
      metric,
      selectedPeriod,
      networkView,
      samplingStrategy,
      graphNodeLimit,
      graphEdgeLimit,
    ],
    queryFn: ({ signal }) =>
      getNetwork(
        selectedRunId,
        {
          metric,
          period: selectedPeriod,
          view: networkView,
          sampling: undefined,
          max_nodes: graphNodeLimit,
          max_edges: graphEdgeLimit,
        },
        signal,
      ),
    enabled: periodEnabled,
  });
  const communityDetailQuery = useQuery({
    queryKey: [
      'overview-community-detail',
      selectedRunId,
      metric,
      selectedPeriod,
      selectedCommunityId,
      OVERVIEW_COMMUNITY_DETAIL_NODES,
      OVERVIEW_COMMUNITY_DETAIL_EDGES,
    ],
    queryFn: ({ signal }) =>
      getCommunity(
        selectedRunId,
        selectedCommunityId ?? '',
        {
          metric,
          period: selectedPeriod,
          max_nodes: OVERVIEW_COMMUNITY_DETAIL_NODES,
          max_edges: OVERVIEW_COMMUNITY_DETAIL_EDGES,
        },
        signal,
      ),
    enabled: periodEnabled && Boolean(selectedCommunityId),
  });

  const communitiesQuery = useQuery({
    queryKey: [
      'overview-communities',
      selectedRunId,
      metric,
      selectedPeriod,
      communityLimit,
      communityOffset,
    ],
    queryFn: ({ signal }) =>
      getCommunities(
        selectedRunId,
        {
          metric,
          period: selectedPeriod,
          limit: communityLimit,
          offset: communityOffset,
        },
        signal,
      ),
    enabled: periodEnabled,
  });
  const centralityLeadersQuery = useQuery({
    queryKey: ['overview-centrality-leaders', selectedRunId, metric],
    queryFn: ({ signal }) => getCentralityLeaders(selectedRunId, { metric }, signal),
    enabled,
  });
  const artifactsQuery = useQuery({
    queryKey: ['artifacts', selectedRunId],
    queryFn: ({ signal }) => getArtifacts(selectedRunId, signal),
    enabled,
  });

  const artifacts = artifactsQuery.data?.artifacts ?? [];
  const hasThemes = artifacts.some((artifact) => artifact.key.startsWith('themes_'));
  const hasMatchedTopics = artifacts.some((artifact) => artifact.key.startsWith('matched_communities_topics'));
  const hasTransitions = artifacts.some((artifact) => artifact.key === 'community_transitions');
  const selectedMonth = selectedPeriod ? selectedPeriod.slice(5, 7) : undefined;

  const themesQuery = useQuery({
    queryKey: ['overview-themes', selectedRunId, selectedMonth, 500],
    queryFn: ({ signal }) =>
      getThemes(
        selectedRunId,
        { month: selectedMonth, limit: 500, offset: 0 },
        signal,
      ),
    enabled: periodEnabled && artifactsQuery.isSuccess && hasThemes,
  });
  const communityTopicsQuery = useQuery({
    queryKey: [
      'overview-community-topics',
      selectedRunId,
      selectedPeriod,
      selectedCommunityId,
      100,
    ],
    queryFn: ({ signal }) =>
      getTopics(
        selectedRunId,
        {
          type: 'matched',
          community_id: selectedCommunityId ?? undefined,
          period: selectedPeriod,
          limit: 100,
          offset: 0,
        },
        signal,
      ),
    enabled: periodEnabled
      && artifactsQuery.isSuccess
      && hasMatchedTopics
      && Boolean(selectedCommunityId),
    retry: false,
  });
  const transitionsQuery = useQuery({
    queryKey: ['overview-transitions', selectedRunId, 1000],
    queryFn: ({ signal }) => getTransitions(selectedRunId, { limit: 1000 }, signal),
    enabled: enabled && artifactsQuery.isSuccess && hasTransitions,
  });

  useEffect(() => {
    if (!periodEnabled) return;
    const currentIndex = periods.indexOf(selectedPeriod);
    for (const adjacentPeriod of [periods[currentIndex - 1], periods[currentIndex + 1]]) {
      if (!adjacentPeriod) continue;
      void queryClient.prefetchQuery({
        queryKey: [
          'overview-network',
          selectedRunId,
          metric,
          adjacentPeriod,
          networkView,
          samplingStrategy,
          graphNodeLimit,
          graphEdgeLimit,
        ],
        queryFn: ({ signal }) =>
          getNetwork(
            selectedRunId,
            {
              metric,
              period: adjacentPeriod,
              view: networkView,
              sampling: undefined,
              max_nodes: graphNodeLimit,
              max_edges: graphEdgeLimit,
            },
            signal,
          ),
        staleTime: 60_000,
      });
    }
  }, [
    graphEdgeLimit,
    graphNodeLimit,
    metric,
    networkView,
    periodEnabled,
    periods,
    queryClient,
    samplingStrategy,
    selectedPeriod,
    selectedRunId,
  ]);

  const setNetworkView = (_view: NetworkView) =>
    setSearchParams(updateDashboardSearchParams(searchParams, { networkView: 'communities' }));
  const setSamplingStrategy = (sampling: SamplingStrategy) =>
    setSearchParams(updateDashboardSearchParams(searchParams, { sampling }));
  const inspectCommunity = (communityId: string) =>
    setSearchParams(
      updateDashboardSearchParams(searchParams, {
        networkView: 'communities',
        communityId,
      }),
    );

  return {
    ...dashboard,
    selectedRunDetail,
    enabled,
    selectedPeriod,
    periods,
    networkView,
    samplingStrategy,
    selectedCommunityId,
    setSelectedPeriod: (period: string) =>
      setSearchParams(
        updateDashboardSearchParams(searchParams, {
          period,
          communityId: null,
        }),
      ),
    setNetworkView,
    setSamplingStrategy,
    inspectCommunity,
    clearCommunity: () =>
      setSearchParams(updateDashboardSearchParams(searchParams, { communityId: null })),
    overviewQuery,
    networkQuery,
    communityDetailQuery,
    communityTopicsQuery,
    communitiesQuery,
    centralityLeadersQuery,
    artifactsQuery,
    themesQuery,
    transitionsQuery,
    hasThemes,
    hasMatchedTopics,
    hasTransitions,
    retryOverview: () => {
      void overviewQuery.refetch();
      void artifactsQuery.refetch();
      void centralityLeadersQuery.refetch();
      if (periodEnabled) {
        void networkQuery.refetch();
        if (selectedCommunityId) {
          void communityDetailQuery.refetch();
          if (hasMatchedTopics) void communityTopicsQuery.refetch();
        }
        void communitiesQuery.refetch();
        if (hasThemes) void themesQuery.refetch();
      }
      if (hasTransitions) void transitionsQuery.refetch();
    },
  };
}
