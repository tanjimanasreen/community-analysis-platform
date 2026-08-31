import { describe, it, expect, beforeEach, vi } from 'vitest';
import { getAuthMode, getCognitoConfig, configureAuth } from '../authConfig';

describe('authConfig', () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
  });

  it('defaults to local auth mode when VITE_AUTH_MODE is unset (undefined)', () => {
    expect(getAuthMode()).toBe('local');
  });

  it('defaults to local auth mode when VITE_AUTH_MODE is empty string or whitespace', () => {
    vi.stubEnv('VITE_AUTH_MODE', '');
    expect(getAuthMode()).toBe('local');

    vi.stubEnv('VITE_AUTH_MODE', '   ');
    expect(getAuthMode()).toBe('local');
  });

  it('accepts explicit local auth mode', () => {
    vi.stubEnv('VITE_AUTH_MODE', 'local');
    expect(getAuthMode()).toBe('local');
  });

  it('resolves cognito auth mode when VITE_AUTH_MODE=cognito', () => {
    vi.stubEnv('VITE_AUTH_MODE', 'cognito');
    expect(getAuthMode()).toBe('cognito');
  });

  it('fails fast on unrecognized non-empty VITE_AUTH_MODE values', () => {
    vi.stubEnv('VITE_AUTH_MODE', 'foo');
    expect(() => getAuthMode()).toThrow(/Invalid VITE_AUTH_MODE: "foo"./);

    vi.stubEnv('VITE_AUTH_MODE', 'production');
    expect(() => getAuthMode()).toThrow(/Invalid VITE_AUTH_MODE: "production"./);
  });

  it('throws an error if cognito mode is missing required variables', () => {
    vi.stubEnv('VITE_AUTH_MODE', 'cognito');
    vi.stubEnv('VITE_COGNITO_USER_POOL_ID', '');
    vi.stubEnv('VITE_COGNITO_CLIENT_ID', '');
    vi.stubEnv('VITE_COGNITO_DOMAIN', '');
    vi.stubEnv('VITE_COGNITO_REDIRECT_URI', '');

    expect(() => getCognitoConfig()).toThrow(/Cognito authentication configuration missing required environment variables/);
  });

  it('successfully returns config when all variables are present in cognito mode', () => {
    vi.stubEnv('VITE_AUTH_MODE', 'cognito');
    vi.stubEnv('VITE_COGNITO_USER_POOL_ID', 'us-east-1_test123');
    vi.stubEnv('VITE_COGNITO_CLIENT_ID', 'client123');
    vi.stubEnv('VITE_COGNITO_DOMAIN', 'https://test-domain.auth.us-east-1.amazoncognito.com/');
    vi.stubEnv('VITE_COGNITO_REDIRECT_URI', 'https://d123.cloudfront.net');

    const config = getCognitoConfig();
    expect(config.userPoolId).toBe('us-east-1_test123');
    expect(config.userPoolClientId).toBe('client123');
    expect(config.cognitoDomain).toBe('test-domain.auth.us-east-1.amazoncognito.com');
    expect(config.redirectUri).toBe('https://d123.cloudfront.net');
  });

  it('configureAuth returns local mode without error when mode is local', () => {
    vi.stubEnv('VITE_AUTH_MODE', 'local');
    const result = configureAuth();
    expect(result.authMode).toBe('local');
  });
});
