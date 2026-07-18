import type {
  ArtifactsResponse,
  HealthResponse,
  RunDetail,
  RunsResponse,
  VerificationResponse,
} from '../types/api';
import { getJson } from './client';
import { API_ROUTES, fillRoute } from './routes';

export interface RunFilters {
  platform?: string;
  content_type?: string;
  year?: number;
  month?: number;
  status?: string;
}

export const getHealth = (signal?: AbortSignal) =>
  getJson<HealthResponse>(API_ROUTES.health, { signal });

export const getRuns = (filters: RunFilters = {}, signal?: AbortSignal) =>
  getJson<RunsResponse>(API_ROUTES.runs, { params: filters, signal });

export const getRun = (runId: string, signal?: AbortSignal) =>
  getJson<RunDetail>(fillRoute(API_ROUTES.runDetail, { run_id: runId }), { signal });

export const getVerification = (runId: string, signal?: AbortSignal) =>
  getJson<VerificationResponse>(
    fillRoute(API_ROUTES.verification, { run_id: runId }),
    { signal },
  );

export const getArtifacts = (runId: string, signal?: AbortSignal) =>
  getJson<ArtifactsResponse>(fillRoute(API_ROUTES.artifacts, { run_id: runId }), {
    signal,
  });
