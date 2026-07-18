import { FileQuestion } from 'lucide-react';
import type { ReactNode } from 'react';

interface ArtifactUnavailableStateProps {
  artifactName?: string;
  message?: string;
  action?: ReactNode;
}

export default function ArtifactUnavailableState({
  artifactName = 'This optional artifact',
  message,
  action,
}: ArtifactUnavailableStateProps) {
  return (
    <section
      className="min-h-48 rounded-2xl border border-border bg-panel/80 p-8 flex items-center justify-center"
      aria-live="polite"
    >
      <div className="max-w-md text-center">
        <FileQuestion className="mx-auto text-muted" size={30} />
        <h2 className="mt-4 text-lg font-semibold text-text-heading">Artifact not generated</h2>
        <p className="mt-2 text-sm text-muted">
          {message || `${artifactName} is not available for the selected run.`}
        </p>
        {action && <div className="mt-4 text-sm">{action}</div>}
      </div>
    </section>
  );
}
