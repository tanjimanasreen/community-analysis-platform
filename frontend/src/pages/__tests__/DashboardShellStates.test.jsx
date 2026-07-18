import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { delay, http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import App from '../../App';
import { testServer } from '../../test/server';

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  );
}

describe('dashboard shell states', () => {
  it('shows the initial connection state while catalog requests are pending', async () => {
    window.history.pushState({}, '', '/');
    testServer.use(
      http.get('*/api/v1/health', async () => {
        await delay(80);
        return HttpResponse.json({ status: 'ok', read_only: true, schema_version: '1' });
      }),
      http.get('*/api/v1/runs', async () => {
        await delay(80);
        return HttpResponse.json({ runs: [], total: 0 });
      }),
    );
    renderApp();
    expect(screen.getByText('Connecting to the dashboard API')).toBeInTheDocument();
    expect(await screen.findByText('No canonical runs found')).toBeInTheDocument();
  });

  it('renders a no-runs state instead of a fixed month fallback', async () => {
    window.history.pushState({}, '', '/');
    testServer.use(
      http.get('*/api/v1/health', () =>
        HttpResponse.json({ status: 'ok', read_only: true, schema_version: '1' }),
      ),
      http.get('*/api/v1/runs', () => HttpResponse.json({ runs: [], total: 0 })),
    );
    renderApp();
    expect(await screen.findByText('No canonical runs found')).toBeInTheDocument();
    expect(screen.queryByText(/May 2024/)).not.toBeInTheDocument();
  });
});
