import { ChevronDown, FileText, Scale, ShieldCheck, Users, type LucideIcon } from 'lucide-react';
import { Link } from 'react-router-dom';
import ArtifactValue from '../../../components/ArtifactValue';
import ErrorState from '../../../components/states/ErrorState';
import LoadingState from '../../../components/states/LoadingState';
import { THESIS_BASELINE, type MethodologyRunView } from '../methodologyModel';

type QueryLike = {
  isPending: boolean;
  error: unknown;
};

interface Props {
  selectedRunId: string | null;
  runView: MethodologyRunView;
  overviewQuery: QueryLike;
  artifactsQuery: QueryLike;
  search: string;
}

export default function ReproducibilityPanel({ selectedRunId, runView, overviewQuery, artifactsQuery, search }: Props) {
  const error = overviewQuery.error || artifactsQuery.error;

  return (
    <div className="panel p-5 sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-primary"><ShieldCheck size={18} aria-hidden="true" /><p className="text-xs font-semibold uppercase tracking-[0.14em]">Reproducibility</p></div>
          <h2 className="mt-1 text-lg font-bold text-text-heading">Reproducibility & Analytical Contract</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">Thesis defaults and executed-run configuration remain independently auditable.</p>
        </div>
        <span className="max-w-full truncate rounded-full border border-border px-3 py-1 text-xs font-medium text-muted" title={selectedRunId || 'No run selected'}>{selectedRunId || 'No run selected'}</span>
      </div>

      <div className="mt-5 space-y-3">
        <details className="group rounded-2xl border border-border/70 bg-surface-soft/30">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-bold text-text-heading focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">
            <span>Thesis baseline & affinity definitions</span>
            <ChevronDown size={16} className="shrink-0 text-muted transition-transform group-open:rotate-180" aria-hidden="true" />
          </summary>
          <div className="border-t border-border/70 p-4">
            <div className="grid gap-4 xl:grid-cols-[2fr_1fr]">
              <div className="grid gap-3 md:grid-cols-2">
                <BaselineGroup title="Graph thresholds" entries={Object.entries(THESIS_BASELINE.graph_thresholds)} />
                <BaselineGroup title="Louvain" entries={Object.entries(THESIS_BASELINE.louvain)} />
                <BaselineGroup title="LDA" entries={Object.entries(THESIS_BASELINE.lda)} />
                <BaselineGroup title="Temporal analysis" entries={Object.entries(THESIS_BASELINE.temporal)} />
              </div>
              <div className="space-y-3">
                <DefinitionCard icon={Users} title="Interaction Frequency (IF)" text="shared_post: the total number of posts produced by an author and shared by a follower." />
                <DefinitionCard icon={Scale} title="Weighted Interaction Frequency (WIF)" text="weighted_post = shared_post / total_post, where total_post is the author's produced-post count." />
              </div>
            </div>
          </div>
        </details>

        <details className="group rounded-2xl border border-border/70 bg-surface-soft/30">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-bold text-text-heading focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">
            <span>Selected run · resolved metadata</span>
            <ChevronDown size={16} className="shrink-0 text-muted transition-transform group-open:rotate-180" aria-hidden="true" />
          </summary>
          <div className="border-t border-border/70 p-4">
            {(overviewQuery.isPending || artifactsQuery.isPending) ? (
              <LoadingState title="Loading selected-run methodology metadata" />
            ) : error ? (
              <ErrorState error={error} title="Selected-run metadata could not be loaded" />
            ) : (
              <div className="grid gap-4 xl:grid-cols-3">
                <MetadataPanel title="Run and dataset" entries={runView.run} />
                <MetadataPanel title="Resolved configuration" entries={runView.configuration} unavailable="Resolved configuration metadata is absent; the dashboard does not assume baseline defaults were used." />
                <MetadataPanel title="Provider and models" entries={runView.models} unavailable="Provider/model metadata unavailable for this run." />
              </div>
            )}

            <div className="mt-4 rounded-xl border border-border/70 bg-bg/20 p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="text-sm font-bold text-text-heading">Available artifact categories</h3>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {runView.artifactCategories.length > 0 ? runView.artifactCategories.map((category) => (
                      <span key={category} className="rounded-full border border-border bg-bg px-3 py-1 text-xs font-medium text-text-heading">{category}</span>
                    )) : <span className="text-sm text-muted">No artifact categories are listed.</span>}
                  </div>
                </div>
                <Link to={`/data-reports?${withEvidenceView(search, 'outputs')}`} className="inline-flex shrink-0 items-center gap-2 self-start rounded-xl border border-border bg-surface px-3 py-2 text-xs font-semibold text-text-heading hover:border-primary/40 hover:text-primary">
                  <FileText size={15} aria-hidden="true" />
                  Data & reports
                </Link>
              </div>
            </div>
          </div>
        </details>
      </div>
    </div>
  );
}

function withEvidenceView(search: string, view: string) {
  const params = new URLSearchParams(search);
  params.set('view', view);
  return params.toString();
}

function BaselineGroup({ title, entries }: { title: string; entries: Array<[string, unknown]> }) {
  return (
    <div className="rounded-xl border border-border/70 bg-bg/20 p-4">
      <h3 className="text-sm font-bold text-text-heading">{title}</h3>
      <dl className="mt-3 grid gap-2 text-xs">
        {entries.map(([key, value]) => (
          <div key={key} className="flex items-start justify-between gap-4"><dt className="text-muted">{key}</dt><dd className="break-all font-mono font-semibold text-text-heading">{String(value)}</dd></div>
        ))}
      </dl>
    </div>
  );
}

function DefinitionCard({ icon: Icon, title, text }: { icon: LucideIcon; title: string; text: string }) {
  return (
    <div className="flex gap-3 rounded-xl border border-border/70 bg-bg/20 p-4">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon size={18} aria-hidden="true" /></div>
      <div><h3 className="text-sm font-bold text-text-heading">{title}</h3><p className="mt-1 text-xs leading-5 text-muted">{text}</p></div>
    </div>
  );
}

function MetadataPanel({ title, entries, unavailable = 'Metadata unavailable.' }: { title: string; entries: Array<[string, unknown]>; unavailable?: string }) {
  return (
    <div className="rounded-xl border border-border/70 bg-bg/20 p-4">
      <h3 className="text-sm font-bold text-text-heading">{title}</h3>
      {entries.length > 0 ? (
        <dl className="mt-3 space-y-3">
          {entries.map(([key, value]) => (
            <div key={key}><dt className="break-all text-[11px] text-muted">{key}</dt><dd className="mt-1 break-words text-sm font-semibold text-text-heading"><ArtifactValue value={value} /></dd></div>
          ))}
        </dl>
      ) : <p className="mt-3 text-sm text-muted">{unavailable}</p>}
    </div>
  );
}
