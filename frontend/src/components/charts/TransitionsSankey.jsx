import React from 'react';
import { Link } from 'react-router-dom';
import { ResponsiveContainer, Sankey, Tooltip } from 'recharts';
import ArtifactUnavailableState from '../states/ArtifactUnavailableState';
import ErrorState from '../states/ErrorState';
import LoadingState from '../states/LoadingState';
import { formatCount } from '../../features/overview/overviewUtils';
import { buildTransitionSankeyModel } from '../../features/evolution/transitionModel';

export default function TransitionsSankey({
  transitions,
  records,
  hasArtifact = true,
  isLoading = false,
  error,
  onRetry,
  search = '',
  maxLinks = 60,
  compact = false,
}) {
  if (isLoading) return <LoadingState title="Loading community transitions" />;
  if (!hasArtifact) {
    return (
      <ArtifactUnavailableState
        artifactName="Community transitions"
        message="The selected run does not list the community transition artifact."
        action={<Link className="text-primary hover:underline" to={`/methodology${search}`}>Why this artifact is optional</Link>}
      />
    );
  }
  if (error) return <ErrorState error={error} title="Community transitions could not be loaded" onRetry={onRetry} />;
  const transitionRecords = records ?? transitions?.records ?? [];
  if (transitionRecords.length === 0) {
    return (
      <section className="bg-panel border border-border rounded-xl p-8 text-center min-h-[220px] flex items-center justify-center">
        <div>
          <p className="font-semibold text-text-heading">No transition records available</p>
          <p className="mt-2 text-sm text-muted">The artifact exists but contains no transitions for this run.</p>
        </div>
      </section>
    );
  }

  const model = buildTransitionSankeyModel(transitionRecords, maxLinks);
  const average = transitionRecords.reduce((sum, row) => sum + row.jaccard_score, 0) / transitionRecords.length;

  return (
    <section className="bg-panel border border-border rounded-xl p-5 flex flex-col h-full">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-text-heading">Community Transitions</h3>
          <p className="mt-1 text-xs text-muted">Links are encoded by Jaccard membership similarity. Nodes are month/community pairs.</p>
        </div>
        <div className="rounded-lg border border-border bg-panel-soft px-3 py-2 text-right">
          <p className="text-[10px] uppercase tracking-wider text-muted">Average Jaccard</p>
          <p className="text-lg font-bold text-text-heading">{average.toFixed(2)}</p>
        </div>
      </div>
      <div className={compact ? 'mt-4 h-[220px]' : 'mt-5 h-[420px]'} role="img" aria-label="Community transition Sankey diagram">
        <ResponsiveContainer width="100%" height="100%">
          <Sankey
            data={{ nodes: model.nodes, links: model.links }}
            nodePadding={compact ? 12 : 20}
            nodeWidth={10}
            margin={{ top: 10, right: 30, bottom: 10, left: 30 }}
            link={{ stroke: 'var(--color-primary)', strokeOpacity: 0.3 }}
            node={{ fill: 'var(--color-primary)', stroke: 'var(--color-border)' }}
          >
            <Tooltip content={<SankeyTooltip />} />
          </Sankey>
        </ResponsiveContainer>
      </div>
      <div className="mt-4 flex flex-wrap justify-between gap-2 text-xs text-muted">
        <span>{formatCount(model.displayedLinks)} of {formatCount(model.totalLinks)} links displayed</span>
        {compact && <Link className="text-primary hover:underline" to={`/transitions${search}`}>Open transitions</Link>}
      </div>
    </section>
  );
}

function SankeyTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const item = payload[0]?.payload;
  if (!item) return null;
  return (
    <div className="rounded-lg border border-border bg-panel p-3 text-xs shadow-xl">
      {item.startLabel && <p className="font-semibold text-text-heading">{item.startLabel} → {item.endLabel}</p>}
      {typeof item.jaccard === 'number' && <p className="mt-1 text-muted">Jaccard: {item.jaccard.toFixed(3)}</p>}
      {item.name && <p className="font-semibold text-text-heading">{item.name}</p>}
    </div>
  );
}
