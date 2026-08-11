import { ChevronLeft, ChevronRight, Search } from 'lucide-react';
import { useEffect, useState, type FormEvent } from 'react';
import type { CommunitiesResponse, MetricName } from '../../types/api';
import { formatCount } from '../overview/overviewUtils';
import { pageRange } from '../../utils/pagination';

interface CommunityDirectoryProps {
  response?: CommunitiesResponse;
  metric: MetricName;
  periodLabel: string;
  selectedCommunityId: string | null;
  onSelectCommunity: (communityId: string) => void;
  onPrevious: () => void;
  onNext: () => void;
  limit: number;
  onLimitChange: (limit: number) => void;
}

export default function CommunityDirectory({
  response,
  metric,
  periodLabel,
  selectedCommunityId,
  onSelectCommunity,
  onPrevious,
  onNext,
  limit,
  onLimitChange,
}: CommunityDirectoryProps) {
  const [communityDraft, setCommunityDraft] = useState(selectedCommunityId ?? '');
  const rows = response?.communities ?? [];
  const offset = response?.offset ?? 0;
  const total = response?.total ?? 0;

  useEffect(() => {
    setCommunityDraft(selectedCommunityId ?? '');
  }, [selectedCommunityId]);

  const submitCommunity = (event: FormEvent) => {
    event.preventDefault();
    const normalized = communityDraft.trim().replace(/^c/i, '');
    if (normalized) onSelectCommunity(normalized);
  };

  return (
    <section className="panel overflow-hidden">
      <div className="flex flex-col gap-4 border-b border-border p-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Monthly community partition</p>
          <h2 className="mt-1 text-lg font-bold text-text-heading">Community Directory</h2>
          <p className="mt-1 text-sm text-muted">
            Browse all published {metric.toUpperCase()} communities for {periodLabel}. Community IDs are local to this month and metric.
          </p>
        </div>

        <form onSubmit={submitCommunity} className="flex w-full max-w-sm items-end gap-2">
          <label className="min-w-0 flex-1 text-xs font-semibold text-muted">
            Exact community ID
            <input
              type="search"
              value={communityDraft}
              onChange={(event) => setCommunityDraft(event.target.value)}
              placeholder="Example: 17"
              className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-heading"
            />
          </label>
          <button
            type="submit"
            className="inline-flex h-[38px] items-center gap-2 rounded-lg border border-border bg-surface-soft px-3 text-sm font-semibold text-primary hover:bg-border/40"
          >
            <Search size={14} aria-hidden="true" /> Go
          </button>
        </form>
      </div>

      {rows.length === 0 ? (
        <div className="p-8 text-center" aria-live="polite">
          <h3 className="font-semibold text-text-heading">No communities available</h3>
          <p className="mt-2 text-sm text-muted">No community summaries were published for this monthly metric partition.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-xs">
            <thead>
              <tr className="border-b border-border bg-surface-soft/30 text-muted">
                <th className="px-4 py-3 font-semibold">Community</th>
                <th className="px-4 py-3 font-semibold">Members</th>
                <th className="px-4 py-3 font-semibold">Internal edges</th>
                <th className="px-4 py-3 font-semibold">{metric.toUpperCase()} internal weight</th>
                <th className="px-4 py-3 font-semibold">Connected communities</th>
                <th className="px-4 py-3 font-semibold">Inbound cross weight</th>
                <th className="px-4 py-3 font-semibold">Outbound cross weight</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((community) => {
                const selected = selectedCommunityId === String(community.community_id);
                return (
                  <tr
                    key={community.community_id}
                    onClick={() => onSelectCommunity(String(community.community_id))}
                    className={`cursor-pointer border-b border-border/40 hover:bg-surface-soft/40 ${selected ? 'bg-primary/10' : ''}`}
                  >
                    <td className="px-4 py-3 font-semibold text-text-heading"><button type="button" aria-current={selected ? 'true' : undefined} onClick={(event) => { event.stopPropagation(); onSelectCommunity(String(community.community_id)); }} className="font-semibold text-primary hover:underline">C{community.community_id}</button></td>
                    <td className="px-4 py-3 text-muted">{formatCount(community.node_count)}</td>
                    <td className="px-4 py-3 text-muted">{formatCount(community.edge_count)}</td>
                    <td className="px-4 py-3 text-muted">{formatMetric(community.total_weight)}</td>
                    <td className="px-4 py-3 text-muted">{optionalCount(community.cross_community_neighbor_count)}</td>
                    <td className="px-4 py-3 text-muted">{optionalMetric(community.inbound_cross_community_weight)}</td>
                    <td className="px-4 py-3 text-muted">{optionalMetric(community.outbound_cross_community_weight)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex flex-col gap-3 border-t border-border px-4 py-3 text-xs text-muted sm:flex-row sm:items-center sm:justify-between">
        <span>{pageRange(offset, limit, total)}</span>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2">
            Rows per page
            <select
              value={limit}
              onChange={(event) => onLimitChange(Number(event.target.value))}
              className="rounded border border-border bg-bg px-2 py-1 text-text-heading"
            >
              <option value="15">15</option>
              <option value="30">30</option>
              <option value="50">50</option>
            </select>
          </label>
          <button type="button" aria-label="Previous community page" disabled={offset <= 0} onClick={onPrevious} className="rounded border border-border p-1.5 disabled:opacity-40"><ChevronLeft size={15} /></button>
          <button type="button" aria-label="Next community page" disabled={offset + limit >= total} onClick={onNext} className="rounded border border-border p-1.5 disabled:opacity-40"><ChevronRight size={15} /></button>
        </div>
      </div>
    </section>
  );
}

function formatMetric(value: number | null | undefined) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return 'Unavailable';
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 4 });
}

function optionalMetric(value: number | null | undefined) {
  return value === null || value === undefined ? 'Unavailable' : formatMetric(value);
}

function optionalCount(value: number | null | undefined) {
  return value === null || value === undefined ? 'Unavailable' : formatCount(value);
}
