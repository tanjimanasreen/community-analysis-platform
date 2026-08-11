import React, { useEffect, useMemo, useState } from 'react';
import {
  ArrowRight,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  GitMerge,
  Network,
  SlidersHorizontal,
  Tags,
  Users,
} from 'lucide-react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { PageNavigationRailSlot } from '../components/PageNavigationRail';
import EmptyState from '../components/states/EmptyState';
import ErrorState from '../components/states/ErrorState';
import LoadingState from '../components/states/LoadingState';
import CommunityDirectory from '../features/communities/CommunityDirectory';
import CommunityMemberGraph from '../features/communities/CommunityMemberGraph';
import { themeNamesForCommunity, topicKeywordsForCommunity } from '../features/communities/communityEnrichment';
import { useCommunitiesWorkspaceData } from '../features/communities/useCommunitiesWorkspaceData';
import {
  parseMinWeight,
  updateNetworkSearchParams,
} from '../features/networks/networkModel';
import { formatCount, formatPeriod } from '../features/overview/overviewUtils';
import { clampPageOffset, nextPageOffset, previousPageOffset } from '../utils/pagination';

const DEFAULT_LIMIT = 15;

export default function CommunitiesPage() {
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const minWeight = parseMinWeight(searchParams.get('minWeight'));
  const [minWeightDraft, setMinWeightDraft] = useState(String(minWeight));
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(DEFAULT_LIMIT);
  const data = useCommunitiesWorkspaceData({ offset, limit, minWeight });

  useEffect(() => {
    setMinWeightDraft(String(minWeight));
  }, [minWeight]);

  useEffect(() => {
    setOffset(0);
  }, [data.selectedRunId, data.metric, data.selectedPeriod]);

  useEffect(() => {
    const response = data.communitiesQuery.data;
    if (!response) return;
    const safeOffset = clampPageOffset(offset, response.total, response.limit);
    if (safeOffset !== offset) setOffset(safeOffset);
  }, [data.communitiesQuery.data, offset]);

  const themes = data.themesQuery.data?.records ?? [];
  const topics = data.topicsQuery.data?.records ?? [];
  const themeNames = data.selectedCommunityId
    ? themeNamesForCommunity(themes, data.metric, data.selectedCommunityId)
    : [];
  const keywords = data.selectedCommunityId
    ? topicKeywordsForCommunity(topics.length > 0 ? topics : themes, data.metric, data.selectedCommunityId)
    : [];
  const neighbors = useMemo(
    () => topNeighbors(data.communityContextQuery.data, data.selectedCommunityId),
    [data.communityContextQuery.data, data.selectedCommunityId],
  );

  const sections = data.selectedCommunityId
    ? [
        { id: 'community-directory', label: 'Directory', icon: 'communities' },
        { id: 'community-summary', label: 'Community Summary', icon: 'kpis' },
        { id: 'community-network', label: 'Member Network', icon: 'network' },
        { id: 'community-themes', label: 'Topics & Themes', icon: 'themes' },
        { id: 'community-provenance', label: 'Provenance', icon: 'provenance' },
      ]
    : [{ id: 'community-directory', label: 'Directory', icon: 'communities' }];

  const applyMinWeight = (event) => {
    event.preventDefault();
    setSearchParams(updateNetworkSearchParams(searchParams, {
      minWeight: parseMinWeight(minWeightDraft),
    }));
  };

  if (data.overviewQuery.isPending) return <LoadingState title="Loading monthly community partitions" />;
  if (data.overviewQuery.error) {
    return <ErrorState error={data.overviewQuery.error} title="Communities could not be loaded" onRetry={() => void data.overviewQuery.refetch()} />;
  }
  if (!data.selectedPeriod) {
    return <EmptyState title="No monthly community snapshots" message="The selected run does not expose a canonical monthly community partition." />;
  }

  const periodLabel = formatPeriod(data.selectedPeriod);
  const periodSummary = data.selectedPeriodSummary;
  const partitionCommunityCount = data.metric === 'if'
    ? periodSummary?.if_community_count
    : periodSummary?.wif_community_count;
  const partitionUsers = data.metric === 'if' ? periodSummary?.if_users : periodSummary?.wif_users;
  const partitionMessages = data.metric === 'if' ? periodSummary?.if_messages : periodSummary?.wif_messages;

  return (
    <div className="mx-auto flex max-w-[1600px] items-start px-1 sm:px-2">
      <div data-run-id={data.selectedRunId || undefined} className="min-w-0 flex-1 space-y-6 pb-16">
        <header className="panel p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Structural analysis · monthly communities</p>
          <div className="mt-2 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-2xl font-bold text-text-heading">Communities</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
                Browse one monthly {data.metric.toUpperCase()} partition, select a community, and inspect its persisted structural and semantic evidence without implying identity across months.
              </p>
            </div>
            <PartitionNavigator
              periods={data.periods}
              selectedPeriod={data.selectedPeriod}
              onChange={data.setSelectedPeriod}
            />
          </div>
        </header>

        <section aria-label="Monthly partition summary" className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <SummaryCard icon={Network} label={`${data.metric.toUpperCase()} communities`} value={optionalCount(partitionCommunityCount)} helper={`${periodLabel} monthly partition`} />
          <SummaryCard icon={Users} label="Users" value={optionalCount(partitionUsers)} helper={`${periodLabel} · ${data.metric.toUpperCase()}`} />
          <SummaryCard icon={GitMerge} label="Messages" value={optionalCount(partitionMessages)} helper={`${periodLabel} · ${data.metric.toUpperCase()}`} />
        </section>

        <section id="community-directory" className="scroll-mt-6" tabIndex={-1}>
          {data.communitiesQuery.isPending ? (
            <LoadingState title="Loading community directory" />
          ) : data.communitiesQuery.error ? (
            <ErrorState error={data.communitiesQuery.error} title="Community directory could not be loaded" onRetry={() => void data.communitiesQuery.refetch()} />
          ) : (
            <CommunityDirectory
              response={data.communitiesQuery.data}
              metric={data.metric}
              periodLabel={periodLabel}
              selectedCommunityId={data.selectedCommunityId}
              onSelectCommunity={data.selectCommunity}
              onPrevious={() => setOffset(previousPageOffset(offset, limit))}
              onNext={() => setOffset(nextPageOffset(offset, data.communitiesQuery.data?.total ?? 0, limit))}
              limit={limit}
              onLimitChange={(nextLimit) => {
                setLimit(nextLimit);
                setOffset(0);
              }}
            />
          )}
        </section>

        {!data.selectedCommunityId ? (
          <EmptyState
            title="Select a community"
            message={`Choose a community from ${periodLabel} · ${data.metric.toUpperCase()} to inspect its structure, member network, and downstream topic/theme evidence.`}
          />
        ) : data.detailQuery.isPending ? (
          <LoadingState title={`Loading community C${data.selectedCommunityId}`} />
        ) : data.detailQuery.error || !data.detailQuery.data ? (
          <ErrorState
            error={data.detailQuery.error}
            title={`Community C${data.selectedCommunityId} is unavailable in ${periodLabel} · ${data.metric.toUpperCase()}`}
            onRetry={() => void data.detailQuery.refetch()}
          />
        ) : (
          <>
            <section id="community-summary" className="panel scroll-mt-6 p-5" tabIndex={-1}>
              <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Selected community</p>
                  <h2 className="mt-1 text-xl font-bold text-text-heading">C{data.selectedCommunityId}</h2>
                  <p className="mt-1 text-sm text-muted">{periodLabel} · {data.metric.toUpperCase()} community. IDs are month-local.</p>
                </div>
                <button type="button" onClick={data.clearCommunity} className="self-start rounded-lg border border-border bg-surface-soft px-3 py-2 text-xs font-semibold text-muted hover:text-text-heading">
                  Clear selection
                </button>
              </div>

              <dl className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
                <Stat label="Members" value={formatCount(data.detailQuery.data.community.node_count)} />
                <Stat label="Internal edges" value={formatCount(data.detailQuery.data.community.edge_count)} />
                <Stat label={`${data.metric.toUpperCase()} internal weight`} value={formatMetric(data.detailQuery.data.community.total_weight)} />
                <Stat label="Connected communities" value={optionalCount(data.detailQuery.data.community.cross_community_neighbor_count)} />
                <Stat label="Inbound cross weight" value={optionalMetric(data.detailQuery.data.community.inbound_cross_community_weight)} />
                <Stat label="Outbound cross weight" value={optionalMetric(data.detailQuery.data.community.outbound_cross_community_weight)} />
              </dl>

              <div className="mt-5 border-t border-border pt-4">
                <h3 className="text-sm font-bold text-text-heading">Strongest neighboring communities</h3>
                {data.communityContextQuery.isPending ? (
                  <p className="mt-3 text-xs text-muted">Loading published cross-community context…</p>
                ) : data.communityContextQuery.error ? (
                  <OptionalUnavailable label="Published cross-community context is unavailable for this monthly partition." />
                ) : !communityRepresented(data.communityContextQuery.data, data.selectedCommunityId) && data.communityContextQuery.data?.sampled ? (
                  <OptionalUnavailable label={`Neighbor drill-down is unavailable because the bounded community-map response did not include C${data.selectedCommunityId}.`} />
                ) : neighbors.length ? (
                  <ol className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                    {neighbors.map((neighbor) => (
                      <li key={neighbor.id} className="flex items-center justify-between gap-3 rounded-lg border border-border/70 bg-bg/30 px-3 py-2 text-xs">
                        <button type="button" onClick={() => data.selectCommunity(neighbor.id)} className="font-semibold text-primary hover:underline">C{neighbor.id}</button>
                        <span className="text-muted">{data.metric.toUpperCase()} {formatMetric(neighbor.weight)} · {formatCount(neighbor.userPairs)} pairs</span>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="mt-3 rounded-lg border border-border bg-surface-soft/40 p-3 text-xs text-muted">No cross-community interaction is published for this community.</p>
                )}
              </div>
            </section>

            <section id="community-network" className="panel scroll-mt-6 p-5" tabIndex={-1}>
              <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Structural drill-down</p>
                  <h2 className="mt-1 text-lg font-bold text-text-heading">Member Interaction Network</h2>
                  <p className="mt-1 text-sm text-muted">Directed creator → spreader interactions inside C{data.selectedCommunityId}. Degree shown in graph tooltips is only within the returned graph.</p>
                </div>
                <form onSubmit={applyMinWeight} className="flex items-end gap-2">
                  <label className="text-xs font-semibold text-muted">
                    Minimum visible edge weight
                    <input type="number" min="0" step="any" value={minWeightDraft} onChange={(event) => setMinWeightDraft(event.target.value)} className="mt-1 w-40 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-heading" />
                  </label>
                  <button type="submit" className="inline-flex h-[38px] items-center gap-2 rounded-lg border border-border bg-surface-soft px-3 text-sm font-semibold text-primary hover:bg-border/40"><SlidersHorizontal size={14} /> Apply</button>
                </form>
              </div>
              <p className="mt-2 text-[11px] text-muted">This filter changes only the returned network visualization. It does not rerun Louvain or change community membership, LDA, or themes.</p>
              <div className="mt-4">
                <CommunityMemberGraph graph={data.detailQuery.data.graph} height={480} />
              </div>
            </section>

            <section id="community-themes" className="panel scroll-mt-6 p-5" tabIndex={-1}>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Semantic preview</p>
                  <h2 className="mt-1 text-lg font-bold text-text-heading">Topics & Themes</h2>
                  <p className="mt-1 text-sm text-muted">LDA evidence is shown first; human-readable theme labels remain downstream of the persisted LDA keywords.</p>
                </div>
                <Link to={thematicHref(location.search, data.metric, data.selectedCommunityId, data.selectedPeriod)} className="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:underline">
                  Explore full thematic evidence <ArrowRight size={14} />
                </Link>
              </div>

              <div className="mt-5 grid gap-5 lg:grid-cols-2">
                <div>
                  <h3 className="flex items-center gap-2 text-sm font-bold text-text-heading"><BookOpen size={15} /> LDA keywords</h3>
                  {data.topicsQuery.isPending ? (
                    <p className="mt-3 text-xs text-muted">Loading matched LDA evidence…</p>
                  ) : data.topicsQuery.error && !keywords.length ? (
                    <OptionalUnavailable label="Matched LDA topic artifact is unavailable for this run, month, and community." />
                  ) : keywords.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">{keywords.slice(0, 30).map((keyword) => <span key={keyword} className="rounded border border-border bg-surface-soft px-2 py-1 text-xs text-muted">{keyword}</span>)}</div>
                  ) : (
                    <OptionalUnavailable label="No unambiguous matched LDA keywords were published for this metric and community ID." />
                  )}
                </div>

                <div>
                  <h3 className="flex items-center gap-2 text-sm font-bold text-text-heading"><Tags size={15} /> Downstream theme labels</h3>
                  {data.themesQuery.isPending ? (
                    <p className="mt-3 text-xs text-muted">Loading generated theme labels…</p>
                  ) : data.themesQuery.error ? (
                    <OptionalUnavailable label="Theme artifact is unavailable for this run, month, and community." />
                  ) : themeNames.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">{themeNames.map((theme) => <span key={theme} className="rounded-full border border-primary/20 bg-primary/10 px-2.5 py-1 text-xs text-primary">{theme}</span>)}</div>
                  ) : (
                    <OptionalUnavailable label="No provider-generated theme was published for this metric and community ID." />
                  )}
                  <p className="mt-3 text-[11px] text-muted">No theme generation occurs in this page.</p>
                </div>
              </div>
            </section>

            <section id="community-provenance" className="panel scroll-mt-6 p-5" tabIndex={-1}>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Coverage & provenance</p>
              <h2 className="mt-1 text-lg font-bold text-text-heading">Returned network coverage</h2>
              <CoverageSummary graph={data.detailQuery.data.graph} />
            </section>
          </>
        )}
      </div>

      <PageNavigationRailSlot sections={sections} />
    </div>
  );
}

function PartitionNavigator({ periods, selectedPeriod, onChange }) {
  const index = periods.indexOf(selectedPeriod);
  const previous = index > 0 ? periods[index - 1] : null;
  const next = index >= 0 && index < periods.length - 1 ? periods[index + 1] : null;

  return (
    <div className="flex flex-wrap items-end gap-2">
      <button type="button" aria-label="Show previous month" disabled={!previous} onClick={() => previous && onChange(previous)} className="rounded-lg border border-border bg-surface-soft p-2 text-muted disabled:opacity-40"><ChevronLeft size={16} /></button>
      <label className="text-xs font-semibold text-muted">
        Monthly partition
        <select value={selectedPeriod} onChange={(event) => onChange(event.target.value)} className="mt-1 min-w-44 rounded-lg border border-border bg-bg px-3 py-2 text-sm font-semibold text-text-heading">
          {periods.map((period) => <option key={period} value={period}>{formatPeriod(period)}</option>)}
        </select>
      </label>
      <button type="button" aria-label="Show next month" disabled={!next} onClick={() => next && onChange(next)} className="rounded-lg border border-border bg-surface-soft p-2 text-muted disabled:opacity-40"><ChevronRight size={16} /></button>
    </div>
  );
}

function SummaryCard({ icon: Icon, label, value, helper }) {
  return (
    <div className="panel p-4">
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon size={19} aria-hidden="true" /></span>
        <div><p className="text-xs text-muted">{label}</p><p className="mt-0.5 text-xl font-bold text-text-heading">{value}</p></div>
      </div>
      <p className="mt-2 text-[11px] text-muted">{helper}</p>
    </div>
  );
}

function Stat({ label, value }) {
  return <div className="rounded-lg border border-border/70 bg-bg/30 p-3"><dt className="text-[11px] text-muted">{label}</dt><dd className="mt-1 break-words font-semibold text-text-heading">{value}</dd></div>;
}

function OptionalUnavailable({ label }) {
  return <p className="mt-3 rounded-lg border border-border bg-surface-soft/40 p-3 text-xs text-muted">{label}</p>;
}

function CoverageSummary({ graph }) {
  const coverage = graph.coverage;
  const sampling = graph.sampling;
  return (
    <dl className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      <Stat label="Available members" value={formatCount(graph.available_nodes)} />
      <Stat label="Returned members" value={formatCount(graph.returned_nodes)} />
      <Stat label="Available internal edges" value={formatCount(graph.available_edges)} />
      <Stat label="Returned internal edges" value={formatCount(graph.returned_edges)} />
      <Stat label="Completeness" value={coverage?.is_complete ? 'Complete' : graph.sampled ? 'Deterministically bounded' : 'Complete at requested filter'} />
      <Stat label="Sampling" value={sampling ? `${sampling.strategy} · ${sampling.deterministic ? 'deterministic' : 'non-deterministic'}` : graph.sampled ? 'Bounded response' : 'No sampling metadata'} />
    </dl>
  );
}


function communityRepresented(network, communityId) {
  if (!network || !communityId) return false;
  return (network.nodes ?? []).some((node) => String(node.id) === String(communityId));
}

function topNeighbors(network, communityId) {
  if (!network || !communityId) return [];
  const totals = new Map();
  for (const edge of network.edges ?? []) {
    const source = String(edge.source);
    const target = String(edge.target);
    if (source !== communityId && target !== communityId) continue;
    const neighbor = source === communityId ? target : source;
    const current = totals.get(neighbor) ?? { weight: 0, userPairs: 0 };
    current.weight += Number(edge.weight) || 0;
    current.userPairs += Number(edge.user_pair_count ?? edge.edge_count) || 0;
    totals.set(neighbor, current);
  }
  return [...totals.entries()]
    .map(([id, values]) => ({ id, ...values }))
    .sort((left, right) => right.weight - left.weight || left.id.localeCompare(right.id))
    .slice(0, 6);
}

function thematicHref(search, metric, communityId, period) {
  const params = new URLSearchParams(search);
  params.set('period', period);
  params.set('metric', metric);
  params.set('semanticMetric', metric);
  params.set('semanticCommunity', communityId);
  return `/thematic?${params.toString()}`;
}

function formatMetric(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return 'Unavailable';
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 4 });
}

function optionalMetric(value) {
  return value === null || value === undefined ? 'Unavailable' : formatMetric(value);
}

function optionalCount(value) {
  return value === null || value === undefined ? 'Unavailable' : formatCount(value);
}
