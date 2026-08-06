import React, { useEffect, useMemo, useState } from 'react';
import { ArrowDown, ArrowRight, ArrowUp, ChevronLeft, ChevronRight, Network, Share2, Users, Weight } from 'lucide-react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import CommunityDetailPanel from '../features/communities/CommunityDetailPanel';
import { sortCommunityPage } from '../features/communities/communityUtils';
import { useCommunitiesPageData } from '../features/communities/useCommunitiesPageData';
import ErrorState from '../components/states/ErrorState';
import LoadingState from '../components/states/LoadingState';
import { formatCount } from '../features/overview/overviewUtils';
import { updateNetworkSearchParams } from '../features/networks/networkModel';
import { clampPageOffset, nextPageOffset, pageRange, previousPageOffset } from '../utils/pagination';

const DEFAULT_LIMIT = 15;
const columns = [
  ['community_id', 'Community ID'],
  ['node_count', 'Nodes'],
  ['edge_count', 'Edges'],
  ['total_weight', 'Total weight'],
];

export default function TopCommunitiesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const selectedCommunityId = searchParams.get('community');
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(DEFAULT_LIMIT);
  const [sortKey, setSortKey] = useState('total_weight');
  const [sortDirection, setSortDirection] = useState('desc');
  const data = useCommunitiesPageData({ offset, limit, selectedCommunityId });
  const { selectedRunId, metric, communitiesQuery, detailQuery, topicsQuery, themesQuery } = data;

  useEffect(() => {
    const response = communitiesQuery.data;
    if (!response) return;
    const safeOffset = clampPageOffset(offset, response.total, response.limit);
    if (safeOffset !== offset) setOffset(safeOffset);
  }, [communitiesQuery.data, offset]);

  const rows = useMemo(
    () => sortCommunityPage(communitiesQuery.data?.communities ?? [], sortKey, sortDirection),
    [communitiesQuery.data?.communities, sortDirection, sortKey],
  );
  const pageNodeCount = rows.reduce((sum, row) => sum + row.node_count, 0);
  const pageEdgeCount = rows.reduce((sum, row) => sum + row.edge_count, 0);
  const pageMaxWeight = rows.reduce((max, row) => Math.max(max, row.total_weight), 0);

  const selectCommunity = (communityId) => {
    const next = new URLSearchParams(searchParams);
    next.set('community', communityId);
    setSearchParams(next);
  };
  const clearCommunity = () => {
    const next = new URLSearchParams(searchParams);
    next.delete('community');
    setSearchParams(next);
  };
  const viewNetwork = () => {
    if (!selectedCommunityId) return;
    const next = updateNetworkSearchParams(new URLSearchParams(location.search), {
      communityId: selectedCommunityId,
    });
    navigate(`/network?${next.toString()}`);
  };
  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortKey(key);
    setSortDirection(key === 'community_id' ? 'asc' : 'desc');
  };

  if (communitiesQuery.isPending) return <LoadingState title="Loading top communities" />;
  if (communitiesQuery.error) {
    return <ErrorState error={communitiesQuery.error} title="Top communities could not be loaded" onRetry={() => void communitiesQuery.refetch()} />;
  }

  const response = communitiesQuery.data;
  const total = response?.total ?? 0;

  return (
    <div data-run-id={selectedRunId || undefined} className="flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
      <div>
        <h1 className="text-xl font-bold text-text-heading">Top Communities</h1>
        <p className="mt-1 text-sm text-muted">Canonical {metric.toUpperCase()} community rankings. Sorting applies to the loaded page only.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <SummaryCard icon={Users} label={`${metric.toUpperCase()} communities`} value={formatCount(total)} helper="Total server-side community count" />
        <SummaryCard icon={Network} label="Nodes on loaded page" value={formatCount(pageNodeCount)} helper="Sum of community node counts on this page" />
        <SummaryCard icon={Share2} label="Edges on loaded page" value={formatCount(pageEdgeCount)} helper="Sum of community edge counts on this page" />
        <SummaryCard icon={Weight} label="Highest weight on loaded page" value={formatCount(pageMaxWeight)} helper={`${metric.toUpperCase()} total weight; page-local maximum`} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
         <section className="xl:col-span-3 bg-surface border border-border rounded-xl overflow-hidden shadow-sm">
          {rows.length === 0 ? (
            <div className="p-10 text-center" aria-live="polite">
              <h2 className="font-semibold text-text-heading">No communities available</h2>
              <p className="mt-2 text-sm text-muted">The selected metric returned no records for this page.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs whitespace-nowrap">
                <thead>
                   <tr className="border-b border-border bg-surface-soft/30 text-muted">
                    <th className="px-4 py-4 font-semibold">Page rank</th>
                    {columns.map(([key, label]) => (
                      <th key={key} className="px-4 py-4 font-semibold">
                        <button type="button" onClick={() => handleSort(key)} className="inline-flex items-center gap-1 hover:text-text-heading">
                          {label}
                          {sortKey === key && (sortDirection === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                        </button>
                      </th>
                    ))}
                    <th className="px-4 py-4"><span className="sr-only">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((community, index) => (
                    <tr
                      key={community.community_id}
                      onClick={() => selectCommunity(community.community_id)}
                       className={`cursor-pointer border-b border-border/40 hover:bg-surface-soft/40 ${selectedCommunityId === community.community_id ? 'bg-primary/10' : ''}`}
                    >
                      <td className="px-4 py-3 text-muted">{offset + index + 1}</td>
                      <td className="px-4 py-3 font-semibold text-text-heading">{community.community_id}</td>
                      <td className="px-4 py-3 text-muted">{formatCount(community.node_count)}</td>
                      <td className="px-4 py-3 text-muted">{formatCount(community.edge_count)}</td>
                      <td className="px-4 py-3 text-muted">{formatCount(community.total_weight)}</td>
                      <td className="px-4 py-3 text-right">
                        <button
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            selectCommunity(community.community_id);
                            const next = updateNetworkSearchParams(new URLSearchParams(location.search), { communityId: community.community_id });
                            navigate(`/network?${next.toString()}`);
                          }}
                          className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:text-primary/80"
                        >
                          View Network <ArrowRight size={13} />
                        </button>
                      </td>
                    </tr>
                  ))}
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
                  onChange={(event) => {
                    setLimit(Number(event.target.value));
                    setOffset(0);
                  }}
                  className="rounded border border-border bg-bg px-2 py-1 text-text-heading"
                >
                  <option value="15">15</option>
                  <option value="30">30</option>
                  <option value="50">50</option>
                </select>
              </label>
              <button type="button" aria-label="Previous community page" disabled={offset <= 0} onClick={() => setOffset(previousPageOffset(offset, limit))} className="rounded border border-border p-1.5 disabled:opacity-40"><ChevronLeft size={15} /></button>
              <button type="button" aria-label="Next community page" disabled={offset + limit >= total} onClick={() => setOffset(nextPageOffset(offset, total, limit))} className="rounded border border-border p-1.5 disabled:opacity-40"><ChevronRight size={15} /></button>
            </div>
          </div>
        </section>

        <div className="xl:col-span-1 min-h-[520px]">
          <CommunityDetailPanel
            communityId={selectedCommunityId}
            metric={metric}
            detail={detailQuery.data}
            detailPending={detailQuery.isPending}
            detailError={detailQuery.error}
            themes={themesQuery.data?.records}
            themesError={themesQuery.error}
            topics={topicsQuery.data?.records}
            topicsError={topicsQuery.error}
            onClose={clearCommunity}
            onViewNetwork={viewNetwork}
          />
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ icon: Icon, label, value, helper }) {
  return (
     <section className="rounded-xl border border-border bg-surface p-4 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon size={20} /></div>
        <div><p className="text-sm text-muted">{label}</p><p className="text-2xl font-bold text-text-heading">{value}</p></div>
      </div>
      <p className="mt-2 text-xs text-muted">{helper}</p>
    </section>
  );
}
