import { ShieldAlert } from 'lucide-react';
import type { VerificationResponse } from '../../types/api';

export default function VerificationFailureState({
  verification,
}: {
  verification: VerificationResponse;
}) {
  return (
    <section
      className="min-h-56 rounded-2xl border border-danger/30 bg-panel/80 p-8 flex items-center justify-center"
      role="alert"
      aria-live="assertive"
    >
      <div className="max-w-xl text-center">
        <ShieldAlert className="mx-auto text-danger" size={32} />
        <h2 className="mt-4 text-lg font-semibold text-text-heading">
          Run verification failed
        </h2>
        <p className="mt-2 text-sm text-muted">
          {verification.error || 'The selected run failed artifact integrity verification.'}
        </p>
        {verification.error_code && (
          <p className="mt-3 font-mono text-xs text-danger">
            {verification.error_code}
          </p>
        )}
      </div>
    </section>
  );
}
