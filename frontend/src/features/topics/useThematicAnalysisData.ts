import { useQuery } from '@tanstack/react-query';
import { getThemeSimilarity } from '../../api/evolution';
import { getOverview } from '../../api/overview';
import { getThemes, getTopics } from '../../api/topics';
import { useDashboardContext } from '../../hooks/useDashboardContext';
import type { TopicType } from '../../types/api';

const SUMMARY_LIMIT = 500;

interface ThematicDataOptions {
  topicType: TopicType;
  communityId: string | null;
  month: string | null;
  topicOffset: number;
  topicLimit: number;
  themeOffset: number;
  themeLimit: number;
}

export function useThematicAnalysisData({
  topicType,
  communityId,
  month,
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
      'thematic-topics', selectedRunId, topicType, communityId, topicLimit, topicOffset,
    ],
    queryFn: ({ signal }) => getTopics(
      selectedRunId,
      {
        type: topicType,
        community_id: communityId ?? undefined,
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
        month: month ?? undefined,
        community_id: communityId ?? undefined,
        limit: themeLimit,
        offset: themeOffset,
      },
      signal,
    ),
    enabled,
    retry: false,
  });
  const themeSummaryQuery = useQuery({
    queryKey: ['thematic-theme-summary', selectedRunId, month, communityId, SUMMARY_LIMIT],
    queryFn: ({ signal }) => getThemes(
      selectedRunId,
      {
        month: month ?? undefined,
        community_id: communityId ?? undefined,
        limit: SUMMARY_LIMIT,
        offset: 0,
      },
      signal,
    ),
    enabled,
    retry: false,
  });
  const themeCatalogQuery = useQuery({
    queryKey: ['thematic-theme-catalog', selectedRunId, SUMMARY_LIMIT],
    queryFn: ({ signal }) => getThemes(selectedRunId, { limit: SUMMARY_LIMIT, offset: 0 }, signal),
    enabled,
    retry: false,
  });
  const similarityQuery = useQuery({
    queryKey: ['thematic-similarity', selectedRunId],
    queryFn: ({ signal }) => getThemeSimilarity(selectedRunId, signal),
    enabled,
    retry: false,
  });

  return {
    ...dashboard,
    overviewQuery,
    topicsQuery,
    themesQuery,
    themeSummaryQuery,
    themeCatalogQuery,
    similarityQuery,
    retrySemanticData: () => {
      void overviewQuery.refetch();
      void topicsQuery.refetch();
      void themesQuery.refetch();
      void themeSummaryQuery.refetch();
      void themeCatalogQuery.refetch();
      void similarityQuery.refetch();
    },
  };
}
