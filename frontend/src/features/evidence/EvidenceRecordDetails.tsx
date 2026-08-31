import { Download, ExternalLink, X } from 'lucide-react';
import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { downloadRunArtifact } from '../../api/reports';
import ArtifactValue from '../../components/ArtifactValue';
import type { MetricName } from '../../types/api';
import { navigationCommunityId, type EvidenceView } from './evidenceModel';

interface EvidenceRecordDetailsProps {
  record: Record<string, unknown> | null;
  view: EvidenceView;
  metric: MetricName;
  period: string;
  runId: string;
  currentSearch: string;
  communitySearch: string;
  onClose: () => void;
}

export default function EvidenceRecordDetails({
  record,
  view,
  metric,
  period,
  runId,
  currentSearch,
  communitySearch,
  onClose,
}: EvidenceRecordDetailsProps) {
  const action = useMemo(
    () => record ? relatedAction(view, record, metric, period, currentSearch, communitySearch) : null,
    [communitySearch, currentSearch, metric, period, record, view],
  );

  if (!record) {
    return (
      <aside className="panel p-6 xl:sticky xl:top-4 xl:self-start">
        <h2 className="font-semibold text-text-heading">Record details</h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          Select a data row to inspect its normalized values. Output artifacts expose manifest metadata here rather than file contents.
        </p>
      </aside>
    );
  }

  const artifactKey = view === 'outputs' && typeof record.key === 'string' ? record.key : null;
  const isDownloadable = artifactKey && record.category !== 'intermediate';

  return (
    <aside className="panel p-5 xl:sticky xl:top-4 xl:self-start xl:max-h-[calc(100dvh-8rem)] xl:overflow-y-auto">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-text-heading">{view === 'outputs' ? 'Artifact metadata' : 'Normalized data record'}</h2>
          <p className="mt-1 text-xs leading-5 text-muted">Values are rendered safely without evaluating persisted artifact text.</p>
        </div>
        <button type="button" aria-label="Close record details" onClick={onClose} className="rounded p-1 text-muted hover:bg-surface-soft"><X size={15} /></button>
      </div>

      <dl className="mt-5 space-y-3">
        {Object.entries(record).map(([key, value]) => (
          <div key={key} className="rounded-lg border border-border/70 bg-bg/30 p-3">
            <dt className="text-[11px] font-semibold text-muted">{key}</dt>
            <dd className="mt-1 text-xs text-text-heading"><ArtifactValue value={value} /></dd>
          </div>
        ))}
      </dl>

      {action && (
        <Link
          to={action.href}
          className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary/10 px-3 py-2 text-xs font-semibold text-primary hover:bg-primary/15"
        >
          {action.label} <ExternalLink size={13} aria-hidden="true" />
        </Link>
      )}

      {view === 'outputs' && (
        isDownloadable && artifactKey ? (
          <button
            type="button"
            onClick={() => downloadRunArtifact(runId, artifactKey)}
            className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text-heading hover:bg-surface-soft cursor-pointer"
          >
            <Download size={13} aria-hidden="true" /> Download verified artifact
          </button>
        ) : (
          <p className="mt-3 rounded-lg border border-border bg-surface-soft/40 p-3 text-xs leading-5 text-muted">
            Intermediate artifacts are retained for provenance but are not downloadable through the read-only API.
          </p>
        )
      )}
    </aside>
  );
}

function relatedAction(
  view: EvidenceView,
  record: Record<string, unknown>,
  metric: MetricName,
  period: string,
  currentSearch: string,
  communitySearch: string,
): { href: string; label: string } | null {
  const params = new URLSearchParams(currentSearch);
  params.delete('view');

  if (view === 'communities') {
    const communityId = navigationCommunityId(record, metric);
    if (!communityId || !period) return null;
    params.set('period', period);
    params.set('metric', metric);
    params.set('community', communityId);
    return { href: `/communities?${params.toString()}`, label: `Explore ${metric.toUpperCase()} community ${communityId}` };
  }

  if (view === 'centrality') {
    if (period) params.set('period', period);
    params.set('metric', metric);
    return { href: `/?${params.toString()}`, label: 'Open Overview structural context' };
  }

  if (view === 'matched-lda' || view === 'partial-lda' || view === 'themes') {
    if (period) params.set('period', period);
    if (view === 'matched-lda' || view === 'partial-lda') {
      params.set('topicType', view === 'partial-lda' ? 'partial' : 'matched');
    }
    if (communitySearch) params.set('semanticCommunity', communitySearch);
    return { href: `/thematic?${params.toString()}`, label: 'Open Thematic Analysis' };
  }

  if (view === 'transitions') {
    params.delete('period');
    return { href: `/evolution?${params.toString()}`, label: 'Open Community Evolution' };
  }

  return null;
}
