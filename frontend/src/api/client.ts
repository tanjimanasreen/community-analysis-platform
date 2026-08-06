import axios, { type AxiosRequestConfig } from 'axios';
import { normalizeApiError } from './errors';

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

export function absoluteApiUrl(path: string): string {
  if (/^https?:\/\//i.test(API_BASE_URL)) {
    return new URL(path.replace(/^\//, ''), `${API_BASE_URL.replace(/\/$/, '')}/`).toString();
  }
  return `${API_BASE_URL.replace(/\/$/, '')}/${path.replace(/^\//, '')}`;
}
