import { BookOpen, Hash, Network, Tags, Users, X } from 'lucide-react';
import { useMemo, useState, type ComponentType, type ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { normalizeApiError } from '../../api/errors';
import type { CommunityDetail, MetricName, NetworkResponse, ThemeRecord, TopicRecord } from '../../types/api';
import { communityIdsMatch } from '../../utils/communityIds';
import { formatCount, formatPeriod } from '../overview/overviewUtils';
import { themeNamesForCommunity, topicKeywordsForCommunity } from './communityEnrichment';
import CommunityMemberGraph from './CommunityMemberGraph';

type InspectorTab = 'summary' | 'members' | 'themes';

interface ProminentCommunityInspectorProps {
  communityId: string;
  metric: MetricName;
  period: string;
  detail?: CommunityDetail;
  detailPending?: boolean;
  detailError?: unknown;
  communityNetwork?: NetworkResponse;
  topics?: TopicRecord[];
  topicsError?: unknown;
  themes?: ThemeRecord[];
  themesError?: unknown;
  providerMetadata?: Record<string, unknown> | null;
  onClose: () => void;
}

export default function ProminentCommunityInspector({
  communityId,
  metric,
  period,
  detail,
  detailPending,
  detailError,
  communityNetwork,
  topics = [],
  topicsError,
  themes = [],
  themesError,
  providerMetadata = null,
  onClose,
}: ProminentCommunityInspectorProps) {
  const [tab, setTab] = useState<InspectorTab>('summary');
  const location = useLocation();
  const neighbors = useMemo(
    () => topNeighbors(communityNetwork, communityId),
    [communityId, communityNetwork],
  );

  if (detailPending) {
    return (
      <aside className="panel prominent-community-inspector" aria-live="polite">
        <div className="h-7 w-40 animate-pulse rounded bg-surface-soft" />
        <div className="mt-6 space-y-3">{[1, 2, 3, 4].map((item) => <div key={item} className="h-12 animate-pulse rounded bg-surface-soft" />)}</div>
      </aside>
    );
  }

  if (detailError || !detail) {
    const error = normalizeApiError(detailError);
    return (
      <aside className="panel prominent-community-inspector border border-danger/30" role="alert">
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
  const keywords = topicKeywordsForCommunity(
    topics.length > 0 ? topics : themes,
    metric,
    communityId,
  );
  const provider = formatProviderMetadata(providerMetadata);
  const summary = detail.community;

  return (
    <aside className="panel prominent-community-inspector" aria-label={`Community C${communityId} details`}>
      <div className="flex items-start justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted"><Hash size={13} /> Selected community</div>
          <h2 className="mt-2 break-all text-xl font-bold text-text-heading">C{communityId}</h2>
          <p className="mt-1 text-xs text-muted">{formatPeriod(period)} · {metric.toUpperCase()} prominent partition</p>
        </div>
        <CloseButton onClick={onClose} />
      </div>

      <p className="sr-only" aria-live="polite">
        Community C{communityId} has {formatCount(summary.node_count)} members, {optionalCount(summary.cross_community_neighbor_count)} connected prominent communities, and summary, member network, and topics and themes detail sections.
      </p>

      <div className="community-inspector-tabs" role="tablist" aria-label="Community detail sections">
        <TabButton active={tab === 'summary'} onClick={() => setTab('summary')} icon={Hash}>Summary</TabButton>
        <TabButton active={tab === 'members'} onClick={() => setTab('members')} icon={Users}>Members</TabButton>
        <TabButton active={tab === 'themes'} onClick={() => setTab('themes')} icon={Tags}>Topics & themes</TabButton>
      </div>

      {tab === 'summary' && (
        <div role="tabpanel" className="mt-5">
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <Stat label="Members" value={formatCount(summary.node_count)} />
            <Stat label="Internal edges" value={formatCount(summary.edge_count)} />
            <Stat label={`${metric.toUpperCase()} internal weight`} value={formatMetric(summary.total_weight)} />
            <Stat label="Connected communities" value={optionalCount(summary.cross_community_neighbor_count)} />
            <Stat label="Inbound cross weight" value={optionalMetric(summary.inbound_cross_community_weight)} />
            <Stat label="Outbound cross weight" value={optionalMetric(summary.outbound_cross_community_weight)} />
          </dl>

          <section className="mt-5 border-t border-border pt-4">
            <h3 className="text-sm font-bold text-text-heading">Strongest neighboring communities</h3>
            {neighbors.length ? (
              <ol className="mt-3 space-y-2">
                {neighbors.map((neighbor) => (
                  <li key={neighbor.id} className="flex items-center justify-between gap-3 rounded-lg border border-border/70 bg-bg/30 px-3 py-2 text-xs">
                    <span className="font-semibold text-text-heading">C{neighbor.id}</span>
                    <span className="text-muted">{metric.toUpperCase()} {formatMetric(neighbor.weight)} · {formatCount(neighbor.userPairs)} pairs</span>
                  </li>
                ))}
              </ol>
            ) : (
              <OptionalUnavailable label="No cross-community interaction is published for this community." />
            )}
          </section>

          <section className="mt-5 border-t border-border pt-4">
            <h3 className="text-sm font-bold text-text-heading">Available downstream detail</h3>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <span className={`rounded-full border px-2.5 py-1 ${keywords.length ? 'border-primary/20 bg-primary/10 text-primary' : 'border-border text-muted'}`}>LDA {keywords.length ? 'available' : 'unavailable'}</span>
              <span className={`rounded-full border px-2.5 py-1 ${themeNames.length ? 'border-primary/20 bg-primary/10 text-primary' : 'border-border text-muted'}`}>Themes {themeNames.length ? 'available' : 'unavailable'}</span>
            </div>
          </section>
        </div>
      )}

      {tab === 'members' && (
        <div role="tabpanel" className="mt-5">
          <CommunityMemberGraph graph={detail.graph} />
        </div>
      )}

      {tab === 'themes' && (
        <div role="tabpanel" className="mt-5">
          <section>
            <h3 className="text-sm font-bold text-text-heading">LDA keywords</h3>
            {topicsError && !keywords.length ? (
              <OptionalUnavailable label="Matched topic artifact unavailable for this run and community." />
            ) : keywords.length ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {keywords.slice(0, 24).map((keyword) => <span key={keyword} className="rounded border border-border bg-surface-soft px-2 py-1 text-xs text-muted">{keyword}</span>)}
              </div>
            ) : (
              <OptionalUnavailable label="No unambiguous matched LDA keywords were found for this metric and community ID." />
            )}
          </section>

          <section className="mt-5 border-t border-border pt-4">
            <h3 className="flex items-center gap-2 text-sm font-bold text-text-heading"><Tags size={15} /> Downstream theme labels</h3>
            {themesError ? (
              <OptionalUnavailable label="Theme artifact unavailable for this run." />
            ) : themeNames.length ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {themeNames.map((theme) => <span key={theme} className="rounded-full border border-primary/20 bg-primary/10 px-2.5 py-1 text-xs text-primary">{theme}</span>)}
              </div>
            ) : (
              <OptionalUnavailable label="No provider-generated theme is published for this metric and community ID." />
            )}
            <p className="mt-3 text-[11px] text-muted">Theme labels are displayed only when published downstream of the community's LDA keywords. No theme is generated in this inspector.</p>
            {provider && <p className="mt-2 text-[11px] text-muted">Provider/model: {provider}</p>}
          </section>
        </div>
      )}

      <Link to={communitiesHref(location.search, communityId, period)} className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-primary/10 px-4 py-2.5 text-sm font-semibold text-primary hover:bg-primary/15">
        <Network size={15} /> Explore in Communities
      </Link>
      <Link to={thematicHref(location.search, metric, communityId, period)} className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-border bg-surface-soft/40 px-4 py-2.5 text-sm font-semibold text-primary hover:bg-surface-soft">
        <BookOpen size={15} /> Open thematic analysis
      </Link>
    </aside>
  );
}

function topNeighbors(network: NetworkResponse | undefined, communityId: string) {
  if (!network) return [];
  const totals = new Map<string, { weight: number; userPairs: number }>();
  for (const edge of network.edges) {
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
    .slice(0, 5);
}

function formatProviderMetadata(metadata: Record<string, unknown> | null): string | null {
  if (!metadata) return null;
  const provider = firstMetadataValue(metadata, [
    'configured_primary_provider',
    'provider',
    'theme_provider',
  ]);
  const model = firstMetadataValue(metadata, [
    'configured_primary_model',
    'model',
    'theme_model',
  ]);
  return [provider, model].filter(Boolean).join(' · ') || null;
}

function firstMetadataValue(
  metadata: Record<string, unknown>,
  keys: string[],
): string | null {
  for (const key of keys) {
    const value = metadata[key];
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  return null;
}

function TabButton({
  active,
  onClick,
  icon: Icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: ComponentType<{ size?: number }>;
  children: ReactNode;
}) {
  return <button type="button" role="tab" aria-selected={active} onClick={onClick} className={active ? 'is-active' : ''}><Icon size={13} />{children}</button>;
}

function Stat({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-border/70 bg-bg/30 p-3"><dt className="text-[11px] text-muted">{label}</dt><dd className="mt-1 break-words font-semibold text-text-heading">{value}</dd></div>;
}

function OptionalUnavailable({ label }: { label: string }) {
  return <p className="mt-3 rounded-lg border border-border bg-surface-soft/40 p-3 text-xs text-muted">{label}</p>;
}

function CloseButton({ onClick }: { onClick: () => void }) {
  return <button type="button" aria-label="Clear selected community" onClick={onClick} className="rounded-lg p-1.5 text-muted hover:bg-surface-soft hover:text-text-heading"><X size={16} /></button>;
}

function communitiesHref(search: string, communityId: string, period: string) {
  const params = new URLSearchParams(search);
  params.delete('networkView');
  params.delete('sampling');
  params.set('community', communityId);
  params.set('period', period);
  return `/communities?${params.toString()}`;
}

function thematicHref(search: string, metric: MetricName, communityId: string, period: string) {
  const params = new URLSearchParams(search);
  params.set('metric', metric);
  params.set('semanticMetric', metric);
  params.set('semanticCommunity', communityId);
  params.set('period', period);
  return `/thematic?${params.toString()}`;
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
