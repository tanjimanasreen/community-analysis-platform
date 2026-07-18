import { AlertTriangle, RefreshCw } from 'lucide-react';
import { normalizeApiError } from '../../api/errors';

interface ErrorStateProps {
  error: unknown;
  title?: string;
  onRetry?: () => void;
}

export default function ErrorState({
  error,
  title = 'Dashboard data could not be loaded',
  onRetry,
}: ErrorStateProps) {
  const normalized = normalizeApiError(error);

  return (
    <section
      className="min-h-56 rounded-2xl border border-danger/30 bg-panel/80 p-8 flex items-center justify-center"
      role="alert"
      aria-live="assertive"
    >
      <div className="max-w-xl text-center">
        <AlertTriangle className="mx-auto text-danger" size={30} />
        <h2 className="mt-4 text-lg font-semibold text-text-heading">{title}</h2>
        <p className="mt-2 text-sm text-muted">{normalized.message}</p>
        <details className="mt-4 text-left text-xs text-muted">
          <summary className="cursor-pointer text-text-heading">Technical details</summary>
          <pre className="mt-2 overflow-x-auto whitespace-pre-wrap rounded-lg border border-border bg-bg/60 p-3">
            {JSON.stringify(
              {
                code: normalized.code,
                status: normalized.status,
                run_id: normalized.runId,
                artifact_key: normalized.artifactKey,
                details: normalized.details,
              },
              null,
              2,
            )}
          </pre>
        </details>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-5 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90"
          >
            <RefreshCw size={16} />
            Retry
          </button>
        )}
      </div>
    </section>
  );
}
