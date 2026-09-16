import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';
import App from '../../App';
import { testServer } from '../../test/server';

describe('dashboard verification gate', () => {
  it('blocks analytical panels when selected-run verification fails', async () => {
    let overviewRequests = 0;
    vi.stubEnv('VITE_AUTH_MODE', 'local');
    window.history.pushState({}, '', '/');
    testServer.use(
      http.get('*/api/v1/health', () =>
        HttpResponse.json({ status: 'ok', read_only: true, schema_version: '1' }),
      ),
      http.get('*/api/v1/runs', () =>
        HttpResponse.json({
          runs: [{
            run_id: 'run-invalid', status: 'completed', platform: 'twitter', content_type: 'reply',
            date_start: '2017-03-01', date_end: '2017-03-31', year: 2017, month: 3,
            started_at: null, completed_at: null, artifact_count: 2,
          }],
          total: 1,
        }),
      ),
      http.get('*/api/v1/runs/run-invalid', () =>
        HttpResponse.json({
          run_id: 'run-invalid', status: 'completed', dataset: {}, code: {}, pipeline: {},
          artifact_count: 2, failure: null,
        }),
      ),
      http.get('*/api/v1/runs/run-invalid/verification', () =>
        HttpResponse.json({
          run_id: 'run-invalid', ok: false, status: 'invalid', checked_artifacts: 0,
          error_code: 'ARTIFACT_CHECKSUM_MISMATCH', error: 'Checksum mismatch.',
        }),
      ),
      http.get('*/api/v1/runs/run-invalid/overview', () => {
        overviewRequests += 1;
        return HttpResponse.json({});
      }),
    );
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <App />
      </QueryClientProvider>,
    );

    expect(await screen.findByText('Run verification failed')).toBeInTheDocument();
    expect(screen.getByText('ARTIFACT_CHECKSUM_MISMATCH')).toBeInTheDocument();
    expect(overviewRequests).toBe(0);
  });
});
