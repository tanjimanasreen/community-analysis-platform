import axios from 'axios';
import type { ApiErrorEnvelope } from '../types/api';

export class DashboardApiError extends Error {
  readonly code: string;
  readonly status: number | null;
  readonly runId: string | null;
  readonly artifactKey: string | null;
  readonly details: Record<string, unknown> | null;
  readonly requestId: string | null;

  constructor({
    code,
    message,
    status = null,
    runId = null,
    artifactKey = null,
    details = null,
    requestId = null,
  }: {
    code: string;
    message: string;
    status?: number | null;
    runId?: string | null;
    artifactKey?: string | null;
    details?: Record<string, unknown> | null;
    requestId?: string | null;
  }) {
    super(message);
    this.name = 'DashboardApiError';
    this.code = code;
    this.status = status;
    this.runId = runId;
    this.artifactKey = artifactKey;
    this.details = details;
    this.requestId = requestId;
  }
}

function isApiEnvelope(value: unknown): value is ApiErrorEnvelope {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<ApiErrorEnvelope>;
  return typeof candidate.code === 'string' && typeof candidate.message === 'string';
}

export function normalizeApiError(error: unknown): DashboardApiError {
  if (error instanceof DashboardApiError) return error;

  if (axios.isAxiosError(error)) {
    const payload = error.response?.data;
    if (isApiEnvelope(payload)) {
      return new DashboardApiError({
        code: payload.code,
        message: payload.message,
        status: error.response?.status ?? null,
        runId: payload.run_id ?? null,
        artifactKey: payload.artifact_key ?? null,
        details: payload.details ?? null,
        requestId: error.response?.headers?.['x-request-id'] ?? null,
      });
    }

    if (error.code === 'ECONNABORTED') {
      return new DashboardApiError({
        code: 'REQUEST_TIMEOUT',
        message: 'The dashboard API did not respond before the request timed out.',
      });
    }

    return new DashboardApiError({
      code: error.code || 'API_UNAVAILABLE',
      message: error.message || 'The dashboard API could not be reached.',
      status: error.response?.status ?? null,
      requestId: error.response?.headers?.['x-request-id'] ?? null,
    });
  }

  if (error instanceof Error) {
    return new DashboardApiError({
      code: 'UNEXPECTED_ERROR',
      message: error.message,
    });
  }

  return new DashboardApiError({
    code: 'UNEXPECTED_ERROR',
    message: 'An unexpected dashboard error occurred.',
  });
}
