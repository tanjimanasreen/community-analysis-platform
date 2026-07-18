import { useQuery } from '@tanstack/react-query';
import {
  getMembershipChanges,
  getPersistentCommunities,
  getThemeSimilarity,
  getTransitions,
} from '../../api/evolution';
import { useDashboardContext } from '../../hooks/useDashboardContext';

export function useTransitionData(limit = 1000, offset = 0) {
  const dashboard = useDashboardContext();
  const enabled = Boolean(
    dashboard.selectedRunId &&
    dashboard.selectedRun?.status === 'completed' &&
    dashboard.verification?.ok,
  );
  const transitionsQuery = useQuery({
    queryKey: ['transitions-page', dashboard.selectedRunId, limit, offset],
    queryFn: ({ signal }) => getTransitions(
      dashboard.selectedRunId,
      { limit, offset },
      signal,
    ),
    enabled,
    retry: false,
  });
  const persistentQuery = useQuery({
    queryKey: ['persistent-communities-page', dashboard.selectedRunId],
    queryFn: ({ signal }) => getPersistentCommunities(dashboard.selectedRunId, signal),
    enabled,
    retry: false,
  });
  const membershipQuery = useQuery({
    queryKey: ['membership-changes-page', dashboard.selectedRunId],
    queryFn: ({ signal }) => getMembershipChanges(dashboard.selectedRunId, signal),
    enabled,
    retry: false,
  });
  const similarityQuery = useQuery({
    queryKey: ['transition-theme-similarity', dashboard.selectedRunId],
    queryFn: ({ signal }) => getThemeSimilarity(dashboard.selectedRunId, signal),
    enabled,
    retry: false,
  });
  return {
    ...dashboard,
    transitionsQuery,
    persistentQuery,
    membershipQuery,
    similarityQuery,
  };
}
