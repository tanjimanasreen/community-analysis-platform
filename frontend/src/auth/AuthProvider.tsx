import React, { useEffect, useState, type ReactNode } from 'react';
import {
  fetchAuthSession,
  getCurrentUser,
  signInWithRedirect,
  signOut as amplifySignOut,
  type AuthUser,
} from 'aws-amplify/auth';
import { getAuthMode, configureAuth, type AuthMode } from './authConfig';
import { AuthContext } from './authContext';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authMode] = useState<AuthMode>(() => getAuthMode());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<AuthUser | { username: string } | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function initAuth() {
      if (authMode === 'local') {
        if (isMounted) {
          setUser({ username: 'local-dev' });
          setIsAuthenticated(true);
          setIsLoading(false);
        }
        return;
      }

      try {
        configureAuth();
        const currentUser = await getCurrentUser();
        const session = await fetchAuthSession();
        if (isMounted) {
          if (session.tokens?.accessToken) {
            setUser(currentUser);
            setIsAuthenticated(true);
          } else {
            setUser(null);
            setIsAuthenticated(false);
          }
          setIsLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setUser(null);
          setIsAuthenticated(false);
          setError(err instanceof Error ? err : new Error(String(err)));
          setIsLoading(false);
        }
      }
    }

    initAuth();

    return () => {
      isMounted = false;
    };
  }, [authMode]);

  const signIn = async () => {
    if (authMode === 'local') return;
    try {
      await signInWithRedirect();
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    }
  };

  const signOut = async () => {
    if (authMode === 'local') return;
    try {
      await amplifySignOut();
      setUser(null);
      setIsAuthenticated(false);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    }
  };

  return (
    <AuthContext.Provider
      value={{
        authMode,
        isLoading,
        isAuthenticated,
        user,
        error,
        signIn,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
