import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchAuthSession } from 'aws-amplify/auth';
import { apiClient } from '../client';

vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: vi.fn(),
}));

describe('apiClient authentication interceptor', () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
    vi.clearAllMocks();
  });

  it('does not attach Authorization header in local auth mode', async () => {
    vi.stubEnv('VITE_AUTH_MODE', 'local');
    const headersMap = new Map();
    const config = await (apiClient.interceptors.request as any).handlers[0].fulfilled({
      headers: headersMap,
    });
    expect(config.headers.get?.('Authorization')).toBeUndefined();
  });

  it('attaches Bearer token in cognito auth mode when session is valid', async () => {
    vi.stubEnv('VITE_AUTH_MODE', 'cognito');
    vi.mocked(fetchAuthSession).mockResolvedValue({
      tokens: {
        accessToken: {
          toString: () => 'mock-jwt-access-token',
        } as any,
      },
    });

    const headersMap = new Map();
    const config = await (apiClient.interceptors.request as any).handlers[0].fulfilled({
      headers: headersMap,
    });
    expect(config.headers.get('Authorization')).toBe('Bearer mock-jwt-access-token');
  });
});
