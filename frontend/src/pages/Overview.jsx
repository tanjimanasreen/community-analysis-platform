import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import KPICards from '../components/KPICards';
import NetworkGraph from '../components/charts/NetworkGraph';
import EvolutionChart from '../components/charts/EvolutionChart';
import PlatformComparison from '../components/charts/PlatformComparison';
import TransitionsSankey from '../components/charts/TransitionsSankey';
import DataTable from '../components/DataTable';
import RightSidebar from '../components/RightSidebar';
import ErrorState from '../components/states/ErrorState';
import LoadingState from '../components/states/LoadingState';
import TopThemesPanel from '../features/overview/TopThemesPanel';
import { useOverviewData } from '../features/overview/useOverviewData';

const COMMUNITY_PAGE_SIZE = 5;

export default function Overview() {
  const location = useLocation();
  const [communityOffset, setCommunityOffset] = useState(0);
  const [sortKey, setSortKey] = useState('total_weight');
  const [sortDirection, setSortDirection] = useState('desc');
  const data = useOverviewData(communityOffset, COMMUNITY_PAGE_SIZE);

  useEffect(() => {
    setCommunityOffset(0);
  }, [data.selectedRunId, data.metric]);

  if (data.overviewQuery.isPending) {
    return <LoadingState title="Loading overview" message="Reading validated summary artifacts for the selected run." />;
  }
  if (data.overviewQuery.error) {
    return <ErrorState error={data.overviewQuery.error} title="Overview could not be loaded" onRetry={data.retryOverview} />;
  }
  const overview = data.overviewQuery.data;
  if (!overview) return null;

  const handleSort = (nextKey) => {
    if (sortKey === nextKey) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(nextKey);
      setSortDirection(nextKey === 'community_id' ? 'asc' : 'desc');
    }
  };

  return (
    <div data-run-id={data.selectedRunId || undefined} className="max-w-[1600px] mx-auto flex flex-col lg:flex-row gap-8">
      <div className="flex-1 flex flex-col gap-6 w-full overflow-hidden">
        <KPICards overview={overview} metric={data.metric} />

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-3">
            <NetworkGraph
              network={data.networkQuery.data}
              metric={data.metric}
              isLoading={data.networkQuery.isPending}
              error={data.networkQuery.error}
              onRetry={() => void data.networkQuery.refetch()}
            />
          </div>
          <div className="xl:col-span-2">
            <EvolutionChart
              history={data.history}
              metric={data.metric}
              selectedRunDetail={data.selectedRunDetail}
            />
          </div>
          <PlatformComparison
            selectedRun={data.selectedRun}
            selectedRunDetail={data.selectedRunDetail}
            overview={overview}
          />
          <TopThemesPanel overview={overview} />
          <div className="xl:col-span-2">
            <TransitionsSankey
              transitions={data.transitionsQuery.data}
              hasArtifact={data.hasTransitions}
              isLoading={data.artifactsQuery.isPending || (data.hasTransitions && data.transitionsQuery.isPending)}
              error={data.artifactsQuery.error || data.transitionsQuery.error}
              onRetry={() => {
                void data.artifactsQuery.refetch();
                if (data.hasTransitions) void data.transitionsQuery.refetch();
              }}
              search={location.search}
            />
          </div>
        </div>

        {data.communitiesQuery.error ? (
          <ErrorState
            error={data.communitiesQuery.error}
            title="Community table could not be loaded"
            onRetry={() => void data.communitiesQuery.refetch()}
          />
        ) : data.communitiesQuery.isPending ? (
          <LoadingState title="Loading communities" />
        ) : (
          <DataTable
            response={data.communitiesQuery.data}
            themes={data.themesQuery.data?.records ?? []}
            metric={data.metric}
            runId={data.selectedRunId}
            sortKey={sortKey}
            sortDirection={sortDirection}
            onSort={handleSort}
            onPrevious={() => setCommunityOffset((current) => Math.max(0, current - COMMUNITY_PAGE_SIZE))}
            onNext={() => setCommunityOffset((current) => current + COMMUNITY_PAGE_SIZE)}
          />
        )}
      </div>

      <div className="w-full lg:w-80 shrink-0">
        <RightSidebar
          overview={overview}
          network={data.networkQuery.data}
          metric={data.metric}
          selectedRun={data.selectedRun}
          selectedRunDetail={data.selectedRunDetail}
          hasTransitions={data.hasTransitions}
        />
      </div>
    </div>
  );
}
