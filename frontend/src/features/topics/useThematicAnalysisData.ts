import { useQuery } from '@tanstack/react-query';
import { getOverview } from '../../api/overview';
import {
  getClusteredThemeEvidence,
  getClusteredThemeTimeline,
  getThemes,
  getTopics,
} from '../../api/topics';
import { useDashboardContext } from '../../hooks/useDashboardContext';

interface ThematicDataOptions {
  communityId: string | null;
  month: string | null;
  canonicalThemeId: string | null;
  timelineStart: string | null;
  timelineEnd: string | null;
  topicOffset: number;
  topicLimit: number;
  themeOffset: number;
  themeLimit: number;
}

export function useThematicAnalysisData({
  communityId,
  month,
  canonicalThemeId,
  timelineStart,
  timelineEnd,
  topicOffset,
  topicLimit,
  themeOffset,
  themeLimit,
}: ThematicDataOptions) {
  const dashboard = useDashboardContext();
  const { selectedRunId, selectedRun, verification } = dashboard;
  const enabled = Boolean(
    selectedRunId && selectedRun?.status === 'completed' && verification?.ok,
  );

  const overviewQuery = useQuery({
    queryKey: ['thematic-overview', selectedRunId],
    queryFn: ({ signal }) => getOverview(selectedRunId, signal),
    enabled,
  });
  const topicsQuery = useQuery({
    queryKey: [
      'thematic-topics', selectedRunId, 'matched', communityId, month, topicLimit, topicOffset,
    ],
    queryFn: ({ signal }) => getTopics(
      selectedRunId,
      {
        type: 'matched',
        community_id: communityId ?? undefined,
        period: month ?? undefined,
        limit: topicLimit,
        offset: topicOffset,
      },
      signal,
    ),
    enabled,
    retry: false,
  });
  const themesQuery = useQuery({
    queryKey: [
      'thematic-themes', selectedRunId, month, communityId, themeLimit, themeOffset,
    ],
    queryFn: ({ signal }) => getThemes(
      selectedRunId,
      {
        period: month ?? undefined,
        community_id: communityId ?? undefined,
        limit: themeLimit,
        offset: themeOffset,
      },
      signal,
    ),
    enabled,
    retry: false,
  });
  const timelineQuery = useQuery({
    queryKey: ['thematic-theme-timeline', selectedRunId, timelineStart, timelineEnd],
    queryFn: ({ signal }) => getClusteredThemeTimeline(
      selectedRunId,
      {
        period_start: timelineStart ?? undefined,
        period_end: timelineEnd ?? undefined,
        scope: 'matched',
      },
      signal,
    ),
    enabled,
    retry: false,
  });

  const clusterEvidenceQuery = useQuery({
    queryKey: ['thematic-cluster-evidence', selectedRunId, month, canonicalThemeId],
    queryFn: ({ signal }) => getClusteredThemeEvidence(
      selectedRunId,
      {
        period: month ?? '',
        canonical_theme_id: canonicalThemeId ?? '',
        limit: 100,
        offset: 0,
      },
      signal,
    ),
    enabled: enabled && Boolean(month && canonicalThemeId),
    retry: false,
  });

  return {
    ...dashboard,
    overviewQuery,
    topicsQuery,
    themesQuery,
    timelineQuery,
    clusterEvidenceQuery,
    retrySemanticData: () => {
      void overviewQuery.refetch();
      void topicsQuery.refetch();
      void themesQuery.refetch();
      void timelineQuery.refetch();
      if (canonicalThemeId) void clusterEvidenceQuery.refetch();
    },
  };
}
