import { useQuery } from '@tanstack/react-query';
import { getOverview } from '../../api/overview';
import { getArtifacts } from '../../api/runs';
import { useDashboardContext } from '../../hooks/useDashboardContext';

export function useMethodologyData() {
  const dashboard = useDashboardContext();
  const enabled = Boolean(
    dashboard.selectedRunId &&
    dashboard.selectedRun?.status === 'completed' &&
    dashboard.verification?.ok,
  );
  const overviewQuery = useQuery({
    queryKey: ['methodology-overview', dashboard.selectedRunId],
    queryFn: ({ signal }) => getOverview(dashboard.selectedRunId, signal),
    enabled,
    retry: false,
  });
  const artifactsQuery = useQuery({
    queryKey: ['methodology-artifacts', dashboard.selectedRunId],
    queryFn: ({ signal }) => getArtifacts(dashboard.selectedRunId, signal),
    enabled,
    retry: false,
  });
  return { ...dashboard, overviewQuery, artifactsQuery };
}
