import { FileQuestion } from 'lucide-react';

interface ArtifactUnavailableStateProps {
  artifactName?: string;
}

export default function ArtifactUnavailableState({
  artifactName = 'This optional artifact',
}: ArtifactUnavailableStateProps) {
  return (
    <section
      className="min-h-48 rounded-2xl border border-border bg-panel/80 p-8 flex items-center justify-center"
      aria-live="polite"
    >
      <div className="max-w-md text-center">
        <FileQuestion className="mx-auto text-muted" size={30} />
        <h2 className="mt-4 text-lg font-semibold text-text-heading">
          Artifact not generated
        </h2>
        <p className="mt-2 text-sm text-muted">
          {artifactName} is not available for the selected run.
        </p>
      </div>
    </section>
  );
}
