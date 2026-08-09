import React, { useEffect, useMemo, useState } from 'react';
import {
  CalendarRange,
  ChevronLeft,
  ChevronRight,
  Database,
  GitCompareArrows,
  Network,
  Tags,
} from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import ArtifactValue from '../components/ArtifactValue';
import MetricCard from '../components/MetricCard';
import KeywordList from '../components/KeywordList';
import ProviderMetadata from '../components/ProviderMetadata';
import PageNavigationRail from '../components/PageNavigationRail';
import ThemeLabel from '../components/ThemeLabel';
import ArtifactUnavailableState from '../components/states/ArtifactUnavailableState';
import EmptyState from '../components/states/EmptyState';
import ErrorState from '../components/states/ErrorState';
import LoadingState from '../components/states/LoadingState';
import { normalizeApiError } from '../api/errors';
import {
  SEMANTIC_COMMUNITY_PARAM,
  resolveSemanticSearchParams,
  updateSemanticSearchParams,
} from '../features/topics/semanticSearchParams';
import {
  adaptTopicRecord,
  topicKeywords,
  topicLabel,
  topicRecordKey,
} from '../features/topics/topicModel';
import { useThematicAnalysisData } from '../features/topics/useThematicAnalysisData';
import { adaptThemeRecord } from '../features/themes/themeModel';
import {
  periodLabel,
  timelineSummaryMetrics,
} from '../features/themes/themeTrendModel';
import MonthlyThemeMatrix from '../features/themes/MonthlyThemeMatrix';
import AggregateThemeProgression from '../features/themes/AggregateThemeProgression';
import ThematicMethodologyOverview from '../features/themes/ThematicMethodologyOverview';
import { clampPageOffset, nextPageOffset, pageRange, previousPageOffset } from '../utils/pagination';

const TOPIC_LIMIT = 10;
const THEME_LIMIT = 8;

const THEMATIC_SECTIONS = [
  { id: 'thematic-methodology', label: 'Methodology', icon: 'metadata' },
  { id: 'thematic-overview', label: 'Overview', icon: 'kpis' },
  { id: 'thematic-monthly-themes', label: 'Monthly Themes', icon: 'themes' },
  { id: 'thematic-progression', label: 'Theme Progression', icon: 'trends' },
  { id: 'thematic-evidence-explorer', label: 'Evidence Explorer', icon: 'communities' },
  { id: 'thematic-canonical-evidence', label: 'Canonical Evidence', icon: 'themes' },
  { id: 'thematic-theme-labels', label: 'Theme Labels', icon: 'themes' },
  { id: 'thematic-lda-evidence', label: 'LDA Evidence', icon: 'provenance' },
  { id: 'thematic-provenance', label: 'Provenance', icon: 'provenance' },
];

function isArtifactUnavailable(error) {
  return normalizeApiError(error).code === 'ARTIFACT_NOT_AVAILABLE';
}

function networkHref(params, metric, communityId, period = null) {
  const next = new URLSearchParams(params);
  next.set('metric', metric);
  next.set('community', communityId);
  if (period) next.set('period', period);
  return `/network?${next.toString()}`;
}

export default function ThematicAnalysisPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const semanticState = resolveSemanticSearchParams(searchParams);
  const [communityDraft, setCommunityDraft] = useState(semanticState.communityId ?? '');
  const [topicOffset, setTopicOffset] = useState(0);
  const [themeOffset, setThemeOffset] = useState(0);
  const [selectedTopicIndex, setSelectedTopicIndex] = useState(0);

  useEffect(() => {
    const canonical = updateSemanticSearchParams(searchParams, {
      ...semanticState,
      topicType: 'matched',
      selectedPath: null,
    });
    if (canonical.toString() !== searchParams.toString()) {
      setSearchParams(canonical, { replace: true });
    }
  }, [searchParams, semanticState, setSearchParams]);

  useEffect(() => {
    setCommunityDraft(semanticState.communityId ?? '');
  }, [semanticState.communityId]);

  const data = useThematicAnalysisData({
    communityId: semanticState.communityId,
    month: semanticState.month,
    canonicalThemeId: semanticState.canonicalThemeId,
    timelineStart: semanticState.timelineStart,
    timelineEnd: semanticState.timelineEnd,
    topicOffset,
    topicLimit: TOPIC_LIMIT,
    themeOffset,
    themeLimit: THEME_LIMIT,
  });
  const {
    selectedRunId,
    overviewQuery,
    topicsQuery,
    themesQuery,
    timelineQuery,
    clusterEvidenceQuery,
  } = data;

  const availablePeriods = useMemo(() => {
    const themePeriods = timelineQuery.data?.available_periods ?? [];
    const source = themePeriods.length > 0
      ? themePeriods
      : overviewQuery.data?.available_periods ?? [];
    return [...new Set(source)].sort();
  }, [overviewQuery.data?.available_periods, timelineQuery.data?.available_periods]);
  const timelinePeriods = timelineQuery.data?.periods ?? [];

  useEffect(() => {
    if (availablePeriods.length === 0) return;
    const patch = {};
    if (semanticState.timelineStart && !availablePeriods.includes(semanticState.timelineStart)) {
      patch.timelineStart = null;
    }
    if (semanticState.timelineEnd && !availablePeriods.includes(semanticState.timelineEnd)) {
      patch.timelineEnd = null;
    }
    const start = patch.timelineStart === null ? null : semanticState.timelineStart;
    const end = patch.timelineEnd === null ? null : semanticState.timelineEnd;
    if (start && end && start > end) patch.timelineEnd = start;

    const evidencePeriods = timelinePeriods.length > 0 ? timelinePeriods : availablePeriods;
    if (!semanticState.month || !evidencePeriods.includes(semanticState.month)) {
      patch.month = evidencePeriods[evidencePeriods.length - 1];
      patch.canonicalThemeId = null;
    }
    if (Object.keys(patch).length === 0) return;
    setSearchParams(updateSemanticSearchParams(searchParams, patch), { replace: true });
  }, [
    availablePeriods,
    searchParams,
    semanticState.month,
    semanticState.timelineEnd,
    semanticState.timelineStart,
    setSearchParams,
    timelinePeriods,
  ]);

  useEffect(() => {
    const response = topicsQuery.data;
    if (!response) return;
    const safeOffset = clampPageOffset(topicOffset, response.total, response.limit);
    if (safeOffset !== topicOffset) setTopicOffset(safeOffset);
  }, [topicOffset, topicsQuery.data]);

  useEffect(() => {
    const response = themesQuery.data;
    if (!response) return;
    const safeOffset = clampPageOffset(themeOffset, response.total, response.limit);
    if (safeOffset !== themeOffset) setThemeOffset(safeOffset);
  }, [themeOffset, themesQuery.data]);

  const topicModels = useMemo(
    () => (topicsQuery.data?.records ?? []).map((record) => adaptTopicRecord(record, 'matched')),
    [topicsQuery.data?.records],
  );
  const allThemeModels = useMemo(
    () => (themesQuery.data?.records ?? []).map((record) =>
      adaptThemeRecord(record, themesQuery.data?.provider_metadata ?? null),
    ),
    [themesQuery.data?.provider_metadata, themesQuery.data?.records],
  );
  const themeModels = allThemeModels;
  const selectedTopic = topicModels[selectedTopicIndex] ?? topicModels[0] ?? null;

  useEffect(() => {
    if (selectedTopicIndex >= topicModels.length) setSelectedTopicIndex(0);
  }, [selectedTopicIndex, topicModels.length]);

  const updateControls = (patch) => {
    setSearchParams(updateSemanticSearchParams(searchParams, patch));
    if ('communityId' in patch || 'month' in patch) setTopicOffset(0);
    if ('month' in patch || 'communityId' in patch || 'canonicalThemeId' in patch) setThemeOffset(0);
    setSelectedTopicIndex(0);
  };

  const selectThemeEvidence = (period, themeId) => {
    const sameSelection = semanticState.month === period && semanticState.canonicalThemeId === themeId;
    updateControls({
      month: period,
      canonicalThemeId: sameSelection ? null : themeId,
      selectedTheme: null,
    });
  };

  const selectedCanonicalTheme = useMemo(() => {
    if (!semanticState.canonicalThemeId) return null;
    for (const summary of timelineQuery.data?.monthly_summaries ?? []) {
      const match = summary.themes.find((theme) => theme.theme_id === semanticState.canonicalThemeId);
      if (match) return match;
    }
    return null;
  }, [semanticState.canonicalThemeId, timelineQuery.data?.monthly_summaries]);

  const summaryMetrics = timelineSummaryMetrics(timelineQuery.data);
  const providerAvailable = Boolean(
    Object.keys(themesQuery.data?.provider_metadata ?? {}).length
    || Object.keys(overviewQuery.data?.model_metadata ?? {}).length,
  );
  const topicMetricView = semanticState.metricView === 'general' ? 'both' : semanticState.metricView;
  const methodologyHref = searchParams.toString() ? `/methodology?${searchParams.toString()}` : '/methodology';

  const jumpToSection = (id) => {
    const element = document.getElementById(id);
    const container = document.getElementById('main-content');
    if (!element || !container) return;
    const containerRect = container.getBoundingClientRect();
    const elementRect = element.getBoundingClientRect();
    container.scrollTo({
      top: container.scrollTop + elementRect.top - containerRect.top - 20,
      behavior: 'smooth',
    });
    window.requestAnimationFrame(() => element.focus({ preventScroll: true }));
  };

  return (
    <div data-run-id={selectedRunId || undefined} className="mx-auto flex w-full max-w-[1600px] items-start px-1 sm:px-2">
      <div className="min-w-0 flex-1 space-y-6 pb-16">
        <section id="thematic-methodology" className="scroll-mt-6" tabIndex={-1}>
          <header>
            <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-text-heading">Thematic Analysis</h1>
            <p className="mt-1 max-w-4xl text-sm text-muted">
              Explore the themes generated for all matched IF/WIF communities across the selected timeline. Monthly rankings use distinct matched-community coverage and preserve LDA keywords as upstream evidence.
            </p>
            <p className="mt-2 text-xs text-muted">
              Persisted-community thematic similarity belongs to <Link to={`/evolution?${searchParams.toString()}`} className="font-semibold text-primary hover:underline">Community Evolution</Link> and is not used on this page.
            </p>
          </div>
              <div className="flex w-full flex-col items-end gap-3 sm:w-auto">
                <span className="rounded-full border border-primary/30 bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary">
                  All matched IF/WIF communities
                </span>
                <label className="w-full text-xs font-semibold text-muted md:hidden sm:min-w-56">
                  Jump to section
                  <select
                    aria-label="Jump to Thematic Analysis section"
                    defaultValue="thematic-methodology"
                    onChange={(event) => jumpToSection(event.target.value)}
                    className="mt-1 w-full rounded-xl border border-border bg-surface px-3 py-2.5 text-sm font-semibold text-text-heading"
                  >
                    {THEMATIC_SECTIONS.map((section) => <option key={section.id} value={section.id}>{section.label}</option>)}
                  </select>
                </label>
              </div>
            </div>
          </header>
          <div className="mt-5"><ThematicMethodologyOverview methodologyHref={methodologyHref} /></div>
        </section>

        <section id="thematic-overview" className="scroll-mt-6 space-y-4" tabIndex={-1}>
          <section className="panel p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-sm font-bold text-text-heading">Timeline scope</h2>
            <p className="mt-1 text-xs text-muted">The selected run determines the platform and interaction type.</p>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <Control label="Timeline start">
            <select
              aria-label="Theme timeline start"
              value={semanticState.timelineStart ?? ''}
              onChange={(event) => {
                const start = event.target.value || null;
                updateControls({
                  timelineStart: start,
                  timelineEnd: start && semanticState.timelineEnd && start > semanticState.timelineEnd
                    ? start
                    : semanticState.timelineEnd,
                });
              }}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-heading"
            >
              <option value="">First available month</option>
              {availablePeriods.map((period) => <option key={period} value={period}>{periodLabel(period)}</option>)}
            </select>
          </Control>
          <Control label="Timeline end">
            <select
              aria-label="Theme timeline end"
              value={semanticState.timelineEnd ?? ''}
              onChange={(event) => {
                const end = event.target.value || null;
                updateControls({
                  timelineEnd: end,
                  timelineStart: end && semanticState.timelineStart && end < semanticState.timelineStart
                    ? end
                    : semanticState.timelineStart,
                });
              }}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-heading"
            >
              <option value="">Last available month</option>
              {availablePeriods.map((period) => <option key={period} value={period}>{periodLabel(period)}</option>)}
            </select>
          </Control>
            </div>
          </section>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard title="Months analyzed" value={timelineQuery.data ? summaryMetrics.monthsAnalyzed : null} detail="Selected matched-theme timeline" source="theme-clusters.timeline.periods" icon={CalendarRange} colorClass="text-blue-400" bgClass="bg-blue-500/20" />
        <MetricCard title="Themed community-months" value={timelineQuery.data ? summaryMetrics.themedCommunityMonths : null} detail="Sum of monthly themed matched-pair denominators" source="theme-clusters.timeline.monthly_summaries" icon={GitCompareArrows} colorClass="text-green-400" bgClass="bg-green-500/20" />
        <MetricCard title="Canonical themes" value={timelineQuery.data ? summaryMetrics.distinctCanonicalThemes : null} detail="Semantic theme families across the range" source="theme-clusters.timeline.distinct_canonical_theme_count" icon={Tags} colorClass="text-purple-400" bgClass="bg-purple-500/20" />
            <MetricCard title="Most prevalent theme" value={summaryMetrics.mostPrevalentTheme} detail={summaryMetrics.mostPrevalentTheme ? `${summaryMetrics.mostPrevalentThemeCommunityMonths} community-months` : 'Unavailable'} source="theme-clusters.timeline.most_discussed_theme" icon={Database} colorClass="text-orange-400" bgClass="bg-orange-500/20" />
          </div>
        </section>

        {timelineQuery.isPending ? (
        <LoadingState title="Loading matched-community theme timeline" />
      ) : timelineQuery.error ? (
        isArtifactUnavailable(timelineQuery.error)
          ? <ArtifactUnavailableState artifactName="Matched-community theme timeline" message="Run the theme-label stage to publish monthly matched-community themes." />
          : <ErrorState error={timelineQuery.error} title="Thematic timeline could not be loaded" onRetry={() => void timelineQuery.refetch()} />
      ) : (
          <>
            <div id="thematic-monthly-themes" className="scroll-mt-6" tabIndex={-1}>
              <MonthlyThemeMatrix
                response={timelineQuery.data}
                selectedPeriod={semanticState.month}
                selectedThemeId={semanticState.canonicalThemeId}
                onSelectTheme={selectThemeEvidence}
              />
            </div>
            <div id="thematic-progression" className="min-w-0 scroll-mt-6" tabIndex={-1}>
              <AggregateThemeProgression
                response={timelineQuery.data}
                selectedPeriod={semanticState.month}
                selectedThemeId={semanticState.canonicalThemeId}
                onSelectTheme={selectThemeEvidence}
              />
            </div>
          </>
      )}

        <section id="thematic-evidence-explorer" className="panel scroll-mt-6 p-5" tabIndex={-1} aria-labelledby="evidence-controls-heading">
        <div>
          <h2 id="evidence-controls-heading" className="text-lg font-bold text-text-heading">Evidence Explorer</h2>
          <p className="mt-1 max-w-4xl text-xs text-muted">
            Inspect matched LDA records and downstream labels for one evidence month. These controls do not change the timeline rankings or aggregate progression above.
          </p>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Control label="Evidence month">
            <select
              aria-label="Evidence month"
              value={semanticState.month ?? ''}
              onChange={(event) => updateControls({ month: event.target.value || null, canonicalThemeId: null, selectedTheme: null })}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-heading"
            >
              {timelinePeriods.length === 0 && <option value="">No theme periods available</option>}
              {timelinePeriods.map((period) => <option key={period} value={period}>{periodLabel(period)}</option>)}
            </select>
          </Control>
          <Control label="Metric evidence view">
            <select
              aria-label="Semantic metric view"
              value={semanticState.metricView}
              onChange={(event) => updateControls({ metricView: event.target.value })}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-heading"
            >
              <option value="general">General labels only</option>
              <option value="both">IF and WIF side by side</option>
              <option value="if">IF only</option>
              <option value="wif">WIF only</option>
            </select>
          </Control>
          <Control label="Token representation">
            <select
              aria-label="Token representation"
              value={semanticState.tokenView}
              onChange={(event) => updateControls({ tokenView: event.target.value })}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-heading"
            >
              <option value="unigram">Unigram LDA</option>
              <option value="bigram">Bigram LDA</option>
              <option value="combined">Combined saved keywords</option>
            </select>
          </Control>
          <Control label="Exact community ID">
            <div className="flex gap-2">
              <input
                aria-label="Exact community ID"
                value={communityDraft}
                onChange={(event) => setCommunityDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') updateControls({ communityId: communityDraft.trim() || null });
                }}
                className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-heading"
                placeholder="e.g. 12"
              />
              <button
                type="button"
                onClick={() => updateControls({ communityId: communityDraft.trim() || null })}
                className="rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white hover:bg-primary/90"
              >
                Apply
              </button>
            </div>
          </Control>
        </div>
        <p className="mt-4 text-xs text-muted">
          Topic evidence is restricted to matched communities on this route. Partially matched topic records remain available on the Topic Modeling page.
          {semanticState.communityId && (
            <button type="button" onClick={() => updateControls({ communityId: null })} className="ml-2 font-semibold text-primary hover:text-primary/80">Clear community filter</button>
          )}
        </p>
      </section>

        <section id="thematic-canonical-evidence" className="scroll-mt-6" tabIndex={-1}>
          <div className="panel overflow-hidden" aria-labelledby="cluster-evidence-heading">
            <div className="border-b border-border p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 id="cluster-evidence-heading" className="text-lg font-bold text-text-heading">Evidence · Canonical theme cluster</h2>
                  <p className="mt-1 text-xs text-muted">Shows the generated general-theme labels and matched-community evidence that formed the selected upstream semantic cluster.</p>
                </div>
                {semanticState.canonicalThemeId && (
                  <button type="button" onClick={() => updateControls({ canonicalThemeId: null })} className="rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
                    {selectedCanonicalTheme?.name ?? semanticState.canonicalThemeId} · clear
                  </button>
                )}
              </div>
            </div>
            {!semanticState.canonicalThemeId ? (
              <div className="p-5">
                <p className="text-sm text-muted">Select a ranked canonical theme above to inspect the source labels and matched-community evidence that formed it.</p>
              </div>
            ) : clusterEvidenceQuery.isPending ? (
              <LoadingState title="Loading canonical-theme evidence" />
            ) : clusterEvidenceQuery.error ? (
              <ErrorState error={clusterEvidenceQuery.error} title="Canonical-theme evidence could not be loaded" onRetry={() => void clusterEvidenceQuery.refetch()} />
            ) : (clusterEvidenceQuery.data?.records ?? []).length === 0 ? (
              <EmptyState title="No cluster evidence" message="No saved source observations are available for this canonical theme in the selected month." />
            ) : (
              <div className="grid grid-cols-1 divide-y divide-border/50 lg:grid-cols-2 lg:divide-x lg:divide-y-0">
                {(clusterEvidenceQuery.data?.records ?? []).map((record, index) => (
                  <article key={`${record.period}:${record.absolute_community ?? ''}:${record.weighted_community ?? ''}:${record.source_general_theme_label}:${index}`} className="p-5">
                    <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
                      <span>IF {record.absolute_community ?? '—'} · WIF {record.weighted_community ?? '—'}</span>
                      <span>HDBSCAN membership: {record.membership_probability == null ? 'Unavailable' : record.membership_probability.toFixed(3)}</span>
                    </div>
                    <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-muted">Source generated general label</p>
                    <p className="mt-1 font-semibold text-text-heading">{record.source_general_theme_label}</p>
                    <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-muted">Monthly representative</p>
                    <p className="mt-1 text-sm text-text-heading">{record.monthly_representative_theme ?? 'Unavailable'}</p>
                    <div className="mt-4"><p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">General LDA keyword evidence</p><KeywordList keywords={record.keywords} /></div>
                  </article>
                ))}
              </div>
            )}
          </div>
        </section>

        <section id="thematic-theme-labels" className="panel scroll-mt-6 overflow-hidden" tabIndex={-1}>
          <div className="border-b border-border p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-text-heading">Evidence · Generated theme labels</h2>
                <p className="mt-1 text-xs text-muted">Provider-generated labels are displayed with the LDA keywords that supplied their evidence.</p>
              </div>
            </div>
          </div>
          {themesQuery.isPending ? (
            <LoadingState title="Loading theme records" />
          ) : themesQuery.error ? (
            isArtifactUnavailable(themesQuery.error)
              ? <ArtifactUnavailableState artifactName="Monthly theme artifact" message="Run the theme-label stage after LDA topics are available for this run." />
              : <ErrorState error={themesQuery.error} title="Theme records could not be loaded" onRetry={() => void themesQuery.refetch()} />
          ) : themeModels.length === 0 ? (
            <EmptyState title="No theme records" message="The evidence month and exact community filter returned no downstream theme labels." />
          ) : (
            <div className="grid grid-cols-1 divide-y divide-border/50 lg:grid-cols-2 lg:divide-x lg:divide-y-0">
              {themeModels.map((theme, index) => (
                <article key={`${theme.ifCommunityId ?? ''}:${theme.wifCommunityId ?? ''}:${index}`} className="p-5">
                  <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
                    <span>Month: {semanticState.month ?? theme.month ?? 'Unavailable'}</span>
                    <span>IF {theme.ifCommunityId ?? '—'} · WIF {theme.wifCommunityId ?? '—'}</span>
                  </div>
                  <div className="mt-4">
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Provider-generated general label</p>
                    <ThemeLabel names={theme.generalThemes} />
                  </div>
                  <div className="mt-4">
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">LDA keyword evidence</p>
                    <KeywordList keywords={theme.generalKeywords} />
                  </div>
                  {semanticState.metricView !== 'general' && (
                    <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
                      {semanticState.metricView !== 'wif' && <ThemeMetricEvidence label="IF" names={theme.ifThemes} keywords={theme.ifKeywords} communityId={theme.ifCommunityId} metric="if" searchParams={searchParams} period={semanticState.month} />}
                      {semanticState.metricView !== 'if' && <ThemeMetricEvidence label="WIF" names={theme.wifThemes} keywords={theme.wifKeywords} communityId={theme.wifCommunityId} metric="wif" searchParams={searchParams} period={semanticState.month} />}
                    </div>
                  )}
                </article>
              ))}
            </div>
          )}
          <PaginationBar
            label="theme records"
            offset={themeOffset}
            limit={THEME_LIMIT}
            total={themesQuery.data?.total ?? 0}
            onPrevious={() => setThemeOffset(previousPageOffset(themeOffset, THEME_LIMIT))}
            onNext={() => setThemeOffset(nextPageOffset(themeOffset, themesQuery.data?.total ?? 0, THEME_LIMIT))}
          />
        </section>

        <section id="thematic-lda-evidence" className="panel scroll-mt-6 overflow-hidden" tabIndex={-1}>
          <div className="border-b border-border p-5">
            <h2 className="text-lg font-bold text-text-heading">Evidence · Matched LDA topic records</h2>
            <p className="mt-1 text-xs text-muted">Deep upstream evidence: community IDs, selected topic representation, keywords, and membership overlap from canonical matched-topic artifacts.</p>
            {semanticState.metricView === 'general' && <p className="mt-2 text-xs text-muted">General labels have no separate LDA metric artifact, so IF and WIF topic evidence remains side by side.</p>}
          </div>
          {topicsQuery.isPending ? (
            <LoadingState title="Loading matched LDA topic records" />
          ) : topicsQuery.error ? (
            isArtifactUnavailable(topicsQuery.error)
              ? <ArtifactUnavailableState artifactName="Matched LDA topic artifact" message="Run the matched topic stage before opening the semantic evidence browser." />
              : <ErrorState error={topicsQuery.error} title="Topic records could not be loaded" onRetry={() => void topicsQuery.refetch()} />
          ) : topicModels.length === 0 ? (
            <EmptyState title="No matched topic records" message="The evidence month and exact community filter returned no matched LDA records." />
          ) : (
            <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1.6fr)_minmax(300px,0.9fr)]">
              <div className="divide-y divide-border/50">
                {topicModels.map((topic, index) => (
                  <button
                    type="button"
                    key={topicRecordKey(topic, index)}
                    onClick={() => setSelectedTopicIndex(index)}
                    className={`block w-full p-5 text-left hover:bg-surface-soft/40 ${selectedTopic === topic ? 'bg-primary/5' : ''}`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex flex-wrap items-center gap-3 text-xs">
                        <span className="rounded border border-border bg-bg/30 px-2 py-1 text-text-heading">IF {topic.ifCommunityId ?? 'Unavailable'}</span>
                        <span className="rounded border border-border bg-bg/30 px-2 py-1 text-text-heading">WIF {topic.wifCommunityId ?? 'Unavailable'}</span>
                      </div>
                      <span className="text-xs text-muted">Jaccard: {topic.jaccardScore === null ? 'Unavailable' : topic.jaccardScore.toFixed(3)}</span>
                    </div>
                    <div className={`mt-4 grid gap-4 ${topicMetricView === 'both' ? 'md:grid-cols-2' : 'grid-cols-1'}`}>
                      {topicMetricView !== 'wif' && <TopicMetricSummary label="IF" topic={topic} metric="if" tokenView={semanticState.tokenView} />}
                      {topicMetricView !== 'if' && <TopicMetricSummary label="WIF" topic={topic} metric="wif" tokenView={semanticState.tokenView} />}
                    </div>
                  </button>
                ))}
              </div>
              <TopicDetailPanel topic={selectedTopic} searchParams={searchParams} period={semanticState.month} />
            </div>
          )}
          <PaginationBar
            label="topic records"
            offset={topicOffset}
            limit={TOPIC_LIMIT}
            total={topicsQuery.data?.total ?? 0}
            onPrevious={() => setTopicOffset(previousPageOffset(topicOffset, TOPIC_LIMIT))}
            onNext={() => setTopicOffset(nextPageOffset(topicOffset, topicsQuery.data?.total ?? 0, TOPIC_LIMIT))}
          />
        </section>

        <section id="thematic-provenance" className="scroll-mt-6" tabIndex={-1}>
          <ProviderMetadata
            providerMetadata={themesQuery.data?.provider_metadata}
            modelMetadata={overviewQuery.data?.model_metadata}
          />
          <p className="mt-3 text-xs text-muted">
            Provider metadata status: {providerAvailable ? 'available' : 'unavailable'}. Evidence filters are stored in the URL under {SEMANTIC_COMMUNITY_PARAM} and related parameters for reproducible links.
          </p>
        </section>
      </div>

      <div className="pointer-events-none sticky top-0 z-40 ml-4 hidden h-screen w-14 shrink-0 flex-col justify-center md:flex lg:ml-6">
        <PageNavigationRail sections={THEMATIC_SECTIONS} />
      </div>
    </div>
  );
}

function Control({ label, children }) {
  return <label className="text-xs font-semibold text-muted"><span className="mb-2 block">{label}</span>{children}</label>;
}

function TopicMetricSummary({ label, topic, metric, tokenView }) {
  return (
    <div className="rounded-lg border border-border/70 bg-bg/20 p-3">
      <p className="text-xs font-semibold text-text-heading">{label} {tokenView} topic: {topicLabel(topic, metric, tokenView)}</p>
      <div className="mt-2"><KeywordList keywords={topicKeywords(topic, metric, tokenView)} limit={12} /></div>
    </div>
  );
}

function TopicDetailPanel({ topic, searchParams, period }) {
  if (!topic) return null;
  return (
    <aside className="border-t border-border bg-bg/20 p-5 xl:border-l xl:border-t-0">
      <h3 className="text-sm font-bold text-text-heading">Selected topic record</h3>
      <dl className="mt-4 space-y-3 text-xs">
        <Detail label="Record type" value={topic.recordType} />
        <Detail label="Jaccard score" value={topic.jaccardScore === null ? 'Unavailable' : topic.jaccardScore.toFixed(4)} />
        <Detail label="IF unigram topic" value={topicLabel(topic, 'if', 'unigram')} />
        <Detail label="WIF unigram topic" value={topicLabel(topic, 'wif', 'unigram')} />
        <Detail label="IF bigram topic" value={topicLabel(topic, 'if', 'bigram')} />
        <Detail label="WIF bigram topic" value={topicLabel(topic, 'wif', 'bigram')} />
        <Detail label="Common members" value={topic.commonMembers.length ? topic.commonMembers.join(', ') : 'Unavailable'} />
        <Detail label="Uncommon members" value={topic.uncommonMembers.length ? topic.uncommonMembers.join(', ') : 'Unavailable'} />
        <Detail label="Shared members field" value={topic.members.length ? topic.members.join(', ') : 'Unavailable'} />
        <Detail label="IF members" value={topic.ifMembers.length ? topic.ifMembers.join(', ') : 'Unavailable'} />
        <Detail label="WIF members" value={topic.wifMembers.length ? topic.wifMembers.join(', ') : 'Unavailable'} />
      </dl>
      <div className="mt-5 space-y-4">
        <div><p className="mb-2 text-xs font-semibold text-muted">IF unigram keywords</p><KeywordList keywords={topic.ifUnigramKeywords} /></div>
        <div><p className="mb-2 text-xs font-semibold text-muted">IF bigram keywords</p><KeywordList keywords={topic.ifBigramKeywords} /></div>
        <div><p className="mb-2 text-xs font-semibold text-muted">WIF unigram keywords</p><KeywordList keywords={topic.wifUnigramKeywords} /></div>
        <div><p className="mb-2 text-xs font-semibold text-muted">WIF bigram keywords</p><KeywordList keywords={topic.wifBigramKeywords} /></div>
      </div>
      <div className="mt-5 flex flex-col gap-2">
        {topic.ifCommunityId && <CommunityLink label="Open IF community" href={networkHref(searchParams, 'if', topic.ifCommunityId, period)} />}
        {topic.wifCommunityId && <CommunityLink label="Open WIF community" href={networkHref(searchParams, 'wif', topic.wifCommunityId, period)} />}
      </div>
    </aside>
  );
}

function ThemeMetricEvidence({ label, names, keywords, communityId, metric, searchParams, period }) {
  return (
    <div className="rounded-lg border border-border/70 bg-bg/20 p-3">
      <p className="mb-2 text-xs font-semibold text-text-heading">{label} provider label</p>
      <ThemeLabel names={names} />
      <p className="mb-2 mt-4 text-xs font-semibold text-muted">{label} keyword evidence</p>
      <KeywordList keywords={keywords} limit={12} />
      {communityId && <CommunityLink label={`Open ${label} community`} href={networkHref(searchParams, metric, communityId, period)} />}
    </div>
  );
}

function CommunityLink({ label, href }) {
  return <Link to={href} className="mt-3 inline-flex items-center gap-2 text-xs font-semibold text-primary hover:text-primary/80"><Network size={13} /> {label}</Link>;
}

function Detail({ label, value }) {
  return <div className="rounded-lg border border-border/70 bg-surface-soft/30 p-3"><dt className="text-muted">{label}</dt><dd className="mt-1 break-words font-semibold text-text-heading"><ArtifactValue value={value} /></dd></div>;
}

function PaginationBar({ label, offset, limit, total, onPrevious, onNext }) {
  return (
    <div className="flex flex-col gap-3 border-t border-border px-5 py-3 text-xs text-muted sm:flex-row sm:items-center sm:justify-between">
      <span>{pageRange(offset, limit, total)} {label}</span>
      <div className="flex gap-2">
        <button type="button" aria-label={`Previous ${label} page`} disabled={offset <= 0} onClick={onPrevious} className="rounded border border-border p-1.5 disabled:opacity-40"><ChevronLeft size={15} /></button>
        <button type="button" aria-label={`Next ${label} page`} disabled={offset + limit >= total} onClick={onNext} className="rounded border border-border p-1.5 disabled:opacity-40"><ChevronRight size={15} /></button>
      </div>
    </div>
  );
}
