import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DashboardContext, type DashboardContextValue } from '../../../app/dashboardContext';
import type { MetricName, RunSummary } from '../../../types/api';
import { getTransitions } from '../../../api/evolution';
import { getCentralityLeaders, getCommunities } from '../../../api/networks';
import { getOverview } from '../../../api/overview';
import { getArtifacts } from '../../../api/runs';
import { getThemes, getTopics } from '../../../api/topics';
import { useEvidenceData } from '../useEvidenceData';
import type { EvidenceView } from '../evidenceModel';

vi.mock('../../../api/evolution', () => ({ getTransitions: vi.fn() }));
vi.mock('../../../api/networks', () => ({ getCentralityLeaders: vi.fn(), getCommunities: vi.fn() }));
vi.mock('../../../api/overview', () => ({ getOverview: vi.fn() }));
vi.mock('../../../api/runs', () => ({ getArtifacts: vi.fn() }));
vi.mock('../../../api/topics', () => ({ getThemes: vi.fn(), getTopics: vi.fn() }));

function Probe({ view, communitySearch = '' }: { view: EvidenceView; communitySearch?: string }) {
  const data = useEvidenceData({ view, offset: 0, limit: 25, communitySearch });
  const location = useLocation();
  return (
    <div>
      <span data-testid="period">{data.selectedPeriod || 'none'}</span>
      <span data-testid="location">{location.search}</span>
      <span data-testid="total">{data.page?.total ?? 'none'}</span>
    </div>
  );
}

function run(runId: string): RunSummary {
  return {
    run_id: runId,
    status: 'completed',
    platform: 'twitter',
    content_type: 'reply',
    date_start: '2017-01-01',
    date_end: '2017-04-30',
    year: 2017,
    month: 4,
    started_at: null,
    completed_at: null,
    artifact_count: 10,
  };
}

function contextValue(metric: MetricName): DashboardContextValue {
  const selected = run('run-a');
  return {
    health: { status: 'ok', read_only: true, schema_version: '1' },
    runs: [selected],
    selectedRunId: 'run-a',
    selectedRun: selected,
    selectedRunDetail: { run_id: 'run-a', status: 'completed', dataset: {}, code: {}, pipeline: {}, artifact_count: 10, failure: null },
    verification: { run_id: 'run-a', ok: true, status: 'valid', checked_artifacts: 10, error_code: null, error: null },
    metric,
    facets: { platforms: ['twitter'], contentTypes: ['reply'], years: [2017], months: [4] },
    isLoading: false,
    isRunMetadataLoading: false,
    healthError: null,
    runsError: null,
    runDetailError: null,
    verificationError: null,
    setSelectedRunId: () => undefined,
    selectedPlatform: 'twitter',
    setSelectedPlatform: () => undefined,
    setMetric: () => undefined,
    retryInitial: () => undefined,
    retryRunMetadata: () => undefined,
  };
}

function renderProbe(view: EvidenceView, entry: string, communitySearch = '', metric: MetricName = 'if') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <QueryClientProvider client={client}>
        <DashboardContext.Provider value={contextValue(metric)}>
          <Probe view={view} communitySearch={communitySearch} />
        </DashboardContext.Provider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

const overview = {
  run_id: 'run-a', platform: 'twitter', content_type: 'reply', date_start: '2017-01-01', date_end: '2017-04-30',
  total_users: null, total_messages: null, total_interactions: null,
  if_users: 12, wif_users: 11, if_messages: 30, wif_messages: 29,
  if_community_count: 2, wif_community_count: 2, matched_community_count: 1, matched_percentage: 50,
  persistent_community_count: null, available_periods: ['2017-03', '2017-04'],
  periods: [
    { period: '2017-03', if_users: 10, wif_users: 9, if_messages: 20, wif_messages: 19, interaction_records: 20, if_community_count: 2, wif_community_count: 2, matched_community_count: 1, matched_percentage: 50 },
    { period: '2017-04', if_users: 12, wif_users: 11, if_messages: 30, wif_messages: 29, interaction_records: 30, if_community_count: 2, wif_community_count: 2, matched_community_count: 1, matched_percentage: 50 },
  ],
  run_summary: { interaction_records: 50, persistent_community_count: null, month_count: 2 },
  top_themes: [], model_metadata: {}, config_metadata: {},
};

describe('useEvidenceData', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getOverview).mockResolvedValue(overview);
    vi.mocked(getCommunities).mockResolvedValue({ run_id: 'run-a', metric: 'if', period: '2017-04', communities: [], total: 0, limit: 25, offset: 0 });
    vi.mocked(getCentralityLeaders).mockResolvedValue({ run_id: 'run-a', metric: 'if', periods: [], methodology_note: 'persisted' });
    vi.mocked(getTopics).mockResolvedValue({ run_id: 'run-a', topic_type: 'matched', records: [], total: 0, limit: 25, offset: 0 });
    vi.mocked(getThemes).mockResolvedValue({ run_id: 'run-a', records: [], total: 0, limit: 25, offset: 0, provider_metadata: null });
    vi.mocked(getTransitions).mockResolvedValue({ run_id: 'run-a', records: [], total: 0, limit: 25, offset: 0 });
    vi.mocked(getArtifacts).mockResolvedValue({ run_id: 'run-a', artifacts: [], total: 0 });
  });

  it('defaults monthly structural evidence to the latest period and scopes communities by period + metric', async () => {
    renderProbe('communities', '/data-reports?run=run-a&metric=if&view=communities');

    expect(await screen.findByTestId('period')).toHaveTextContent('2017-04');
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('period=2017-04'));
    await waitFor(() => expect(getCommunities).toHaveBeenCalledWith(
      'run-a',
      expect.objectContaining({ period: '2017-04', metric: 'if', limit: 25, offset: 0 }),
      expect.anything(),
    ));
  });

  it('uses the period-aware centrality leaders read model instead of the raw centrality table', async () => {
    renderProbe('centrality', '/data-reports?run=run-a&metric=wif&view=centrality&period=2017-03', '', 'wif');
    await waitFor(() => expect(getCentralityLeaders).toHaveBeenCalledWith(
      'run-a',
      { period: '2017-03', metric: 'wif' },
      expect.anything(),
    ));
  });

  it('scopes matched LDA to period plus exact community without adding a single metric filter', async () => {
    renderProbe('matched-lda', '/data-reports?run=run-a&metric=wif&view=matched-lda&period=2017-03', '12', 'wif');
    await waitFor(() => expect(getTopics).toHaveBeenCalledWith(
      'run-a',
      expect.objectContaining({ type: 'matched', period: '2017-03', community_id: '12' }),
      expect.anything(),
    ));
    expect(vi.mocked(getTopics).mock.calls[0][1]).not.toHaveProperty('metric');
  });

  it('scopes partial-match LDA to period plus exact community without adding a single metric filter', async () => {
    renderProbe('partial-lda', '/data-reports?run=run-a&metric=if&view=partial-lda&period=2017-03', '12', 'if');
    await waitFor(() => expect(getTopics).toHaveBeenCalledWith(
      'run-a',
      expect.objectContaining({ type: 'partial', period: '2017-03', community_id: '12' }),
      expect.anything(),
    ));
    expect(vi.mocked(getTopics).mock.calls[0][1]).not.toHaveProperty('metric');
  });

  it('scopes generated-theme reads to period plus exact community without adding a single metric filter', async () => {
    renderProbe('themes', '/data-reports?run=run-a&metric=wif&view=themes&period=2017-03', '12', 'wif');
    await waitFor(() => expect(getThemes).toHaveBeenCalledWith(
      'run-a',
      expect.objectContaining({ period: '2017-03', community_id: '12' }),
      expect.anything(),
    ));
    expect(vi.mocked(getThemes).mock.calls[0][1]).not.toHaveProperty('metric');
  });

  it('keeps transitions longitudinal', async () => {
    renderProbe('transitions', '/data-reports?run=run-a&metric=wif&view=transitions&period=2017-03', '', 'wif');
    await waitFor(() => expect(getTransitions).toHaveBeenCalledWith(
      'run-a',
      { limit: 25, offset: 0 },
      expect.anything(),
    ));
    expect(getOverview).not.toHaveBeenCalled();
  });

  it('keeps outputs run-scoped', async () => {
    renderProbe('outputs', '/data-reports?run=run-a&metric=wif&view=outputs&period=2017-03', '', 'wif');
    await waitFor(() => expect(getArtifacts).toHaveBeenCalledWith('run-a', expect.anything()));
    expect(getOverview).not.toHaveBeenCalled();
    expect(getCommunities).not.toHaveBeenCalled();
    expect(getCentralityLeaders).not.toHaveBeenCalled();
    expect(getTopics).not.toHaveBeenCalled();
    expect(getThemes).not.toHaveBeenCalled();
    expect(getTransitions).not.toHaveBeenCalled();
  });
});
