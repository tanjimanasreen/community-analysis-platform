import { useQuery } from '@tanstack/react-query';
import { getTransitions } from '../../api/evolution';
import { getCentrality, getCommunities } from '../../api/networks';
import { getArtifacts } from '../../api/runs';
import { getThemes, getTopics } from '../../api/topics';
import { useDashboardContext } from '../../hooks/useDashboardContext';
import {
  adaptArtifacts,
  adaptCentrality,
  adaptCommunities,
  adaptThemes,
  adaptTopics,
  adaptTransitions,
  type ExplorerMode,
  type ExplorerPage,
  modeSupportsExactCommunitySearch,
} from './explorerModel';

interface ExplorerOptions {
  mode: ExplorerMode;
  offset: number;
  limit: number;
  search: string;
}

export function useExplorerData({ mode, offset, limit, search }: ExplorerOptions) {
  const dashboard = useDashboardContext();
  const { selectedRunId, selectedRun, verification, metric } = dashboard;
  const enabled = Boolean(
    selectedRunId && selectedRun?.status === 'completed' && verification?.ok,
  );
  const exactCommunityId = modeSupportsExactCommunitySearch(mode) && search.trim()
    ? search.trim()
    : undefined;

  const communitiesQuery = useQuery({
    queryKey: ['explorer', 'communities', selectedRunId, metric, limit, offset],
    queryFn: ({ signal }) => getCommunities(selectedRunId, { metric, limit, offset }, signal),
    enabled: enabled && mode === 'communities',
  });
  const centralityQuery = useQuery({
    queryKey: ['explorer', 'centrality', selectedRunId, limit, offset],
    queryFn: ({ signal }) => getCentrality(selectedRunId, { limit, offset }, signal),
    enabled: enabled && mode === 'centrality',
  });
  const matchedTopicsQuery = useQuery({
    queryKey: ['explorer', 'matched-topics', selectedRunId, exactCommunityId, limit, offset],
    queryFn: ({ signal }) => getTopics(
      selectedRunId,
      { type: 'matched', community_id: exactCommunityId, limit, offset },
      signal,
    ),
    enabled: enabled && mode === 'matched-topics',
    retry: false,
  });
  const partialTopicsQuery = useQuery({
    queryKey: ['explorer', 'partial-topics', selectedRunId, exactCommunityId, limit, offset],
    queryFn: ({ signal }) => getTopics(
      selectedRunId,
      { type: 'partial', community_id: exactCommunityId, limit, offset },
      signal,
    ),
    enabled: enabled && mode === 'partial-topics',
    retry: false,
  });
  const themesQuery = useQuery({
    queryKey: ['explorer', 'themes', selectedRunId, exactCommunityId, limit, offset],
    queryFn: ({ signal }) => getThemes(
      selectedRunId,
      { community_id: exactCommunityId, limit, offset },
      signal,
    ),
    enabled: enabled && mode === 'themes',
    retry: false,
  });
  const transitionsQuery = useQuery({
    queryKey: ['explorer', 'transitions', selectedRunId, limit, offset],
    queryFn: ({ signal }) => getTransitions(selectedRunId, { limit, offset }, signal),
    enabled: enabled && mode === 'transitions',
    retry: false,
  });
  const artifactsQuery = useQuery({
    queryKey: ['explorer', 'artifacts', selectedRunId],
    queryFn: ({ signal }) => getArtifacts(selectedRunId, signal),
    enabled: enabled && mode === 'artifacts',
  });

  const query = (() => {
    switch (mode) {
      case 'communities': return communitiesQuery;
      case 'centrality': return centralityQuery;
      case 'matched-topics': return matchedTopicsQuery;
      case 'partial-topics': return partialTopicsQuery;
      case 'themes': return themesQuery;
      case 'transitions': return transitionsQuery;
      case 'artifacts': return artifactsQuery;
    }
  })();

  let page: ExplorerPage | null = null;
  switch (mode) {
    case 'communities':
      if (communitiesQuery.data) {
        page = {
          records: adaptCommunities(communitiesQuery.data.communities),
          total: communitiesQuery.data.total,
          limit: communitiesQuery.data.limit,
          offset: communitiesQuery.data.offset,
        };
      }
      break;
    case 'centrality':
      if (centralityQuery.data) {
        page = {
          records: adaptCentrality(centralityQuery.data.records),
          total: centralityQuery.data.total,
          limit: centralityQuery.data.limit,
          offset: centralityQuery.data.offset,
        };
      }
      break;
    case 'matched-topics':
      if (matchedTopicsQuery.data) {
        page = {
          records: adaptTopics(matchedTopicsQuery.data.records),
          total: matchedTopicsQuery.data.total,
          limit: matchedTopicsQuery.data.limit,
          offset: matchedTopicsQuery.data.offset,
        };
      }
      break;
    case 'partial-topics':
      if (partialTopicsQuery.data) {
        page = {
          records: adaptTopics(partialTopicsQuery.data.records),
          total: partialTopicsQuery.data.total,
          limit: partialTopicsQuery.data.limit,
          offset: partialTopicsQuery.data.offset,
        };
      }
      break;
    case 'themes':
      if (themesQuery.data) {
        page = {
          records: adaptThemes(themesQuery.data.records),
          total: themesQuery.data.total,
          limit: themesQuery.data.limit,
          offset: themesQuery.data.offset,
        };
      }
      break;
    case 'transitions':
      if (transitionsQuery.data) {
        page = {
          records: adaptTransitions(transitionsQuery.data.records),
          total: transitionsQuery.data.total,
          limit: transitionsQuery.data.limit,
          offset: transitionsQuery.data.offset,
        };
      }
      break;
    case 'artifacts':
      if (artifactsQuery.data) {
        const records = adaptArtifacts(artifactsQuery.data.artifacts);
        page = {
          records: records.slice(offset, offset + limit),
          total: records.length,
          limit,
          offset,
        };
      }
      break;
  }

  return {
    ...dashboard,
    query,
    page,
    exactCommunitySearch: modeSupportsExactCommunitySearch(mode),
  };
}
