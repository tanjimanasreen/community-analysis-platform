import React, { useEffect, useMemo, useState } from 'react';
import {
  BookOpen,
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
import SimilarityMatrix from '../components/SimilarityMatrix';
import ThemeLabel from '../components/ThemeLabel';
import ArtifactUnavailableState from '../components/states/ArtifactUnavailableState';
import EmptyState from '../components/states/EmptyState';
import ErrorState from '../components/states/ErrorState';
import LoadingState from '../components/states/LoadingState';
import { normalizeApiError } from '../api/errors';
import { getArtifactDownloadUrl } from '../api/reports';
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
import {
  adaptThemeRecord,
  availableThemeMonths,
  themeFrequencies,
} from '../features/themes/themeModel';
import { clampPageOffset, nextPageOffset, pageRange, previousPageOffset } from '../utils/pagination';

const TOPIC_LIMIT = 10;
const THEME_LIMIT = 8;

function isArtifactUnavailable(error) {
  return normalizeApiError(error).code === 'ARTIFACT_NOT_AVAILABLE';
}

function networkHref(params, metric, communityId) {
  const next = new URLSearchParams(params);
  next.set('metric', metric);
  next.set('community', communityId);
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
    const canonical = updateSemanticSearchParams(searchParams, semanticState);
    if (canonical.toString() !== searchParams.toString()) {
      setSearchParams(canonical, { replace: true });
    }
  }, [searchParams, semanticState, setSearchParams]);

  useEffect(() => {
    setCommunityDraft(semanticState.communityId ?? '');
  }, [semanticState.communityId]);

  const data = useThematicAnalysisData({
    topicType: semanticState.topicType,
    communityId: semanticState.communityId,
    month: semanticState.month,
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
    themeSummaryQuery,
    themeCatalogQuery,
    similarityQuery,
  } = data;

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
    () => (topicsQuery.data?.records ?? []).map((record) => adaptTopicRecord(record, semanticState.topicType)),
    [semanticState.topicType, topicsQuery.data?.records],
  );
  const themeModels = useMemo(
    () => (themesQuery.data?.records ?? []).map((record) =>
      adaptThemeRecord(record, themesQuery.data?.provider_metadata ?? null),
    ),
    [themesQuery.data?.provider_metadata, themesQuery.data?.records],
  );
  const frequencies = useMemo(
    () => themeSummaryQuery.data ? themeFrequencies(themeSummaryQuery.data) : null,
    [themeSummaryQuery.data],
  );
  const months = useMemo(
    () => availableThemeMonths(themeCatalogQuery.data?.records ?? []),
    [themeCatalogQuery.data?.records],
  );
  const selectedTopic = topicModels[selectedTopicIndex] ?? topicModels[0] ?? null;

  useEffect(() => {
    if (selectedTopicIndex >= topicModels.length) setSelectedTopicIndex(0);
  }, [selectedTopicIndex, topicModels.length]);

  const updateControls = (patch) => {
    setSearchParams(updateSemanticSearchParams(searchParams, patch));
    if ('topicType' in patch || 'communityId' in patch) setTopicOffset(0);
    if ('month' in patch || 'communityId' in patch) setThemeOffset(0);
    setSelectedTopicIndex(0);
  };

  const completeUniqueThemeCount = frequencies === null ? null : frequencies.length;
  const providerAvailable = Boolean(
    Object.keys(themesQuery.data?.provider_metadata ?? themeCatalogQuery.data?.provider_metadata ?? {}).length ||
    Object.keys(overviewQuery.data?.model_metadata ?? {}).length,
  );

  return (
    <div data-run-id={selectedRunId || undefined} className="mx-auto flex w-full max-w-[1600px] flex-col gap-6">
      <header>
        <h1 className="text-xl font-bold text-text-heading">Thematic Analysis</h1>
        <p className="mt-1 max-w-4xl text-sm text-muted">
          LDA topics and keyword evidence are shown first. Human-readable theme labels are downstream provider outputs and never replace the topic model.
        </p>
      </header>

      <section className="panel p-5">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
          <Control label="Topic records">
            <select
              aria-label="Topic record type"
              value={semanticState.topicType}
              onChange={(event) => updateControls({ topicType: event.target.value })}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-heading"
            >
              <option value="matched">Matched communities</option>
              <option value="partial">Partially matched communities</option>
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
            </select>
          </Control>
          <Control label="Metric view">
            <select
              aria-label="Semantic metric view"
              value={semanticState.metricView}
              onChange={(event) => updateControls({ metricView: event.target.value })}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-heading"
            >
              <option value="both">IF and WIF side by side</option>
              <option value="if">IF only</option>
              <option value="wif">WIF only</option>
            </select>
          </Control>
          <Control label="Theme month">
            <select
              aria-label="Theme month"
              value={semanticState.month ?? ''}
              onChange={(event) => updateControls({ month: event.target.value || null })}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-heading"
            >
              <option value="">All available months</option>
              {months.map((month) => <option key={month} value={month}>{month}</option>)}
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
          Matched/partial describes structural overlap between IF and WIF communities. Unigram/bigram selects the saved LDA keyword representation.
          {semanticState.communityId && (
            <button
              type="button"
              onClick={() => updateControls({ communityId: null })}
              className="ml-2 font-semibold text-primary hover:text-primary/80"
            >
              Clear community filter
            </button>
          )}
        </p>
      </section>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title={`${semanticState.topicType === 'matched' ? 'Matched' : 'Partial'} topic records`} value={topicsQuery.data?.total ?? null} detail="Server-side total for the current community filter" source="TopicsResponse.total" icon={BookOpen} colorClass="text-blue-400" bgClass="bg-blue-500/20" />
        <MetricCard title="Theme records" value={themesQuery.data?.total ?? null} detail={semanticState.month ? `Filtered to month ${semanticState.month}` : 'All available theme months'} source="ThemesResponse.total" icon={Tags} colorClass="text-purple-400" bgClass="bg-purple-500/20" />
        <MetricCard title="Matched communities" value={overviewQuery.data?.matched_percentage ?? null} detail="Structural IF/WIF match rate" source="OverviewResponse.matched_percentage" icon={GitCompareArrows} colorClass="text-green-400" bgClass="bg-green-500/20" format={(value) => `${value}%`} />
        <MetricCard title="Unique theme labels" value={completeUniqueThemeCount} detail={frequencies === null ? 'Unavailable until the complete filtered result fits the safe summary cap' : 'Distinct general labels in the complete filtered result'} source="ThemesResponse.records.general_theme_names" icon={Database} colorClass="text-orange-400" bgClass="bg-orange-500/20" />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <ThemeFrequencyPanel query={themeSummaryQuery} frequencies={frequencies} />
        <ProviderMetadata
          providerMetadata={themesQuery.data?.provider_metadata ?? themeCatalogQuery.data?.provider_metadata}
          modelMetadata={overviewQuery.data?.model_metadata}
        />
      </div>

      <section className="panel overflow-hidden">
        <div className="border-b border-border p-5">
          <h2 className="text-lg font-bold text-text-heading">LDA topic records</h2>
          <p className="mt-1 text-xs text-muted">Community IDs, selected topic representation, keyword evidence, and membership overlap from canonical topic artifacts.</p>
        </div>
        {topicsQuery.isPending ? (
          <LoadingState title="Loading LDA topic records" />
        ) : topicsQuery.error ? (
          isArtifactUnavailable(topicsQuery.error)
            ? <ArtifactUnavailableState artifactName={`${semanticState.topicType} LDA topic artifact`} message="Run the topic stage for this record type before opening the semantic browser." />
            : <ErrorState error={topicsQuery.error} title="Topic records could not be loaded" onRetry={() => void topicsQuery.refetch()} />
        ) : topicModels.length === 0 ? (
          <EmptyState title="No topic records" message="The selected record type and exact community filter returned no LDA records." />
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
                  <div className={`mt-4 grid gap-4 ${semanticState.metricView === 'both' ? 'md:grid-cols-2' : 'grid-cols-1'}`}>
                    {semanticState.metricView !== 'wif' && <TopicMetricSummary label="IF" topic={topic} metric="if" tokenView={semanticState.tokenView} />}
                    {semanticState.metricView !== 'if' && <TopicMetricSummary label="WIF" topic={topic} metric="wif" tokenView={semanticState.tokenView} />}
                  </div>
                </button>
              ))}
            </div>
            <TopicDetailPanel topic={selectedTopic} searchParams={searchParams} />
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

      <section className="panel overflow-hidden">
        <div className="border-b border-border p-5">
          <h2 className="text-lg font-bold text-text-heading">Downstream theme labels</h2>
          <p className="mt-1 text-xs text-muted">Provider-generated labels are displayed with the LDA keywords that supplied their evidence.</p>
        </div>
        {themesQuery.isPending ? (
          <LoadingState title="Loading theme records" />
        ) : themesQuery.error ? (
          isArtifactUnavailable(themesQuery.error)
            ? <ArtifactUnavailableState artifactName="Monthly theme artifact" message="Run the theme-label stage after LDA topics are available for this run." />
            : <ErrorState error={themesQuery.error} title="Theme records could not be loaded" onRetry={() => void themesQuery.refetch()} />
        ) : themeModels.length === 0 ? (
          <EmptyState title="No theme records" message="The selected month and exact community filter returned no downstream theme labels." />
        ) : (
          <div className="grid grid-cols-1 divide-y divide-border/50 lg:grid-cols-2 lg:divide-x lg:divide-y-0">
            {themeModels.map((theme, index) => (
              <article key={`${theme.ifCommunityId ?? ''}:${theme.wifCommunityId ?? ''}:${index}`} className="p-5">
                <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
                  <span>Month: {theme.month ?? 'Unavailable'}</span>
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
                <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {semanticState.metricView !== 'wif' && <ThemeMetricEvidence label="IF" names={theme.ifThemes} keywords={theme.ifKeywords} communityId={theme.ifCommunityId} metric="if" searchParams={searchParams} />}
                  {semanticState.metricView !== 'if' && <ThemeMetricEvidence label="WIF" names={theme.wifThemes} keywords={theme.wifKeywords} communityId={theme.wifCommunityId} metric="wif" searchParams={searchParams} />}
                </div>
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

      <section className="panel p-5">
        <h2 className="text-lg font-bold text-text-heading">Theme similarity</h2>
        <p className="mt-1 text-xs text-muted">Only saved similarity matrices or manifest-listed visualization artifacts are shown. No embeddings are computed in the browser.</p>
        <div className="mt-5">
          {similarityQuery.isPending ? (
            <LoadingState title="Loading theme similarity" />
          ) : similarityQuery.error ? (
            isArtifactUnavailable(similarityQuery.error)
              ? <ArtifactUnavailableState artifactName="Theme similarity artifact" message="Run the longitudinal theme-similarity stage to populate this optional panel." />
              : <ErrorState error={similarityQuery.error} title="Theme similarity could not be loaded" onRetry={() => void similarityQuery.refetch()} />
          ) : similarityQuery.data?.matrix && similarityQuery.data.labels.length > 0 ? (
            <SimilarityMatrix matrix={similarityQuery.data.matrix} labels={similarityQuery.data.labels} />
          ) : similarityQuery.data?.artifacts?.length ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {similarityQuery.data.artifacts.map((artifact) => {
                const url = getArtifactDownloadUrl(selectedRunId, artifact.artifact_key);
                return (
                  <article key={artifact.artifact_key} className="rounded-lg border border-border bg-bg/30 p-4">
                    {artifact.media_type.startsWith('image/') && (
                      <img src={url} alt={`Theme similarity artifact ${artifact.artifact_key}`} className="mb-3 max-h-80 w-full rounded object-contain" />
                    )}
                    <p className="break-all text-sm font-semibold text-text-heading">{artifact.artifact_key}</p>
                    <p className="mt-1 text-xs text-muted">{artifact.media_type}</p>
                    <a href={url} className="mt-3 inline-flex text-sm font-semibold text-primary hover:text-primary/80">Open artifact</a>
                  </article>
                );
              })}
            </div>
          ) : (
            <ArtifactUnavailableState artifactName="Theme similarity artifact" />
          )}
        </div>
      </section>

      <p className="text-xs text-muted">
        Provider metadata status: {providerAvailable ? 'available' : 'unavailable'}. Semantic filters are stored in the URL under {SEMANTIC_COMMUNITY_PARAM} and related parameters for reproducible links.
      </p>
    </div>
  );
}

function Control({ label, children }) {
  return <label className="text-xs font-semibold text-muted"><span className="mb-2 block">{label}</span>{children}</label>;
}

function ThemeFrequencyPanel({ query, frequencies }) {
    return (
     <section className="panel p-5">
      <h2 className="text-sm font-bold text-text-heading">Theme-frequency summary</h2>
      <p className="mt-1 text-xs text-muted">Counts general provider labels, falling back to metric-specific labels when needed. The denominator is the number of labels across the complete filtered result.</p>
      {query.isPending ? (
        <div className="mt-5 h-40 animate-pulse rounded-lg bg-surface-soft" aria-live="polite" />
      ) : query.error ? (
        <p className="mt-4 text-xs text-muted">Theme summary unavailable because the theme artifact could not be loaded.</p>
      ) : frequencies === null ? (
         <p className="mt-4 rounded-lg border border-border bg-surface-soft/40 p-3 text-xs text-muted">The filtered result exceeds the 500-record safe cap, so no partial frequency chart is shown. Use the paginated theme browser below.</p>
      ) : frequencies.length === 0 ? (
        <p className="mt-4 text-xs text-muted">No theme labels are available for the current filter.</p>
      ) : (
        <div className="mt-4 space-y-3">
          {frequencies.slice(0, 8).map((frequency) => (
            <div key={frequency.name}>
              <div className="mb-1 flex items-center justify-between gap-3 text-xs">
                <span className="truncate font-medium text-text-heading" title={frequency.name}>{frequency.name}</span>
                <span className="text-muted">{frequency.count} / {frequency.percentage.toFixed(1)}%</span>
              </div>
               <div className="h-2.5 rounded-full bg-surface-soft">
                <div className="h-2.5 rounded-full" style={{ width: `${frequency.percentage}%`, backgroundColor: frequency.color }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function TopicMetricSummary({ label, topic, metric, tokenView }) {
  return (
    <div className="rounded-lg border border-border/70 bg-bg/20 p-3">
      <p className="text-xs font-semibold text-text-heading">{label} {tokenView} topic: {topicLabel(topic, metric, tokenView)}</p>
      <div className="mt-2"><KeywordList keywords={topicKeywords(topic, metric, tokenView)} limit={12} /></div>
    </div>
  );
}

function TopicDetailPanel({ topic, searchParams }) {
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
        {topic.ifCommunityId && <CommunityLink label="Open IF community" href={networkHref(searchParams, 'if', topic.ifCommunityId)} />}
        {topic.wifCommunityId && <CommunityLink label="Open WIF community" href={networkHref(searchParams, 'wif', topic.wifCommunityId)} />}
      </div>
    </aside>
  );
}

function ThemeMetricEvidence({ label, names, keywords, communityId, metric, searchParams }) {
  return (
    <div className="rounded-lg border border-border/70 bg-bg/20 p-3">
      <p className="mb-2 text-xs font-semibold text-text-heading">{label} provider label</p>
      <ThemeLabel names={names} />
      <p className="mb-2 mt-4 text-xs font-semibold text-muted">{label} keyword evidence</p>
      <KeywordList keywords={keywords} limit={12} />
      {communityId && <CommunityLink label={`Open ${label} community`} href={networkHref(searchParams, metric, communityId)} />}
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
