import { useQuery } from '@tanstack/react-query';
import { getOverview } from '../../api/overview';
import { getArtifacts, getRun } from '../../api/runs';
import { useDashboardContext } from '../../hooks/useDashboardContext';

export function useComparisonData(twitterRunId: string, telegramRunId: string) {
  const dashboard = useDashboardContext();
  const twitterEnabled = Boolean(twitterRunId);
  const telegramEnabled = Boolean(telegramRunId);

  const twitterOverview = useQuery({
    queryKey: ['comparison-overview', twitterRunId],
    queryFn: ({ signal }) => getOverview(twitterRunId, signal),
    enabled: twitterEnabled,
    retry: false,
  });
  const telegramOverview = useQuery({
    queryKey: ['comparison-overview', telegramRunId],
    queryFn: ({ signal }) => getOverview(telegramRunId, signal),
    enabled: telegramEnabled,
    retry: false,
  });
  const twitterDetail = useQuery({
    queryKey: ['comparison-run-detail', twitterRunId],
    queryFn: ({ signal }) => getRun(twitterRunId, signal),
    enabled: twitterEnabled,
    retry: false,
  });
  const telegramDetail = useQuery({
    queryKey: ['comparison-run-detail', telegramRunId],
    queryFn: ({ signal }) => getRun(telegramRunId, signal),
    enabled: telegramEnabled,
    retry: false,
  });
  const twitterArtifacts = useQuery({
    queryKey: ['comparison-artifacts', twitterRunId],
    queryFn: ({ signal }) => getArtifacts(twitterRunId, signal),
    enabled: twitterEnabled,
    retry: false,
  });
  const telegramArtifacts = useQuery({
    queryKey: ['comparison-artifacts', telegramRunId],
    queryFn: ({ signal }) => getArtifacts(telegramRunId, signal),
    enabled: telegramEnabled,
    retry: false,
  });

  return {
    ...dashboard,
    twitterOverview,
    telegramOverview,
    twitterDetail,
    telegramDetail,
    twitterArtifacts,
    telegramArtifacts,
    isLoading: [
      twitterOverview,
      telegramOverview,
      twitterDetail,
      telegramDetail,
      twitterArtifacts,
      telegramArtifacts,
    ].some((query) => query.isPending && query.fetchStatus !== 'idle'),
  };
}
