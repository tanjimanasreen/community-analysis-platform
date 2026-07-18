import React from 'react';
import { Link } from 'react-router-dom';
import ArtifactUnavailableState from '../states/ArtifactUnavailableState';
import ErrorState from '../states/ErrorState';
import LoadingState from '../states/LoadingState';
import { formatCount } from '../../features/overview/overviewUtils';

export default function TransitionsSankey({ transitions, hasArtifact, isLoading, error, onRetry, search }) {
  if (isLoading) return <LoadingState title="Loading community transitions" />;
  if (!hasArtifact) {
    return (
      <ArtifactUnavailableState
        artifactName="Community transitions"
        message="The selected run does not list the community_transitions artifact."
        action={<Link className="text-primary hover:underline" to={`/methodology${search}`}>Why this artifact is optional</Link>}
      />
    );
  }
  if (error) return <ErrorState error={error} title="Community transitions could not be loaded" onRetry={onRetry} />;
  const records = transitions?.records ?? [];
  if (records.length === 0) {
    return (
      <section className="bg-panel border border-border rounded-xl p-8 text-center min-h-[220px] flex items-center justify-center">
        <div>
          <p className="font-semibold text-text-heading">No transition records available</p>
          <p className="mt-2 text-sm text-muted">The artifact exists but contains no transitions for this run.</p>
        </div>
      </section>
    );
  }
  const average = records.reduce((sum, row) => sum + row.jaccard_score, 0) / records.length;
  const strongest = [...records].sort((a, b) => b.jaccard_score - a.jaccard_score).slice(0, 6);

  return (
    <section className="bg-panel border border-border rounded-xl p-5 flex flex-col h-full">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-text-heading">Community Transitions</h3>
          <p className="mt-1 text-xs text-muted">Top member-overlap links from the canonical transition artifact.</p>
        </div>
        <div className="rounded-lg border border-border bg-panel-soft px-3 py-2 text-right">
          <p className="text-[10px] uppercase tracking-wider text-muted">Average Jaccard</p>
          <p className="text-lg font-bold text-text-heading">{average.toFixed(2)}</p>
        </div>
      </div>
      <div className="mt-5 space-y-3">
        {strongest.map((row, index) => (
          <div key={`${row.start_month}-${row.start_month_community}-${row.end_month}-${row.end_month_community}-${index}`} className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-3">
            <div className="rounded-lg border border-border bg-panel-soft/50 px-3 py-2 text-xs text-text-heading truncate">
              {row.start_month} · C{row.start_month_community}
            </div>
            <div className="flex flex-col items-center gap-1 min-w-20">
              <span className="text-[10px] text-muted">{row.jaccard_score.toFixed(2)}</span>
              <div className="h-2 w-full rounded-full bg-border overflow-hidden" title={`Jaccard similarity ${row.jaccard_score}`}>
                <div className="h-full rounded-full bg-primary" style={{ width: `${Math.max(2, Math.min(100, row.jaccard_score * 100))}%` }} />
              </div>
            </div>
            <div className="rounded-lg border border-border bg-panel-soft/50 px-3 py-2 text-xs text-text-heading truncate text-right">
              {row.end_month} · C{row.end_month_community}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 flex justify-between text-xs text-muted">
        <span>{formatCount(records.length)} transition records</span>
        <Link className="text-primary hover:underline" to={`/transitions${search}`}>Open transitions</Link>
      </div>
    </section>
  );
}
