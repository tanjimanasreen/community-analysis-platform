import { displayArtifactValue } from '../utils/artifactValues';
import { providerMetadataEntries } from '../features/themes/themeModel';

interface ProviderMetadataProps {
  providerMetadata?: Record<string, unknown> | null;
  modelMetadata?: Record<string, unknown> | null;
}

export default function ProviderMetadata({
  providerMetadata,
  modelMetadata,
}: ProviderMetadataProps) {
  const entries = providerMetadataEntries(providerMetadata, modelMetadata);
  return (
    <section className="rounded-xl border border-border bg-panel p-5">
      <h2 className="text-sm font-bold text-text-heading">Theme provider and model metadata</h2>
      <p className="mt-1 text-xs text-muted">
        These fields describe the downstream label-generation stage. LDA topics and keywords remain the analytical input.
      </p>
      {entries.length === 0 ? (
        <p className="mt-4 rounded-lg border border-border bg-panel-soft/40 p-3 text-xs text-muted">
          Provider metadata unavailable for this run.
        </p>
      ) : (
        <dl className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {entries.map(([key, value]) => (
            <div key={key} className="rounded-lg border border-border/70 bg-bg/30 p-3">
              <dt className="break-all text-[11px] text-muted">{key}</dt>
              <dd className="mt-1 break-words text-sm font-semibold text-text-heading">
                {displayArtifactValue(value)}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}
