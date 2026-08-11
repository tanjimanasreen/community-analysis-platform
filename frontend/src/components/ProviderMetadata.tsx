import ArtifactValue from './ArtifactValue';
import {
  buildProviderMetadataViewModel,
  shortenDigest,
  type ProviderMetadataItem,
} from '../features/themes/providerMetadataModel';

interface ProviderMetadataProps {
  providerMetadata?: Record<string, unknown> | null;
  modelMetadata?: Record<string, unknown> | null;
}

export default function ProviderMetadata({
  providerMetadata,
  modelMetadata,
}: ProviderMetadataProps) {
  const metadata = buildProviderMetadataViewModel(providerMetadata, modelMetadata);

  return (
    <section className="rounded-xl border border-border bg-panel p-5">
      <h2 className="text-lg font-bold text-text-heading">Theme provider and model provenance</h2>
      <p className="mt-1 max-w-4xl text-xs text-muted">
        Label-generation configuration and compact runtime provenance for this run. LDA topics and keywords remain the analytical input.
      </p>

      {!metadata.hasMetadata ? (
        <p className="mt-4 rounded-lg border border-border bg-panel-soft/40 p-3 text-xs text-muted">
          Provider metadata unavailable for this run.
        </p>
      ) : (
        <div className="mt-4 space-y-5">
          {metadata.configuration.length > 0 && (
            <MetadataGroup title="Generation configuration" items={metadata.configuration} />
          )}

          {metadata.operational.length > 0 && (
            <MetadataGroup title="Operational summary" items={metadata.operational} compact />
          )}

          {metadata.timing.length > 0 && (
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wide text-muted">Performance summary</h3>
              <div className="mt-2 grid grid-cols-1 gap-3 md:grid-cols-3">
                {metadata.timing.map((summary) => (
                  <div key={summary.key} className="rounded-lg border border-border/70 bg-bg/30 p-3">
                    <p className="text-xs font-semibold text-text-heading">{summary.label}</p>
                    <dl className="mt-2 grid grid-cols-3 gap-2 text-xs">
                      <TimingValue label="p50" value={formatMilliseconds(summary.p50Ms)} />
                      <TimingValue label="p95" value={formatMilliseconds(summary.p95Ms)} />
                      <TimingValue label="Samples" value={formatInteger(summary.sampleCount)} />
                    </dl>
                  </div>
                ))}
              </div>
            </div>
          )}

          {metadata.advanced.length > 0 && (
            <details className="rounded-lg border border-border/70 bg-bg/20">
              <summary className="cursor-pointer px-4 py-3 text-xs font-semibold text-text-heading">
                Advanced provenance
              </summary>
              <dl className="grid grid-cols-1 gap-3 border-t border-border/60 p-4 sm:grid-cols-2">
                {metadata.advanced.map((item) => (
                  <MetadataField key={item.key} item={item} />
                ))}
              </dl>
            </details>
          )}

          {metadata.rawRunMetrics && (
            <details className="rounded-lg border border-border/70 bg-bg/20">
              <summary className="cursor-pointer px-4 py-3 text-xs font-semibold text-text-heading">
                Raw run metrics
              </summary>
              <div className="border-t border-border/60 p-4 text-xs text-text-heading">
                {metadata.promptPayloadOmitted && (
                  <p className="mb-3 rounded-lg border border-border/70 bg-surface-soft/30 p-3 text-muted">
                    Prompt and response payloads are not displayed in the dashboard.
                  </p>
                )}
                <ArtifactValue value={metadata.rawRunMetrics} maxItems={20} />
              </div>
            </details>
          )}
        </div>
      )}
    </section>
  );
}

function MetadataGroup({
  title,
  items,
  compact = false,
}: {
  title: string;
  items: ProviderMetadataItem[];
  compact?: boolean;
}) {
  return (
    <div>
      <h3 className="text-xs font-bold uppercase tracking-wide text-muted">{title}</h3>
      <dl className={`mt-2 grid grid-cols-1 gap-3 ${compact ? 'sm:grid-cols-2 xl:grid-cols-4' : 'sm:grid-cols-2 lg:grid-cols-3'}`}>
        {items.map((item) => <MetadataField key={item.key} item={item} />)}
      </dl>
    </div>
  );
}

function MetadataField({ item }: { item: ProviderMetadataItem }) {
  return (
    <div className="min-w-0 rounded-lg border border-border/70 bg-bg/30 p-3">
      <dt className="text-[11px] text-muted">{item.label}</dt>
      <dd className="mt-1 min-w-0 break-words text-sm font-semibold text-text-heading">
        {item.kind === 'currency' ? (
          formatCurrency(item.value)
        ) : item.kind === 'digest' ? (
          <DigestValue value={item.value} />
        ) : (
          <ArtifactValue value={item.value} compact />
        )}
      </dd>
    </div>
  );
}

function DigestValue({ value }: { value: unknown }) {
  const full = String(value ?? '').trim();
  return (
    <span className="block truncate font-mono text-xs" title={full} aria-label={full}>
      {shortenDigest(full)}
    </span>
  );
}

function TimingValue({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted">{label}</dt>
      <dd className="mt-0.5 font-semibold text-text-heading">{value}</dd>
    </div>
  );
}

function formatInteger(value: unknown): string {
  const numeric = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(numeric)
    ? new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(numeric)
    : 'Unavailable';
}

function formatCurrency(value: unknown): string {
  const numeric = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(numeric)
    ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 4 }).format(numeric)
    : 'Unavailable';
}

function formatMilliseconds(value: number): string {
  if (!Number.isFinite(value)) return 'Unavailable';
  if (Math.abs(value) >= 1000) {
    return `${new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value / 1000)} s`;
  }
  return `${new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(value)} ms`;
}
