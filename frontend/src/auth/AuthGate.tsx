import React, { type ReactNode } from 'react';
import { LogIn, AlertCircle } from 'lucide-react';
import { useAuth } from './useAuth';
import LoadingState from '../components/states/LoadingState';

export function AuthGate({ children }: { children: ReactNode }) {
  const { authMode, isLoading, isAuthenticated, error, signIn } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-bg text-text">
        <LoadingState title="Checking authentication session" />
      </div>
    );
  }

  if (authMode === 'cognito' && !isAuthenticated) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center bg-bg p-6 text-text selection:bg-primary/30">
        <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-8 shadow-xl">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <LogIn size={20} />
            </div>
            <div>
              <h1 className="text-lg font-bold text-text-heading">Authentication Required</h1>
              <p className="text-xs text-muted">Community Analysis Platform</p>
            </div>
          </div>

          <p className="mt-4 text-sm leading-relaxed text-muted">
            This dashboard is protected with Cognito authentication. Please sign in to access analytical data and reports.
          </p>

          {error && (
            <div className="mt-4 flex items-start gap-2.5 rounded-xl border border-danger/30 bg-danger/10 p-3 text-xs text-danger">
              <AlertCircle size={16} className="shrink-0 mt-0.5" />
              <span>{error.message || 'Authentication error'}</span>
            </div>
          )}

          <button
            type="button"
            onClick={signIn}
            className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary/50 cursor-pointer"
          >
            <LogIn size={16} /> Sign In
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
