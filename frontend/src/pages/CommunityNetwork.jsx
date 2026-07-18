import React, { useEffect, useMemo, useState } from 'react';
import { GitCommit, Network, Share2, SlidersHorizontal, Users } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import NetworkGraph from '../components/charts/NetworkGraph';
import NotableCommunitiesTable from '../components/NotableCommunitiesTable';
import ErrorState from '../components/states/ErrorState';
import LoadingState from '../components/states/LoadingState';
import CommunityDetailPanel from '../features/communities/CommunityDetailPanel';
import CentralityTable from '../features/networks/CentralityTable';
import {
  averageDegreeInReturnedGraph,
  parseMinWeight,
  transformNetworkResponse,
  updateNetworkSearchParams,
} from '../features/networks/networkModel';
import { useNetworkPageData } from '../features/networks/useNetworkPageData';
import { formatCount } from '../features/overview/overviewUtils';
import { clampPageOffset, nextPageOffset, previousPageOffset } from '../utils/pagination';

const COMMUNITY_LIMIT = 10;
const CENTRALITY_LIMIT = 10;

export default function CommunityNetworkPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedCommunityId = searchParams.get('community');
  const minWeight = parseMinWeight(searchParams.get('minWeight'));
  const [minWeightDraft, setMinWeightDraft] = useState(String(minWeight));
  const [communityOffset, setCommunityOffset] = useState(0);
  const [centralityOffset, setCentralityOffset] = useState(0);
  const [selectedNode, setSelectedNode] = useState(null);

  const data = useNetworkPageData({
    communityId: selectedCommunityId,
    minWeight,
    communityOffset,
    communityLimit: COMMUNITY_LIMIT,
    centralityOffset,
    centralityLimit: CENTRALITY_LIMIT,
  });
  const {
    selectedRunId,
    metric,
    networkQuery,
    communitiesQuery,
    centralityQuery,
    detailQuery,
    topicsQuery,
    themesQuery,
  } = data;

  useEffect(() => {
    setMinWeightDraft(String(minWeight));
  }, [minWeight]);

  useEffect(() => {
    const response = communitiesQuery.data;
    if (!response) return;
    const safeOffset = clampPageOffset(communityOffset, response.total, response.limit);
    if (safeOffset !== communityOffset) setCommunityOffset(safeOffset);
  }, [communitiesQuery.data, communityOffset]);

  useEffect(() => {
    const response = centralityQuery.data;
    if (!response) return;
    const safeOffset = clampPageOffset(centralityOffset, response.total, response.limit);
    if (safeOffset !== centralityOffset) setCentralityOffset(safeOffset);
  }, [centralityOffset, centralityQuery.data]);

  const graphData = useMemo(
    () => transformNetworkResponse(networkQuery.data, selectedCommunityId),
    [networkQuery.data, selectedCommunityId],
  );
  const averageDegree = averageDegreeInReturnedGraph(graphData);

  const selectCommunity = (communityId) => {
    setSelectedNode(null);
    setSearchParams(updateNetworkSearchParams(searchParams, { communityId }));
  };
  const clearCommunity = () => {
    setSearchParams(updateNetworkSearchParams(searchParams, { communityId: null }));
  };
  const applyMinWeight = (event) => {
    event.preventDefault();
    setSearchParams(updateNetworkSearchParams(searchParams, {
      minWeight: parseMinWeight(minWeightDraft),
    }));
  };

  return (
    <div data-run-id={selectedRunId || undefined} className="flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
      <div className="flex flex-col gap-4 rounded-xl border border-border bg-panel p-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-xl font-bold text-text-heading">Community Network</h1>
          <p className="mt-1 text-sm text-muted">Bounded, run-scoped interaction graph using the selected {metric.toUpperCase()} metric.</p>
        </div>
        <form onSubmit={applyMinWeight} className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <label className="text-xs font-semibold text-text-heading">
            Minimum edge weight
            <input
              type="number"
              min="0"
              step="any"
              value={minWeightDraft}
              onChange={(event) => setMinWeightDraft(event.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-heading sm:w-44"
            />
          </label>
          <button
            type="submit"
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90"
          >
            <SlidersHorizontal size={15} /> Apply
          </button>
        </form>
      </div>

      {networkQuery.isPending || communitiesQuery.isPending ? (
        <LoadingState title="Loading structural network data" />
      ) : communitiesQuery.error ? (
        <ErrorState
          error={communitiesQuery.error}
          title="Communities could not be loaded"
          onRetry={() => void communitiesQuery.refetch()}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
          <MetricSummary icon={Network} label="Available nodes" value={formatCount(networkQuery.data?.available_nodes ?? 0)} help="Nodes after the current minimum-weight filter, before graph caps." />
          <MetricSummary icon={Share2} label="Available edges" value={formatCount(networkQuery.data?.available_edges ?? 0)} help="Edges after the current minimum-weight filter, before graph caps." />
          <MetricSummary icon={Users} label={`${metric.toUpperCase()} communities`} value={formatCount(communitiesQuery.data?.total ?? 0)} help="Community count from the selected metric partition." />
          <MetricSummary
            icon={Share2}
            label="Returned graph"
            value={`${formatCount(networkQuery.data?.returned_nodes ?? 0)} / ${formatCount(networkQuery.data?.returned_edges ?? 0)}`}
            help="Returned nodes / returned edges after bounded API limits."
          />
          <MetricSummary
            icon={GitCommit}
            label="Average degree in returned graph"
            value={averageDegree === null ? 'Unavailable' : formatCount(averageDegree)}
            help={`${formatCount(networkQuery.data?.returned_nodes ?? 0)} returned nodes / ${formatCount(networkQuery.data?.returned_edges ?? 0)} returned edges.`}
          />
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 min-h-[650px]">
        <div className="xl:col-span-2 min-h-[520px]">
          <NetworkGraph
            network={networkQuery.data}
            metric={metric}
            selectedCommunityId={selectedCommunityId}
            isLoading={networkQuery.isPending}
            error={networkQuery.error}
            onRetry={() => void networkQuery.refetch()}
            onSelectCommunity={selectCommunity}
            onSelectNode={setSelectedNode}
            onClearSelection={clearCommunity}
            height={500}
          />
        </div>
        <div className="min-h-[520px]">
          {selectedNode && !selectedCommunityId && selectedNode.communityIds.length === 0 ? (
            <NodeDetail node={selectedNode} onClose={() => setSelectedNode(null)} />
          ) : (
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
            />
          )}
        </div>
      </div>

      {communitiesQuery.isPending ? (
        <LoadingState title="Loading communities" />
      ) : communitiesQuery.error ? (
        <ErrorState error={communitiesQuery.error} title="Community table could not be loaded" onRetry={() => void communitiesQuery.refetch()} />
      ) : (
        <NotableCommunitiesTable
          response={communitiesQuery.data}
          metric={metric}
          selectedCommunityId={selectedCommunityId}
          onSelectCommunity={selectCommunity}
          onPrevious={() => setCommunityOffset(previousPageOffset(communityOffset, COMMUNITY_LIMIT))}
          onNext={() => setCommunityOffset(nextPageOffset(communityOffset, communitiesQuery.data?.total ?? 0, COMMUNITY_LIMIT))}
        />
      )}

      {centralityQuery.isPending ? (
        <LoadingState title="Loading centrality artifact" />
      ) : centralityQuery.error ? (
        <ErrorState error={centralityQuery.error} title="Centrality data could not be loaded" onRetry={() => void centralityQuery.refetch()} />
      ) : (
        <CentralityTable
          response={centralityQuery.data}
          onPrevious={() => setCentralityOffset(previousPageOffset(centralityOffset, CENTRALITY_LIMIT))}
          onNext={() => setCentralityOffset(nextPageOffset(centralityOffset, centralityQuery.data?.total ?? 0, CENTRALITY_LIMIT))}
        />
      )}
    </div>
  );
}

function MetricSummary({ icon: Icon, label, value, help }) {
  return (
    <section className="bg-panel border border-border rounded-xl p-4">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon size={20} /></div>
        <div>
          <p className="text-sm font-medium text-muted">{label}</p>
          <p className="text-2xl font-bold text-text-heading">{value}</p>
        </div>
      </div>
      <p className="mt-2 text-xs text-muted">{help}</p>
    </section>
  );
}

function NodeDetail({ node, onClose }) {
  return (
    <aside className="h-full rounded-xl border border-border bg-panel p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">Selected node</p>
          <h2 className="mt-2 break-all text-xl font-bold text-text-heading">{node.id}</h2>
        </div>
        <button type="button" onClick={onClose} className="rounded border border-border px-2 py-1 text-xs text-muted hover:bg-panel-soft">Clear</button>
      </div>
      <dl className="mt-6 grid grid-cols-2 gap-4 text-sm">
        <div><dt className="text-xs text-muted">In-degree within returned graph</dt><dd className="mt-1 font-semibold text-text-heading">{node.inDegree}</dd></div>
        <div><dt className="text-xs text-muted">Out-degree within returned graph</dt><dd className="mt-1 font-semibold text-text-heading">{node.outDegree}</dd></div>
      </dl>
      <p className="mt-6 rounded-lg border border-border bg-panel-soft/40 p-3 text-sm text-muted">This node has no community ID in the returned bounded graph, so no community was inferred.</p>
    </aside>
  );
}
