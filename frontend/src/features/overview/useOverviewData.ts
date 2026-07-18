import { useQueries, useQuery } from '@tanstack/react-query';
import { getTransitions } from '../../api/evolution';
import { getCommunities, getNetwork } from '../../api/networks';
import { getOverview } from '../../api/overview';
import { getArtifacts } from '../../api/runs';
import { getThemes } from '../../api/topics';
import { useDashboardContext } from '../../hooks/useDashboardContext';
import { compatibleRuns } from './overviewUtils';

export function useOverviewData(communityOffset: number, communityLimit = 5) {
  const dashboard = useDashboardContext();
  const {
    selectedRunId,
    selectedRun,
    selectedRunDetail,
    verification,
    metric,
    runs,
  } = dashboard;
  const enabled = Boolean(
    selectedRunId && selectedRun?.status === 'completed' && verification?.ok,
  );

  const overviewQuery = useQuery({
    queryKey: ['overview', selectedRunId],
    queryFn: ({ signal }) => getOverview(selectedRunId, signal),
    enabled,
  });
  const networkQuery = useQuery({
    queryKey: ['overview-network', selectedRunId, metric, 180, 350],
    queryFn: ({ signal }) =>
      getNetwork(selectedRunId, { metric, max_nodes: 180, max_edges: 350 }, signal),
    enabled,
  });
  const communitiesQuery = useQuery({
    queryKey: ['overview-communities', selectedRunId, metric, communityLimit, communityOffset],
    queryFn: ({ signal }) =>
      getCommunities(
        selectedRunId,
        { metric, limit: communityLimit, offset: communityOffset },
        signal,
      ),
    enabled,
  });
  const artifactsQuery = useQuery({
    queryKey: ['artifacts', selectedRunId],
    queryFn: ({ signal }) => getArtifacts(selectedRunId, signal),
    enabled,
  });

  const artifacts = artifactsQuery.data?.artifacts ?? [];
  const hasThemes = artifacts.some(
    (artifact) => artifact.key.startsWith('themes_'),
  );
  const hasTransitions = artifacts.some((artifact) => artifact.key === 'community_transitions');

  const themesQuery = useQuery({
    queryKey: ['overview-themes', selectedRunId, 500],
    queryFn: ({ signal }) => getThemes(selectedRunId, { limit: 500, offset: 0 }, signal),
    enabled: enabled && artifactsQuery.isSuccess && hasThemes,
  });
  const transitionsQuery = useQuery({
    queryKey: ['overview-transitions', selectedRunId, 100],
    queryFn: ({ signal }) => getTransitions(selectedRunId, { limit: 100 }, signal),
    enabled: enabled && artifactsQuery.isSuccess && hasTransitions,
  });

  const historyRuns = compatibleRuns(runs, selectedRun);
  const historyQueries = useQueries({
    queries: historyRuns.map((run) => ({
      queryKey: ['overview', run.run_id],
      queryFn: ({ signal }: { signal: AbortSignal }) => getOverview(run.run_id, signal),
      enabled,
      staleTime: 60_000,
    })),
  });
  const history = historyRuns.flatMap((run, index) => {
    const data = historyQueries[index]?.data;
    return data ? [{ run, overview: data }] : [];
  });

  return {
    ...dashboard,
    selectedRunDetail,
    enabled,
    overviewQuery,
    networkQuery,
    communitiesQuery,
    artifactsQuery,
    themesQuery,
    transitionsQuery,
    history,
    hasThemes,
    hasTransitions,
    retryOverview: () => {
      void overviewQuery.refetch();
      void networkQuery.refetch();
      void communitiesQuery.refetch();
      void artifactsQuery.refetch();
      if (hasThemes) void themesQuery.refetch();
      if (hasTransitions) void transitionsQuery.refetch();
    },
  };
}
