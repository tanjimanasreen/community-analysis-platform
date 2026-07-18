import { Hash, Network, Tags, X } from 'lucide-react';
import { normalizeApiError } from '../../api/errors';
import type { CommunityDetail, MetricName, ThemeRecord, TopicRecord } from '../../types/api';
import { formatCount } from '../overview/overviewUtils';
import { themeNamesForCommunity, topicKeywordsForCommunity } from './communityEnrichment';

interface CommunityDetailPanelProps {
  communityId: string | null;
  metric: MetricName;
  detail?: CommunityDetail;
  detailPending?: boolean;
  detailError?: unknown;
  themes?: ThemeRecord[];
  themesError?: unknown;
  topics?: TopicRecord[];
  topicsError?: unknown;
  onClose: () => void;
  onViewNetwork?: () => void;
}

export default function CommunityDetailPanel({
  communityId,
  metric,
  detail,
  detailPending,
  detailError,
  themes = [],
  themesError,
  topics = [],
  topicsError,
  onClose,
  onViewNetwork,
}: CommunityDetailPanelProps) {
  if (!communityId) {
    return (
      <aside className="bg-panel border border-border rounded-xl p-6 h-full flex items-center justify-center text-center">
        <div>
          <Network className="mx-auto text-muted" size={28} />
          <h2 className="mt-3 font-semibold text-text-heading">No community selected</h2>
          <p className="mt-2 text-sm text-muted">Select a graph node or table row to inspect canonical community details.</p>
        </div>
      </aside>
    );
  }

  if (detailPending) {
    return (
      <aside className="bg-panel border border-border rounded-xl p-6 h-full" aria-live="polite">
        <div className="h-7 w-40 animate-pulse rounded bg-panel-soft" />
        <div className="mt-6 space-y-3">
          {[1, 2, 3, 4].map((item) => <div key={item} className="h-12 animate-pulse rounded bg-panel-soft" />)}
        </div>
      </aside>
    );
  }

  if (detailError || !detail) {
    const error = normalizeApiError(detailError);
    return (
      <aside className="bg-panel border border-danger/30 rounded-xl p-6 h-full" role="alert">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="font-semibold text-text-heading">Community unavailable</h2>
            <p className="mt-2 text-sm text-muted">{error.message}</p>
            <p className="mt-2 text-xs text-muted">Community ID: {communityId}</p>
          </div>
          <CloseButton onClick={onClose} />
        </div>
      </aside>
    );
  }

  const themeNames = themeNamesForCommunity(themes, metric, communityId);
  const keywords = topicKeywordsForCommunity(topics, metric, communityId);
  const graph = detail.graph;

  return (
    <aside className="bg-panel border border-border rounded-xl p-6 h-full overflow-y-auto">
      <div className="flex items-start justify-between gap-4 border-b border-border pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted">
            <Hash size={13} /> Community ID
          </div>
          <h2 className="mt-2 break-all text-xl font-bold text-text-heading">{communityId}</h2>
          <p className="mt-1 text-xs text-muted">{metric.toUpperCase()} structural partition</p>
        </div>
        <CloseButton onClick={onClose} />
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-4 text-sm">
        <Stat label="Nodes" value={formatCount(detail.community.node_count)} />
        <Stat label="Edges" value={formatCount(detail.community.edge_count)} />
        <Stat label={`${metric.toUpperCase()} total weight`} value={formatCount(detail.community.total_weight)} />
        <Stat label="Returned graph" value={`${formatCount(graph.returned_nodes)} nodes / ${formatCount(graph.returned_edges)} edges`} />
        <Stat label="Available graph" value={`${formatCount(graph.available_nodes)} nodes / ${formatCount(graph.available_edges)} edges`} />
        <Stat label="Sampling" value={graph.sampled ? 'Bounded sample' : 'Complete at requested filter'} />
      </dl>

      <section className="mt-6 border-t border-border pt-5">
        <h3 className="flex items-center gap-2 text-sm font-bold text-text-heading"><Tags size={15} /> Theme enrichment</h3>
        {themesError ? (
          <OptionalUnavailable label="Theme artifact unavailable for this run." />
        ) : themeNames.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {themeNames.map((theme) => (
              <span key={theme} className="rounded-full border border-primary/20 bg-primary/10 px-2.5 py-1 text-xs text-primary">{theme}</span>
            ))}
          </div>
        ) : (
          <OptionalUnavailable label="No unambiguous theme matched this metric and community ID." />
        )}
      </section>

      <section className="mt-6 border-t border-border pt-5">
        <h3 className="text-sm font-bold text-text-heading">LDA keyword enrichment</h3>
        {topicsError ? (
          <OptionalUnavailable label="Topic artifact unavailable for this run." />
        ) : keywords.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {keywords.slice(0, 20).map((keyword) => (
              <span key={keyword} className="rounded border border-border bg-panel-soft px-2 py-1 text-xs text-muted">{keyword}</span>
            ))}
          </div>
        ) : (
          <OptionalUnavailable label="No matched LDA keywords were found for this metric and community ID." />
        )}
      </section>

      {onViewNetwork && (
        <button
          type="button"
          onClick={onViewNetwork}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-primary/10 px-4 py-2.5 text-sm font-semibold text-primary hover:bg-primary/15"
        >
          <Network size={15} /> View in Network
        </button>
      )}
    </aside>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border/70 bg-bg/30 p-3">
      <dt className="text-[11px] text-muted">{label}</dt>
      <dd className="mt-1 break-words font-semibold text-text-heading">{value}</dd>
    </div>
  );
}

function OptionalUnavailable({ label }: { label: string }) {
  return <p className="mt-3 rounded-lg border border-border bg-panel-soft/40 p-3 text-xs text-muted">{label}</p>;
}

function CloseButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      aria-label="Clear selected community"
      onClick={onClick}
      className="rounded-lg p-1.5 text-muted hover:bg-panel-soft hover:text-text-heading"
    >
      <X size={16} />
    </button>
  );
}
