import { useQuery } from '@tanstack/react-query';
import { getArtifacts } from '../../api/runs';
import { useDashboardContext } from '../../hooks/useDashboardContext';

export function useArtifactLibrary() {
  const dashboard = useDashboardContext();
  const enabled = Boolean(
    dashboard.selectedRunId &&
    dashboard.selectedRun?.status === 'completed' &&
    dashboard.verification?.ok,
  );
  const artifactsQuery = useQuery({
    queryKey: ['artifact-library', dashboard.selectedRunId],
    queryFn: ({ signal }) => getArtifacts(dashboard.selectedRunId, signal),
    enabled,
    retry: false,
  });
  return { ...dashboard, artifactsQuery };
}
