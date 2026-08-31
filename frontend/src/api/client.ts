import axios, { type AxiosRequestConfig } from 'axios';
import { fetchAuthSession } from 'aws-amplify/auth';
import { normalizeApiError } from './errors';
import { getAuthMode } from '../auth/authConfig';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
const configuredTimeout = Number(import.meta.env.VITE_API_TIMEOUT_MS || 30_000);
export const API_TIMEOUT_MS = Number.isFinite(configuredTimeout) && configuredTimeout > 0
  ? configuredTimeout
  : 30_000;

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
  headers: {
    Accept: 'application/json',
  },
});

// Centralized request interceptor for Cognito Bearer token injection
apiClient.interceptors.request.use(async (config) => {
  if (getAuthMode() === 'cognito') {
    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.accessToken?.toString();
      if (token) {
        config.headers.set('Authorization', `Bearer ${token}`);
      }
    } catch {
      // In unauthenticated state, proceed without header so API returns 401
    }
  }
  return config;
});

export async function getJson<T>(
  url: string,
  config: AxiosRequestConfig = {},
): Promise<T> {
  try {
    const response = await apiClient.get<T>(url, config);
    return response.data;
  } catch (error) {
    throw normalizeApiError(error);
  }
}

export async function downloadAuthenticatedBlob(
  url: string,
  filename?: string,
): Promise<void> {
  try {
    const response = await apiClient.get(url, { responseType: 'blob' });
    const blob = new Blob([response.data]);
    const blobUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = blobUrl;
    if (filename) {
      link.setAttribute('download', filename);
    } else {
      link.setAttribute('target', '_blank');
      link.setAttribute('rel', 'noopener noreferrer');
    }
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => window.URL.revokeObjectURL(blobUrl), 1000);
  } catch (error) {
    throw normalizeApiError(error);
  }
}

export async function openAuthenticatedReport(
  url: string,
): Promise<void> {
  try {
    const response = await apiClient.get(url, { responseType: 'blob' });
    const blob = new Blob([response.data], { type: 'text/markdown' });
    const blobUrl = window.URL.createObjectURL(blob);
    window.open(blobUrl, '_blank', 'noopener,noreferrer');
    setTimeout(() => window.URL.revokeObjectURL(blobUrl), 60_000);
  } catch (error) {
    throw normalizeApiError(error);
  }
}

export function absoluteApiUrl(path: string): string {
  if (/^https?:\/\//i.test(API_BASE_URL)) {
    return new URL(path.replace(/^\//, ''), `${API_BASE_URL.replace(/\/$/, '')}/`).toString();
  }
  return `${API_BASE_URL.replace(/\/$/, '')}/${path.replace(/^\//, '')}`;
}
