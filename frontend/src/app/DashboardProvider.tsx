import { useEffect, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { getHealth, getRun, getRuns, getVerification } from '../api/runs';
import {
  deriveRunFacets,
  METRIC_PARAM,
  resolveMetric,
  RUN_PARAM,
  selectDefaultRunId,
  updateDashboardSearchParams,
} from './dashboardSearchParams';
import { DashboardContext, type DashboardContextValue } from './dashboardContext';

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [searchParams, setSearchParams] = useSearchParams();

  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: ({ signal }) => getHealth(signal),
  });
  const runsQuery = useQuery({
    queryKey: ['runs'],
    queryFn: ({ signal }) => getRuns({}, signal),
  });

  const runs = runsQuery.data?.runs ?? [];
  const facets = deriveRunFacets(runs);
  const requestedRunId = searchParams.get(RUN_PARAM);
  const selectedRunId = selectDefaultRunId(runs, requestedRunId);
  const metric = resolveMetric(searchParams.get(METRIC_PARAM));

  useEffect(() => {
    if (runsQuery.isPending || runsQuery.isError) return;
    const requestedMetric = searchParams.get(METRIC_PARAM);
    const runIsCanonical = requestedRunId === selectedRunId;
    const metricIsCanonical = requestedMetric === metric;
    if (runIsCanonical && metricIsCanonical) return;

    setSearchParams(
      updateDashboardSearchParams(searchParams, {
        runId: selectedRunId,
        metric,
      }),
      { replace: true },
    );
  }, [
    metric,
    requestedRunId,
    runsQuery.isError,
    runsQuery.isPending,
    searchParams,
    selectedRunId,
    setSearchParams,
  ]);

  const runDetailQuery = useQuery({
    queryKey: ['run', selectedRunId],
    queryFn: ({ signal }) => getRun(selectedRunId, signal),
    enabled: Boolean(selectedRunId),
  });
  const verificationQuery = useQuery({
    queryKey: ['run-verification', selectedRunId],
    queryFn: ({ signal }) => getVerification(selectedRunId, signal),
    enabled: Boolean(selectedRunId),
  });

  const selectedRun = runs.find((run) => run.run_id === selectedRunId) ?? null;
  const selectedPlatform = selectedRun?.platform ?? facets.platforms[0] ?? '';

  const value: DashboardContextValue = {
    health: healthQuery.data ?? null,
    runs,
    selectedRunId,
    selectedRun,
    selectedRunDetail: runDetailQuery.data ?? null,
    verification: verificationQuery.data ?? null,
    metric,
    facets,
    isLoading: healthQuery.isPending || runsQuery.isPending,
    isRunMetadataLoading:
      Boolean(selectedRunId) &&
      (runDetailQuery.isPending || verificationQuery.isPending),
    healthError: healthQuery.error,
    runsError: runsQuery.error,
    runDetailError: runDetailQuery.error,
    verificationError: verificationQuery.error,
    setSelectedRunId: (runId) =>
      setSearchParams(updateDashboardSearchParams(searchParams, { runId })),
    selectedPlatform,
    setSelectedPlatform: (platform) => {
      const nextRun = runs.find((run) => run.status === 'completed' && run.platform === platform)
        ?? runs.find((run) => run.platform === platform);
      if (nextRun) {
        setSearchParams(updateDashboardSearchParams(searchParams, { runId: nextRun.run_id }));
      }
    },
    setMetric: (nextMetric) =>
      setSearchParams(
        updateDashboardSearchParams(searchParams, { metric: nextMetric }),
      ),
    retryInitial: () => {
      void healthQuery.refetch();
      void runsQuery.refetch();
    },
    retryRunMetadata: () => {
      void runDetailQuery.refetch();
      void verificationQuery.refetch();
    },
  };

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}
