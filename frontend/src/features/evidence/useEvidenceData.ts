import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { getCentralityLeaders, getCommunities } from '../../api/networks';
import { getOverview } from '../../api/overview';
import { getArtifacts } from '../../api/runs';
import { getThemes, getTopics } from '../../api/topics';
import { getTransitions } from '../../api/evolution';
import { PERIOD_PARAM, updateDashboardSearchParams } from '../../app/dashboardSearchParams';
import { useDashboardContext } from '../../hooks/useDashboardContext';
import {
  EVIDENCE_VIEWS,
  adaptCentralityLeader,
  adaptCommunities,
  adaptThemes,
  adaptTopics,
  adaptTransitions,
  type EvidencePage,
  type EvidenceView,
} from './evidenceModel';

interface EvidenceOptions {
  view: EvidenceView;
  offset: number;
  limit: number;
  communitySearch: string;
}

export function useEvidenceData({ view, offset, limit, communitySearch }: EvidenceOptions) {
  const dashboard = useDashboardContext();
  const [searchParams, setSearchParams] = useSearchParams();
  const { selectedRunId, selectedRun, verification, metric } = dashboard;
  const definition = EVIDENCE_VIEWS[view];
  const enabled = Boolean(
    selectedRunId && selectedRun?.status === 'completed' && verification?.ok,
  );

  const overviewQuery = useQuery({
    queryKey: ['evidence-overview-periods', selectedRunId],
    queryFn: ({ signal }) => getOverview(selectedRunId, signal),
    enabled: enabled && definition.requiresPeriod,
    retry: false,
  });

  const requestedPeriod = searchParams.get(PERIOD_PARAM);
  const periods = overviewQuery.data?.available_periods ?? [];
  const selectedPeriod = requestedPeriod && periods.includes(requestedPeriod)
    ? requestedPeriod
    : periods.at(-1) ?? '';
  const periodEnabled = enabled && (!definition.requiresPeriod || Boolean(selectedPeriod));
  const exactCommunityId = definition.supportsCommunitySearch && communitySearch.trim()
    ? communitySearch.trim()
    : undefined;

  useEffect(() => {
    if (!definition.requiresPeriod || !overviewQuery.data || !selectedPeriod || requestedPeriod === selectedPeriod) return;
    setSearchParams(
      updateDashboardSearchParams(searchParams, { period: selectedPeriod }),
      { replace: true },
    );
  }, [
    definition.requiresPeriod,
    overviewQuery.data,
    requestedPeriod,
    searchParams,
    selectedPeriod,
    setSearchParams,
  ]);

  const communitiesQuery = useQuery({
    queryKey: ['evidence', 'communities', selectedRunId, selectedPeriod, metric, limit, offset],
    queryFn: ({ signal }) => getCommunities(
      selectedRunId,
      { period: selectedPeriod, metric, limit, offset },
      signal,
    ),
    enabled: periodEnabled && view === 'communities',
    retry: false,
  });

  const centralityQuery = useQuery({
    queryKey: ['evidence', 'centrality', selectedRunId, selectedPeriod, metric],
    queryFn: ({ signal }) => getCentralityLeaders(
      selectedRunId,
      { period: selectedPeriod, metric },
      signal,
    ),
    enabled: periodEnabled && view === 'centrality',
    retry: false,
  });

  const matchedTopicsQuery = useQuery({
    queryKey: ['evidence', 'matched-lda', selectedRunId, selectedPeriod, exactCommunityId, limit, offset],
    queryFn: ({ signal }) => getTopics(
      selectedRunId,
      { type: 'matched', period: selectedPeriod, community_id: exactCommunityId, limit, offset },
      signal,
    ),
    enabled: periodEnabled && view === 'matched-lda',
    retry: false,
  });

  const partialTopicsQuery = useQuery({
    queryKey: ['evidence', 'partial-lda', selectedRunId, selectedPeriod, exactCommunityId, limit, offset],
    queryFn: ({ signal }) => getTopics(
      selectedRunId,
      { type: 'partial', period: selectedPeriod, community_id: exactCommunityId, limit, offset },
      signal,
    ),
    enabled: periodEnabled && view === 'partial-lda',
    retry: false,
  });

  const themesQuery = useQuery({
    queryKey: ['evidence', 'themes', selectedRunId, selectedPeriod, exactCommunityId, limit, offset],
    queryFn: ({ signal }) => getThemes(
      selectedRunId,
      { period: selectedPeriod, community_id: exactCommunityId, limit, offset },
      signal,
    ),
    enabled: periodEnabled && view === 'themes',
    retry: false,
  });

  const transitionsQuery = useQuery({
    queryKey: ['evidence', 'transitions', selectedRunId, limit, offset],
    queryFn: ({ signal }) => getTransitions(selectedRunId, { limit, offset }, signal),
    enabled: enabled && view === 'transitions',
    retry: false,
  });

  const artifactsQuery = useQuery({
    queryKey: ['evidence', 'outputs', selectedRunId],
    queryFn: ({ signal }) => getArtifacts(selectedRunId, signal),
    enabled: enabled && view === 'outputs',
    retry: false,
  });

  const query = (() => {
    switch (view) {
      case 'communities': return communitiesQuery;
      case 'centrality': return centralityQuery;
      case 'matched-lda': return matchedTopicsQuery;
      case 'partial-lda': return partialTopicsQuery;
      case 'themes': return themesQuery;
      case 'transitions': return transitionsQuery;
      case 'outputs': return artifactsQuery;
    }
  })();

  let page: EvidencePage | null = null;
  switch (view) {
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
        const period = centralityQuery.data.periods.find((item) => item.period === selectedPeriod)
          ?? centralityQuery.data.periods[0];
        const records = period
          ? [adaptCentralityLeader(period, centralityQuery.data.methodology_note)]
          : [];
        page = { records, total: records.length, limit: 1, offset: 0 };
      }
      break;
    case 'matched-lda':
      if (matchedTopicsQuery.data) {
        page = {
          records: adaptTopics(matchedTopicsQuery.data.records),
          total: matchedTopicsQuery.data.total,
          limit: matchedTopicsQuery.data.limit,
          offset: matchedTopicsQuery.data.offset,
        };
      }
      break;
    case 'partial-lda':
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
    case 'outputs':
      break;
  }

  return {
    ...dashboard,
    definition,
    enabled,
    overviewQuery,
    periods,
    selectedPeriod,
    setSelectedPeriod: (period: string) => setSearchParams(
      updateDashboardSearchParams(searchParams, { period }),
    ),
    exactCommunitySearch: definition.supportsCommunitySearch,
    query,
    page,
    artifactsQuery,
  };
}
