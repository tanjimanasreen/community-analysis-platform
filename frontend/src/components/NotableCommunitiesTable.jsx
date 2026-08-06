import React, { useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight } from 'lucide-react';
import { formatCount } from '../features/overview/overviewUtils';
import { sortCommunityPage } from '../features/communities/communityUtils';
import { pageRange } from '../utils/pagination';

const columns = [
  ['community_id', 'Community ID'],
  ['node_count', 'Nodes'],
  ['edge_count', 'Edges'],
  ['total_weight', 'Total weight'],
];

export default function NotableCommunitiesTable({
  response,
  metric,
  selectedCommunityId,
  onSelectCommunity,
  onPrevious,
  onNext,
}) {
  const [sortKey, setSortKey] = useState('total_weight');
  const [sortDirection, setSortDirection] = useState('desc');
  const rows = useMemo(
    () => sortCommunityPage(response?.communities ?? [], sortKey, sortDirection),
    [response?.communities, sortDirection, sortKey],
  );
  const offset = response?.offset ?? 0;
  const limit = response?.limit ?? rows.length;
  const total = response?.total ?? 0;

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortKey(key);
    setSortDirection(key === 'community_id' ? 'asc' : 'desc');
  };

  return (
    <section className="panel overflow-hidden">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-5 py-4 border-b border-border">
        <div>
          <h2 className="text-sm font-bold text-text-heading">Communities · {metric.toUpperCase()}</h2>
          <p className="mt-1 text-[11px] text-muted">Sorting applies to this loaded page only.</p>
        </div>
        <span className="text-xs text-muted">{pageRange(offset, limit, total)}</span>
      </div>
      {rows.length === 0 ? (
        <div className="p-8 text-center" aria-live="polite">
          <p className="font-semibold text-text-heading">No communities available</p>
          <p className="mt-2 text-sm text-muted">The selected metric returned no community records on this page.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-border bg-surface-soft/40 text-muted">
                {columns.map(([key, label]) => (
                  <th key={key} className="px-5 py-3 font-semibold">
                    <button
                      type="button"
                      onClick={() => handleSort(key)}
                      className="inline-flex items-center gap-1 hover:text-text-heading"
                    >
                      {label}
                      {sortKey === key && (sortDirection === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.community_id}
                  onClick={() => onSelectCommunity(row.community_id)}
                  className={`cursor-pointer border-b border-border/40 transition-colors hover:bg-surface-soft/40 ${selectedCommunityId === row.community_id ? 'bg-primary/10' : ''}`}
                >
                  <td className="px-5 py-3 font-semibold text-text-heading">{row.community_id}</td>
                  <td className="px-5 py-3 text-muted">{formatCount(row.node_count)}</td>
                  <td className="px-5 py-3 text-muted">{formatCount(row.edge_count)}</td>
                  <td className="px-5 py-3 text-muted">{formatCount(row.total_weight)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-border">
        <button
          type="button"
          aria-label="Previous community page"
          disabled={offset <= 0}
           onClick={onPrevious}
           className="rounded-md border border-border p-1.5 text-muted hover:bg-surface-soft disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronLeft size={15} />
        </button>
        <button
          type="button"
          aria-label="Next community page"
          disabled={offset + limit >= total}
           onClick={onNext}
           className="rounded-md border border-border p-1.5 text-muted hover:bg-surface-soft disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronRight size={15} />
        </button>
      </div>
    </section>
  );
}
