import { Amplify } from 'aws-amplify';

export type AuthMode = 'local' | 'cognito';

export interface CognitoAuthConfig {
  userPoolId: string;
  userPoolClientId: string;
  cognitoDomain: string;
  redirectUri: string;
}

export function getAuthMode(): AuthMode {
  const rawMode = import.meta.env.VITE_AUTH_MODE;
  if (!rawMode || rawMode.trim() === '') {
    return 'local';
  }
  const mode = rawMode.toLowerCase().trim();
  if (mode === 'local') {
    return 'local';
  }
  if (mode === 'cognito') {
    return 'cognito';
  }
  throw new Error(
    `Invalid VITE_AUTH_MODE: "${rawMode}". Allowed values are "local" or "cognito".`
  );
}

export function getCognitoConfig(): CognitoAuthConfig {
  const userPoolId = import.meta.env.VITE_COGNITO_USER_POOL_ID?.trim();
  const userPoolClientId = import.meta.env.VITE_COGNITO_CLIENT_ID?.trim();
  const rawDomain = import.meta.env.VITE_COGNITO_DOMAIN?.trim();
  const redirectUri = import.meta.env.VITE_COGNITO_REDIRECT_URI?.trim();

  const missing: string[] = [];
  if (!userPoolId) missing.push('VITE_COGNITO_USER_POOL_ID');
  if (!userPoolClientId) missing.push('VITE_COGNITO_CLIENT_ID');
  if (!rawDomain) missing.push('VITE_COGNITO_DOMAIN');
  if (!redirectUri) missing.push('VITE_COGNITO_REDIRECT_URI');

  if (missing.length > 0) {
    throw new Error(
      `Cognito authentication configuration missing required environment variables: ${missing.join(', ')}`
    );
  }

  const cognitoDomain = rawDomain.replace(/^https?:\/\//i, '').replace(/\/$/, '');

  return {
    userPoolId,
    userPoolClientId,
    cognitoDomain,
    redirectUri,
  };
}

let isConfigured = false;

export function configureAuth(): { authMode: AuthMode; config?: CognitoAuthConfig } {
  const authMode = getAuthMode();
  if (authMode === 'local') {
    return { authMode: 'local' };
  }

  const config = getCognitoConfig();
  if (!isConfigured) {
    Amplify.configure({
      Auth: {
        Cognito: {
          userPoolId: config.userPoolId,
          userPoolClientId: config.userPoolClientId,
          loginWith: {
            oauth: {
              domain: config.cognitoDomain,
              scopes: ['openid', 'email', 'profile'],
              redirectSignIn: [config.redirectUri],
              redirectSignOut: [config.redirectUri],
              responseType: 'code',
            },
          },
        },
      },
    });
    isConfigured = true;
  }

  return { authMode: 'cognito', config };
}
