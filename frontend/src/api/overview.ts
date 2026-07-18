import type { OverviewResponse } from '../types/api';
import { getJson } from './client';
import { API_ROUTES, fillRoute } from './routes';

export const getOverview = (runId: string, signal?: AbortSignal) =>
  getJson<OverviewResponse>(fillRoute(API_ROUTES.overview, { run_id: runId }), {
    signal,
  });
