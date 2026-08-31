import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AuthGate } from '../AuthGate';
import { AuthProvider } from '../AuthProvider';

describe('AuthGate', () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
  });

  it('renders children immediately when in local auth mode', async () => {
    vi.stubEnv('VITE_AUTH_MODE', 'local');

    render(
      <AuthProvider>
        <AuthGate>
          <div data-testid="protected-content">Protected Analytical Dashboard</div>
        </AuthGate>
      </AuthProvider>
    );

    expect(await screen.findByTestId('protected-content')).toBeInTheDocument();
    expect(screen.getByText('Protected Analytical Dashboard')).toBeInTheDocument();
  });

  it('displays authentication required gate in cognito mode when unauthenticated', async () => {
    vi.stubEnv('VITE_AUTH_MODE', 'cognito');
    vi.stubEnv('VITE_COGNITO_USER_POOL_ID', 'us-east-1_example');
    vi.stubEnv('VITE_COGNITO_CLIENT_ID', 'exampleclient');
    vi.stubEnv('VITE_COGNITO_DOMAIN', 'example.auth.us-east-1.amazoncognito.com');
    vi.stubEnv('VITE_COGNITO_REDIRECT_URI', 'https://example.cloudfront.net');

    render(
      <AuthProvider>
        <AuthGate>
          <div data-testid="protected-content">Protected Analytical Dashboard</div>
        </AuthGate>
      </AuthProvider>
    );

    expect(await screen.findByText('Authentication Required')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sign In/i })).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });
});
