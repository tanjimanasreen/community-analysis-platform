import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { DashboardContext, type DashboardContextValue } from '../../../app/dashboardContext';
import { testServer } from '../../../test/server';
import type { MetricName, RunSummary } from '../../../types/api';
import { useCommunitiesWorkspaceData } from '../useCommunitiesWorkspaceData';

const requests: string[] = [];

function Probe() {
  const data = useCommunitiesWorkspaceData({ offset: 0, limit: 15, minWeight: 2 });
  const location = useLocation();
  return (
    <div>
      <span data-testid="period">{data.selectedPeriod || 'none'}</span>
      <span data-testid="location">{location.search}</span>
      <span data-testid="detail-period">{data.detailQuery.data?.period || 'loading'}</span>
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

function renderProbe(metric: MetricName, entry = '/communities?run=run-a&metric=if&community=7') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <QueryClientProvider client={client}>
        <DashboardContext.Provider value={contextValue(metric)}>
          <Probe />
        </DashboardContext.Provider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe('useCommunitiesWorkspaceData', () => {
  it('defaults to the latest period and scopes every selected-community read to that month', async () => {
    requests.length = 0;
    installHandlers();
    renderProbe('if');

    expect(await screen.findByTestId('period')).toHaveTextContent('2017-04');
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('period=2017-04'));
    await waitFor(() => expect(screen.getByTestId('detail-period')).toHaveTextContent('2017-04'));

    const relevant = requests.filter((url) =>
      url.includes('/communities') || url.includes('/network') || url.includes('/topics/7') || url.includes('/themes/7'),
    );
    expect(relevant.length).toBeGreaterThanOrEqual(5);
    for (const url of relevant) expect(url).toContain('period=2017-04');
    expect(requests.some((url) => url.includes('/communities/7') && url.includes('min_weight=2'))).toBe(true);
    expect(requests.some((url) => url.includes('/network') && url.includes('view=communities'))).toBe(true);
  });

  it('clears a month-local community when the IF/WIF partition changes', async () => {
    requests.length = 0;
    installHandlers();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const entry = '/communities?run=run-a&metric=if&period=2017-04&community=7';
    const view = (metric: MetricName) => (
      <MemoryRouter initialEntries={[entry]}>
        <QueryClientProvider client={client}>
          <DashboardContext.Provider value={contextValue(metric)}>
            <Probe />
          </DashboardContext.Provider>
        </QueryClientProvider>
      </MemoryRouter>
    );
    const rendered = render(view('if'));

    await screen.findByText('2017-04');
    expect(screen.getByTestId('location')).toHaveTextContent('community=7');

    rendered.rerender(view('wif'));

    await waitFor(() => expect(screen.getByTestId('location')).not.toHaveTextContent('community=7'));
    expect(requests.some((url) => url.includes('/communities/7') && url.includes('metric=wif'))).toBe(false);
  });
});

function installHandlers() {
  testServer.use(
    http.get('*/api/v1/runs/run-a/overview', () => HttpResponse.json({
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
    })),
    http.get('*/api/v1/runs/run-a/communities', ({ request }) => {
      requests.push(request.url);
      return HttpResponse.json({ run_id: 'run-a', metric: 'if', period: '2017-04', communities: [{ community_id: '7', node_count: 5, edge_count: 4, total_weight: 8 }], total: 1, limit: 15, offset: 0 });
    }),
    http.get('*/api/v1/runs/run-a/communities/7', ({ request }) => {
      requests.push(request.url);
      return HttpResponse.json({
        run_id: 'run-a', metric: 'if', period: '2017-04', community: { community_id: '7', node_count: 5, edge_count: 4, total_weight: 8 },
        graph: { run_id: 'run-a', metric: 'if', period: '2017-04', community_id: '7', view: 'users', nodes: [], edges: [], available_nodes: 5, available_edges: 4, returned_nodes: 5, returned_edges: 4, sampled: false },
      });
    }),
    http.get('*/api/v1/runs/run-a/network', ({ request }) => {
      requests.push(request.url);
      return HttpResponse.json({ run_id: 'run-a', metric: 'if', period: '2017-04', community_id: null, view: 'communities', nodes: [], edges: [], available_nodes: 2, available_edges: 0, returned_nodes: 2, returned_edges: 0, sampled: false });
    }),
    http.get('*/api/v1/runs/run-a/topics/7', ({ request }) => {
      requests.push(request.url);
      return HttpResponse.json({ run_id: 'run-a', topic_type: 'matched', records: [], total: 0, limit: 100, offset: 0 });
    }),
    http.get('*/api/v1/runs/run-a/themes/7', ({ request }) => {
      requests.push(request.url);
      return HttpResponse.json({ run_id: 'run-a', records: [], total: 0, limit: 100, offset: 0, provider_metadata: null });
    }),
  );
}
