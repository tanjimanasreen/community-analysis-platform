import { useQuery } from '@tanstack/react-query';
import {
  getEvolutionPathMobility,
  getEvolutionPaths,
  getEvolutionPathThemeSimilarity,
} from '../../api/evolution';
import { useDashboardContext } from '../../hooks/useDashboardContext';
import type { EvolutionThemeType } from '../../types/api';

export function useCommunityEvolutionData(
  pathId: string | null,
  themeType: EvolutionThemeType,
) {
  const dashboard = useDashboardContext();
  const enabled = Boolean(
    dashboard.selectedRunId
    && dashboard.selectedRun?.status === 'completed'
    && dashboard.verification?.ok,
  );

  const pathsQuery = useQuery({
    queryKey: ['community-evolution-paths', dashboard.selectedRunId],
    queryFn: ({ signal }) => getEvolutionPaths(dashboard.selectedRunId, signal),
    enabled,
    retry: false,
  });

  const pathEnabled = enabled && Boolean(pathId);
  const mobilityQuery = useQuery({
    queryKey: ['community-evolution-mobility', dashboard.selectedRunId, pathId],
    queryFn: ({ signal }) => getEvolutionPathMobility(dashboard.selectedRunId, pathId!, signal),
    enabled: pathEnabled,
    retry: false,
  });

  const similarityQuery = useQuery({
    queryKey: [
      'community-evolution-theme-similarity',
      dashboard.selectedRunId,
      pathId,
      themeType,
    ],
    queryFn: ({ signal }) => getEvolutionPathThemeSimilarity(
      dashboard.selectedRunId,
      pathId!,
      themeType,
      signal,
    ),
    enabled: pathEnabled,
    retry: false,
  });


  return {
    ...dashboard,
    pathsQuery,
    mobilityQuery,
    similarityQuery,
  };
}
