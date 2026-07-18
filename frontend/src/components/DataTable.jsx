import React from 'react';
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Download, ExternalLink } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  communitiesCsv,
  enrichCommunities,
  formatCount,
  sortCommunities,
} from '../features/overview/overviewUtils';

const columns = [
  ['community_id', 'Community ID'],
  ['node_count', 'Nodes'],
  ['edge_count', 'Edges'],
  ['total_weight', 'Total Weight'],
];

export default function DataTable({
  response,
  themes = [],
  metric,
  runId,
  sortKey,
  sortDirection,
  onSort,
  onPrevious,
  onNext,
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const enriched = enrichCommunities(response?.communities ?? [], themes, metric);
  const rows = sortCommunities(enriched, sortKey, sortDirection);
  const offset = response?.offset ?? 0;
  const limit = response?.limit ?? rows.length;
  const total = response?.total ?? 0;
  const hasPrevious = offset > 0;
  const hasNext = offset + limit < total;

  const viewCommunity = (communityId) => {
    const params = new URLSearchParams(location.search);
    params.set('run', runId);
    params.set('metric', metric);
    params.set('community', communityId);
    navigate(`/network?${params.toString()}`);
  };

  const exportVisible = () => {
    const csv = communitiesCsv(rows, metric);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const date = new Date().toISOString().slice(0, 10);
    link.href = url;
    link.download = `communities_${runId}_${metric}_${date}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="bg-panel border border-border rounded-xl flex flex-col overflow-hidden">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-5 border-b border-border">
        <div>
          <h2 className="text-lg font-bold text-text-heading">Top Communities · {metric.toUpperCase()}</h2>
          <p className="text-xs text-muted mt-1">Canonical structural fields from the selected community partition.</p>
        </div>
        <button
          type="button"
          onClick={exportVisible}
          disabled={rows.length === 0}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-border bg-panel-soft px-3 py-2 text-sm font-medium text-text-heading hover:bg-border/50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Download size={16} />
          Export visible communities
        </button>
      </div>

      {rows.length === 0 ? (
        <div className="p-8 text-center" aria-live="polite">
          <p className="font-semibold text-text-heading">No communities available</p>
          <p className="mt-2 text-sm text-muted">The selected metric returned no community records for this page.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-border bg-panel-soft/50 text-xs text-muted uppercase tracking-wider font-semibold">
                {columns.map(([key, label]) => (
                  <th key={key} className="px-5 py-3 font-medium">
                    <button
                      type="button"
                      onClick={() => onSort(key)}
                      className="inline-flex items-center gap-1 hover:text-text-heading"
                    >
                      {label}
                      {sortKey === key && (sortDirection === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                    </button>
                  </th>
                ))}
                <th className="px-5 py-3 font-medium">Theme</th>
                <th className="px-5 py-3 font-medium"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {rows.map((row) => (
                <tr key={row.community_id} className="border-b border-border/50 hover:bg-panel-soft/30 transition-colors">
                  <td className="px-5 py-3 font-semibold text-text-heading">{row.community_id}</td>
                  <td className="px-5 py-3">{formatCount(row.node_count)}</td>
                  <td className="px-5 py-3">{formatCount(row.edge_count)}</td>
                  <td className="px-5 py-3">{formatCount(row.total_weight)}</td>
                  <td className="px-5 py-3 text-muted">{row.theme || 'Not unambiguously matched'}</td>
                  <td className="px-5 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => viewCommunity(row.community_id)}
                      className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:text-primary/80"
                    >
                      View in Network
                      <ExternalLink size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex items-center justify-between gap-3 px-5 py-3 border-t border-border text-xs text-muted">
        <span>
          {total === 0 ? '0 records' : `${offset + 1}–${Math.min(offset + limit, total)} of ${total}`}
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            aria-label="Previous community page"
            onClick={onPrevious}
            disabled={!hasPrevious}
            className="p-1.5 rounded-md border border-border hover:bg-panel-soft disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronLeft size={15} />
          </button>
          <button
            type="button"
            aria-label="Next community page"
            onClick={onNext}
            disabled={!hasNext}
            className="p-1.5 rounded-md border border-border hover:bg-panel-soft disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronRight size={15} />
          </button>
        </div>
      </div>
    </section>
  );
}
