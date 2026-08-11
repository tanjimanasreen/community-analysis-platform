import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import KPICards from '../components/KPICards';
import NetworkGraph from '../components/charts/NetworkGraph';
import CommunityContinuityTimeline from '../components/charts/CommunityContinuityTimeline';
import DataTable from '../components/DataTable';
import EmptyState from '../components/states/EmptyState';
import ErrorState from '../components/states/ErrorState';
import LoadingState from '../components/states/LoadingState';
import CentralActorsSection from '../features/overview/CentralActorsSection';
import MonthlyTrends from '../features/overview/MonthlyTrends';
import PeriodNavigator from '../features/overview/PeriodNavigator';
import RunConfigurationPanel from '../features/overview/RunConfigurationPanel';
import RunProvenancePanel from '../features/overview/RunProvenancePanel';
import TopThemesPanel from '../features/overview/TopThemesPanel';
import ProminentCommunityInspector from '../features/communities/ProminentCommunityInspector';
import { PageNavigationRailSlot } from '../components/PageNavigationRail';
import { formatPeriod } from '../features/overview/overviewUtils';
import { useOverviewData } from '../features/overview/useOverviewData';

const COMMUNITY_PAGE_SIZE = 5;

export default function Overview() {
  const location = useLocation();
  const [communityOffset, setCommunityOffset] = useState(0);
  const [sortKey, setSortKey] = useState('total_weight');
  const [sortDirection, setSortDirection] = useState('desc');
  const [isPlaying, setIsPlaying] = useState(false);
  const [highlightNodeId, setHighlightNodeId] = useState(null);
  const data = useOverviewData(communityOffset, COMMUNITY_PAGE_SIZE);

  useEffect(() => {
    setCommunityOffset(0);
    setHighlightNodeId(null);
  }, [data.selectedRunId, data.metric, data.selectedPeriod, data.networkView]);

  if (data.overviewQuery.error) {
    return <ErrorState error={data.overviewQuery.error} title="Overview could not be loaded" onRetry={data.retryOverview} />;
  }
  const overview = data.overviewQuery.data;
  const isOverviewLoading = data.overviewQuery.isPending;

  if (!overview && !isOverviewLoading) return null;

  const handleSort = (nextKey) => {
    if (sortKey === nextKey) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(nextKey);
      setSortDirection(nextKey === 'community_id' ? 'asc' : 'desc');
    }
  };

  const overviewSections = [
    { id: 'kpis', label: 'Key Metrics', icon: 'kpis' },
    { id: 'trends', label: 'Monthly Trends', icon: 'trends' },
    { id: 'network', label: 'Community Network', icon: 'network' },
    { id: 'actors', label: 'Central Actors', icon: 'actors' },
    { id: 'themes', label: 'Top Themes', icon: 'themes' },
    { id: 'continuity', label: 'Continuity Timeline', icon: 'continuity' },
    { id: 'communities', label: 'Communities List', icon: 'communities' },
    { id: 'metadata', label: 'Run Metadata', icon: 'metadata' }
  ];

  return (
    <div className="flex max-w-[1600px] mx-auto items-start relative px-4 sm:px-6">
      <div data-run-id={data.selectedRunId || undefined} className="overview-page flex-1 min-w-0 pb-16">

      {overview && (
        <PeriodNavigator
          periods={overview.available_periods}
          selectedPeriod={data.selectedPeriod}
          onChange={data.setSelectedPeriod}
          isPlaying={isPlaying}
          onPlayingChange={setIsPlaying}
        />
      )}

      <div id="kpis" className="flex flex-col gap-5">
        <KPICards
          overview={overview ?? {}}
          metric={data.metric}
          selectedPeriod={data.selectedPeriod}
          isLoading={isOverviewLoading}
        />
      </div>

      {overview && (
        <div id="trends">
          <MonthlyTrends
            periods={overview.periods}
            selectedPeriod={data.selectedPeriod}
            metric={data.metric}
            onSelectPeriod={data.setSelectedPeriod}
          />
        </div>
      )}

      {data.selectedPeriod ? (
        <>
          <div id="network" className={`overview-community-network-layout ${data.selectedCommunityId ? 'has-inspector' : ''}`}>
            <NetworkGraph
              network={data.networkQuery.data}
              metric={data.metric}
              periodLabel={formatPeriod(data.selectedPeriod)}
              selectedCommunityId={data.selectedCommunityId}
              highlightNodeId={highlightNodeId}
              isLoading={data.networkQuery.isPending}
              error={data.networkQuery.error}
              onRetry={() => void data.networkQuery.refetch()}
              onInteraction={() => setIsPlaying(false)}
              onSelectCommunity={data.inspectCommunity}
              onClearSelection={data.clearCommunity}
              height={560}
            />
            {data.selectedCommunityId && (
              <ProminentCommunityInspector
                communityId={data.selectedCommunityId}
                metric={data.metric}
                period={data.selectedPeriod}
                detail={data.communityDetailQuery.data}
                detailPending={data.communityDetailQuery.isPending}
                detailError={data.communityDetailQuery.error}
                communityNetwork={data.networkQuery.data}
                topics={data.communityTopicsQuery.data?.records ?? []}
                topicsError={data.communityTopicsQuery.error}
                themes={data.themesQuery.data?.records ?? []}
                themesError={data.themesQuery.error}
                providerMetadata={data.themesQuery.data?.provider_metadata ?? null}
                onClose={data.clearCommunity}
              />
            )}
          </div>
          <div id="actors">
            <CentralActorsSection
              leaders={data.centralityLeadersQuery.data}
              selectedPeriod={data.selectedPeriod}
              metric={data.metric}
              network={data.networkQuery.data}
              isLoading={data.centralityLeadersQuery.isPending}
              error={data.centralityLeadersQuery.error}
              onRetry={() => void data.centralityLeadersQuery.refetch()}
              onSelectPeriod={data.setSelectedPeriod}
              onInspectCommunity={data.inspectCommunity}
              onHighlightUser={(userId) => {
                setHighlightNodeId(userId);
                data.clearCommunity();
              }}
            />
          </div>
        </>
      ) : (
        <EmptyState
          title="No monthly network snapshots"
          message="The selected run does not expose a canonical monthly period for the Overview graph."
        />
      )}

      <div id="themes">
        <TopThemesPanel
          period={data.selectedPeriod}
          themes={data.themeClustersQuery.data}
          hasArtifact={data.hasThemeClusters}
          isLoading={data.artifactsQuery.isPending || (data.hasThemeClusters && data.themeClustersQuery.isPending)}
          error={data.artifactsQuery.error || data.themeClustersQuery.error}
          onRetry={() => {
            void data.artifactsQuery.refetch();
            if (data.hasThemeClusters) void data.themeClustersQuery.refetch();
          }}
          search={location.search}
        />
      </div>

      <div id="continuity">
        <CommunityContinuityTimeline
          transitions={data.transitionsQuery.data}
          hasArtifact={data.hasTransitions}
          isLoading={data.artifactsQuery.isPending || (data.hasTransitions && data.transitionsQuery.isPending)}
          error={data.artifactsQuery.error || data.transitionsQuery.error}
          onRetry={() => {
            void data.artifactsQuery.refetch();
            if (data.hasTransitions) void data.transitionsQuery.refetch();
          }}
          onInteraction={() => setIsPlaying(false)}
          search={location.search}
          maxPaths={10}
        />
      </div>

      {!data.selectedPeriod ? (
        <EmptyState
          title="No monthly community summaries"
          message="The selected run does not expose a canonical monthly period for the Overview community table."
        />
      ) : data.communitiesQuery.error ? (
        <ErrorState
          error={data.communitiesQuery.error}
          title="Community table could not be loaded"
          onRetry={() => void data.communitiesQuery.refetch()}
        />
      ) : data.communitiesQuery.isPending ? (
        <LoadingState title="Loading communities" />
      ) : (
        <div id="communities">
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
        </div>
      )}

      {overview && (
        <div id="metadata" className="overview-metadata-grid">
          <RunConfigurationPanel overview={overview} metric={data.metric} selectedRun={data.selectedRun} />
          <RunProvenancePanel
            overview={overview}
            selectedRun={data.selectedRun}
            selectedRunDetail={data.selectedRunDetail}
            verification={data.verification}
          />
        </div>
      )}
      </div>

      <PageNavigationRailSlot sections={overviewSections} className="sm:block sm:ml-6" />
    </div>
  );
}
