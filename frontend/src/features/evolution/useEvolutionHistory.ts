import { useQueries } from '@tanstack/react-query';
import { getOverview } from '../../api/overview';
import { useDashboardContext } from '../../hooks/useDashboardContext';
import { compatibleCompletedRuns, type RunOverviewRecord } from './runCompatibility';

const MAX_HISTORY_RUNS = 12;

export function useEvolutionHistory() {
  const dashboard = useDashboardContext();
  const compatibleRuns = compatibleCompletedRuns(
    dashboard.runs,
    dashboard.selectedRun,
    MAX_HISTORY_RUNS,
  );
  const enabled = Boolean(dashboard.verification?.ok && dashboard.selectedRun?.status === 'completed');
  const results = useQueries({
    queries: compatibleRuns.map((run) => ({
      queryKey: ['evolution-run-overview', run.run_id],
      queryFn: ({ signal }: { signal: AbortSignal }) => getOverview(run.run_id, signal),
      enabled,
      staleTime: 60_000,
      retry: false,
    })),
  });
  const history: RunOverviewRecord[] = [];
  results.forEach((result, index) => {
    if (result.data) history.push({ run: compatibleRuns[index], overview: result.data });
  });
  return {
    ...dashboard,
    compatibleRuns,
    history,
    isLoading: results.some((result) => result.isPending),
    errors: results.map((result) => result.error).filter(Boolean),
    retry: () => results.forEach((result) => void result.refetch()),
  };
}
