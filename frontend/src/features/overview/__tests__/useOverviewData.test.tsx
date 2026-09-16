import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { DashboardContext, type DashboardContextValue } from '../../../app/dashboardContext';
import { testServer } from '../../../test/server';
import type { MetricName, RunSummary } from '../../../types/api';
import { useOverviewData } from '../useOverviewData';

const requests: string[] = [];

function Probe() {
  const data = useOverviewData(0, 5);
  return (
    <div>
      <span data-testid="overview-run">{data.overviewQuery.data?.run_id || 'loading'}</span>
      <span data-testid="network-metric">{data.networkQuery.data?.metric || 'loading'}</span>
    </div>
  );
}

function run(runId: string): RunSummary {
  return {
    run_id: runId,
    status: 'completed',
    platform: 'twitter',
    content_type: 'reply',
    date_start: runId === 'run-a' ? '2017-03-01' : '2017-04-01',
    date_end: null,
    year: 2017,
    month: runId === 'run-a' ? 3 : 4,
    started_at: null,
    completed_at: null,
    artifact_count: 4,
  };
}

function contextValue(runId: string, metric: MetricName): DashboardContextValue {
  const selected = run(runId);
  return {
    health: { status: 'ok', read_only: true, schema_version: '1' },
    runs: [selected],
    selectedRunId: runId,
    selectedRun: selected,
    selectedRunDetail: {
      run_id: runId,
      status: 'completed',
      dataset: {},
      code: {},
      pipeline: {},
      artifact_count: 4,
      failure: null,
    },
    verification: {
      run_id: runId,
      ok: true,
      status: 'valid',
      checked_artifacts: 4,
      error_code: null,
      error: null,
    },
    metric,
    selectedPlatform: 'twitter',
    facets: { platforms: ['twitter'], contentTypes: ['reply'], years: [2017], months: [3] },
    isLoading: false,
    isRunMetadataLoading: false,
    healthError: null,
    runsError: null,
    runDetailError: null,
    verificationError: null,
    setSelectedRunId: () => undefined,
    setSelectedPlatform: () => undefined,
    setMetric: () => undefined,
    retryInitial: () => undefined,
    retryRunMetadata: () => undefined,
  };
}

function Wrapper({ value }: { value: DashboardContextValue }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <MemoryRouter>
      <QueryClientProvider client={client}>
        <DashboardContext.Provider value={value}>
          <Probe />
        </DashboardContext.Provider>
      </QueryClientProvider>
    </MemoryRouter>
  );
}

describe('useOverviewData', () => {
  it('keys run-scoped requests by run and metric', async () => {
    requests.length = 0;
    testServer.use(
      http.get('*/api/v1/runs/:runId/overview', ({ params }) =>
        HttpResponse.json(overviewResponse(String(params.runId))),
      ),
      http.get('*/api/v1/runs/:runId/network', ({ request, params }) => {
        requests.push(request.url);
        const metric = new URL(request.url).searchParams.get('metric') || 'if';
        return HttpResponse.json({
          run_id: String(params.runId), metric, community_id: null,
          nodes: [], edges: [], available_nodes: 0, available_edges: 0,
          returned_nodes: 0, returned_edges: 0, sampled: false,
        });
      }),
      http.get('*/api/v1/runs/:runId/communities', ({ request, params }) => {
        requests.push(request.url);
        const metric = new URL(request.url).searchParams.get('metric') || 'if';
        return HttpResponse.json({
          run_id: String(params.runId), metric, communities: [], total: 0, limit: 5, offset: 0,
        });
      }),
      http.get('*/api/v1/runs/:runId/artifacts', ({ params }) =>
        HttpResponse.json({ run_id: String(params.runId), artifacts: [], total: 0 }),
      ),
      http.get('*/api/v1/runs/:runId/centrality-leaders', ({ params }) =>
        HttpResponse.json({ run_id: String(params.runId), metric: 'if', periods: [], methodology_note: 'persisted' }),
      ),
    );

    const { rerender } = render(<Wrapper value={contextValue('run-a', 'if')} />);
    await screen.findByText('run-a');
    await screen.findByText('if');
    expect(requests.some((url) => url.includes('/run-a/network') && url.includes('metric=if'))).toBe(true);

    rerender(<Wrapper value={contextValue('run-b', 'wif')} />);
    await waitFor(() => expect(screen.getByTestId('overview-run')).toHaveTextContent('run-b'));
    await waitFor(() => expect(screen.getByTestId('network-metric')).toHaveTextContent('wif'));
    expect(requests.some((url) => url.includes('/run-b/network') && url.includes('metric=wif'))).toBe(true);
    expect(requests.some((url) => url.includes('/run-b/communities') && url.includes('metric=wif'))).toBe(true);
  });
});

function overviewResponse(runId: string) {
  return {
    run_id: runId,
    platform: 'twitter', content_type: 'reply', date_start: '2017-03-01', date_end: '2017-03-31',
    total_users: 5, total_messages: 20, total_interactions: 4,
    if_users: 5, wif_users: 4, if_messages: 20, wif_messages: 18,
    if_community_count: 3, wif_community_count: 4,
    matched_community_count: 2, matched_percentage: 50,
    persistent_community_count: null, available_periods: ['2017-03'],
    periods: [{ period: '2017-03', if_users: 5, wif_users: 4, if_messages: 20, wif_messages: 18, interaction_records: 20, if_community_count: 3, wif_community_count: 4, matched_community_count: 2, matched_percentage: 50 }],
    run_summary: { interaction_records: 20, persistent_community_count: null, month_count: 1 },
    top_themes: [], model_metadata: {}, config_metadata: {},
  };
}
