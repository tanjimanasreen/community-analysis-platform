import React, { useEffect, useMemo } from 'react';
import { Activity, CalendarRange, GitBranch, Timer } from 'lucide-react';
import { useLocation, useSearchParams } from 'react-router-dom';
import { PageNavigationRailSlot } from '../components/PageNavigationRail';
import ArtifactUnavailableState from '../components/states/ArtifactUnavailableState';
import ErrorState from '../components/states/ErrorState';
import LoadingState from '../components/states/LoadingState';
import { normalizeApiError } from '../api/errors';
import EvolutionEvidence from '../features/evolution/components/EvolutionEvidence';
import EvolutionMethodologyStrip from '../features/evolution/components/EvolutionMethodologyStrip';
import MemberMobilityFlow from '../features/evolution/components/MemberMobilityFlow';
import PathThemeSimilarity from '../features/evolution/components/PathThemeSimilarity';
import PersistentPathTimeline from '../features/evolution/components/PersistentPathTimeline';
import SelectedPathContext from '../features/evolution/components/SelectedPathContext';
import { useCommunityEvolutionData } from '../features/evolution/useCommunityEvolutionData';
import { formatCount, formatPeriod } from '../features/overview/overviewUtils';

const EVOLUTION_SECTIONS = [
  { id: 'evolution-overview', label: 'Overview', icon: 'kpis' },
  { id: 'evolution-method', label: 'Methodology', icon: 'metadata' },
  { id: 'evolution-structure', label: 'Community Similarity', icon: 'continuity' },
  { id: 'evolution-mobility', label: 'Member Mobility', icon: 'actors' },
  { id: 'evolution-themes', label: 'Thematic Similarity', icon: 'themes' },
  { id: 'evolution-evidence', label: 'Evidence', icon: 'provenance' },
];

const THEME_TYPES = new Set(['general', 'absolute', 'weighted']);

function isArtifactUnavailable(error) {
  return Boolean(error) && normalizeApiError(error).code === 'ARTIFACT_NOT_AVAILABLE';
}

export default function CommunityEvolution() {
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedPathId = searchParams.get('path');
  const requestedThemeType = searchParams.get('themeView');
  const themeType = THEME_TYPES.has(requestedThemeType) ? requestedThemeType : 'general';
  const data = useCommunityEvolutionData(requestedPathId, themeType);
  const paths = data.pathsQuery.data?.paths ?? [];

  const selectedPath = useMemo(() => {
    if (paths.length === 0) return null;
    return paths.find((path) => path.path_id === requestedPathId) ?? paths[0];
  }, [paths, requestedPathId]);

  useEffect(() => {
    if (!selectedPath || requestedPathId === selectedPath.path_id) return;
    const next = new URLSearchParams(searchParams);
    next.set('path', selectedPath.path_id);
    setSearchParams(next, { replace: true });
  }, [requestedPathId, searchParams, selectedPath, setSearchParams]);

  const handlePathSelect = (pathId) => {
    const next = new URLSearchParams(searchParams);
    next.set('path', pathId);
    setSearchParams(next);
  };

  const handleThemeTypeChange = (nextThemeType) => {
    const next = new URLSearchParams(searchParams);
    next.set('themeView', nextThemeType);
    setSearchParams(next, { replace: true });
  };

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

  if (data.pathsQuery.isPending) {
    return <LoadingState title="Loading persistent community paths" />;
  }

  if (data.pathsQuery.error) {
    if (isArtifactUnavailable(data.pathsQuery.error)) {
      return (
        <ArtifactUnavailableState
          artifactName="Persistent community paths"
          message="This run predates the persisted Community Evolution path contract or did not generate its evolution artifacts. Re-run the theme/evolution stage with the updated pipeline."
        />
      );
    }
    return (
      <ErrorState
        error={data.pathsQuery.error}
        title="Community Evolution could not be loaded"
        onRetry={() => void data.pathsQuery.refetch()}
      />
    );
  }

  if (!data.pathsQuery.data) return null;

  const methodology = data.pathsQuery.data.methodology;
  const longestPath = paths.reduce((longest, path) => Math.max(longest, path.duration), 0);
  const averagePathJaccard = paths.length
    ? paths.reduce((sum, path) => sum + path.average_jaccard, 0) / paths.length
    : 0;
  const timelineMonths = Array.from(new Set(paths.flatMap((path) => path.months)))
    .sort((left, right) => left.localeCompare(right, undefined, { numeric: true }));
  const timelineCoverage = timelineMonths.length
    ? `${formatPeriod(timelineMonths[0])} → ${formatPeriod(timelineMonths[timelineMonths.length - 1])}`
    : 'No periods';

  return (
    <div className="mx-auto flex max-w-[1600px] items-start px-1 sm:px-2">
      <div className="min-w-0 flex-1 space-y-6 pb-16">
        <section id="evolution-overview" aria-labelledby="community-evolution-heading" className="scroll-mt-6" tabIndex={-1}>
          <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
            <div className="max-w-3xl">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">RQ3 · RQ4 longitudinal analysis</p>
              <h1 id="community-evolution-heading" className="mt-2 text-2xl font-bold text-text-heading sm:text-3xl">
                Community Evolution
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
                See the complete persistent-path landscape first, then inspect one lineage through structural
                continuity, member mobility, and thematic consistency.
              </p>
            </div>

            <label className="w-full text-xs font-semibold text-muted md:hidden sm:max-w-xs">
              Jump to section
              <select
                aria-label="Jump to Community Evolution section"
                defaultValue="evolution-overview"
                onChange={(event) => jumpToSection(event.target.value)}
                className="mt-1 w-full rounded-xl border border-border bg-surface px-3 py-2.5 text-sm font-semibold text-text-heading"
              >
                {EVOLUTION_SECTIONS.map((section) => <option key={section.id} value={section.id}>{section.label}</option>)}
              </select>
            </label>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="Persistent paths"
              value={formatCount(paths.length)}
              detail="Accepted start-to-end lineages"
              icon={GitBranch}
            />
            <MetricCard
              label="Longest path"
              value={`${longestPath || 0} mo`}
              detail="Maximum persisted duration"
              icon={Timer}
            />
            <MetricCard
              label="Average path Jaccard"
              value={averagePathJaccard.toFixed(2)}
              detail="Accepted path transitions"
              icon={Activity}
            />
            <MetricCard
              label="Timeline coverage"
              value={timelineCoverage}
              detail={`${formatCount(timelineMonths.length)} periods represented`}
              icon={CalendarRange}
              compactValue
            />
          </div>
        </section>

        <div id="evolution-method" className="scroll-mt-6" tabIndex={-1}>
          <EvolutionMethodologyStrip methodology={methodology} search={location.search} />
        </div>

        <section id="evolution-structure" className="panel scroll-mt-6 p-5" aria-labelledby="evolution-structure-heading" tabIndex={-1}>
          <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
            <SectionHeading
              eyebrow="1 · Structural continuity"
              title="Community Similarity over Time"
              description="See every persisted start-to-end community path together, then choose one lineage to carry through the membership and thematic detail views below."
            />
            <label className="w-full shrink-0 text-xs font-semibold text-muted sm:max-w-xs">
              Inspect persistent path
              <select
                aria-label="Inspect persistent path"
                value={selectedPath?.path_id ?? ''}
                onChange={(event) => handlePathSelect(event.target.value)}
                disabled={paths.length === 0}
                className="mt-1 w-full rounded-xl border border-border bg-surface px-3 py-2.5 text-sm font-semibold text-text-heading"
              >
                {paths.map((path) => (
                  <option key={path.path_id} value={path.path_id}>
                    Path {path.display_order} · {path.duration} months
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="mt-5">
            <PersistentPathTimeline
              paths={paths}
              selectedPathId={selectedPath?.path_id ?? null}
              onSelectPath={handlePathSelect}
            />
          </div>
          {selectedPath && <SelectedPathContext path={selectedPath} />}
        </section>

        <section id="evolution-mobility" className="panel scroll-mt-6 p-5" aria-labelledby="evolution-mobility-heading" tabIndex={-1}>
          <SectionHeading
            eyebrow="2 · Membership dynamics"
            title="Member Mobility"
            description="Track the same persistent path month by month to distinguish the stable core from newly joined, reappearing, and exiting members."
            context={selectedPath ? `Path ${selectedPath.display_order} · ${pathRange(selectedPath.months)}` : undefined}
          />
          <div className="mt-5">
            <OptionalQuery
              query={data.mobilityQuery}
              artifactName="Path member mobility"
              loadingTitle="Loading member mobility"
            >
              <MemberMobilityFlow records={data.mobilityQuery.data?.records ?? []} />
            </OptionalQuery>
          </div>
        </section>

        <section id="evolution-themes" className="panel scroll-mt-6 p-5" aria-labelledby="evolution-themes-heading" tabIndex={-1}>
          <SectionHeading
            eyebrow="3 · Semantic continuity"
            title="Thematic Similarity"
            description="Read the raw generated themes for this persistent path, then compare their sentence-embedding cosine similarity across months."
            context={selectedPath ? `Path ${selectedPath.display_order} · ${pathRange(selectedPath.months)}` : undefined}
          />
          <div className="mt-5">
            <OptionalQuery
              query={data.similarityQuery}
              artifactName="Path thematic similarity"
              loadingTitle="Loading thematic similarity"
            >
              {data.similarityQuery.data && (
                <PathThemeSimilarity
                  similarity={data.similarityQuery.data}
                  themeType={themeType}
                  onThemeTypeChange={handleThemeTypeChange}
                />
              )}
            </OptionalQuery>
          </div>
        </section>

        <section id="evolution-evidence" className="scroll-mt-6" aria-labelledby="evolution-evidence-heading" tabIndex={-1}>
          <h2 id="evolution-evidence-heading" className="sr-only">Analytical evidence</h2>
          {selectedPath && (
            <EvolutionEvidence path={selectedPath} mobility={data.mobilityQuery.data?.records ?? []} />
          )}
        </section>
      </div>

      <PageNavigationRailSlot sections={EVOLUTION_SECTIONS} />
    </div>
  );
}

function OptionalQuery({ query, artifactName, loadingTitle, children }) {
  if (query.isPending) return <LoadingState title={loadingTitle} />;
  if (query.error) {
    if (isArtifactUnavailable(query.error)) {
      return <ArtifactUnavailableState artifactName={artifactName} message={`${artifactName} was not generated for the selected run.`} />;
    }
    return <ErrorState error={query.error} title={`${artifactName} could not be loaded`} onRetry={() => void query.refetch()} />;
  }
  return children;
}

function MetricCard({ label, value, detail, icon: Icon, compactValue = false }) {
  return (
    <article className="rounded-2xl border border-border/70 bg-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold text-muted">{label}</p>
          <p className={`mt-1 font-bold text-text-heading ${compactValue ? 'text-lg' : 'text-2xl'}`}>{value}</p>
          <p className="mt-1 text-xs text-muted">{detail}</p>
        </div>
        <span className="shrink-0 rounded-xl bg-primary/10 p-2 text-primary"><Icon size={18} aria-hidden="true" /></span>
      </div>
    </article>
  );
}

function SectionHeading({ eyebrow, title, description, context }) {
  const headingId = title === 'Community Similarity over Time'
    ? 'evolution-structure-heading'
    : title === 'Member Mobility'
      ? 'evolution-mobility-heading'
      : 'evolution-themes-heading';
  return (
    <div className="flex max-w-4xl flex-col gap-2 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">{eyebrow}</p>
        <h2 id={headingId} className="mt-1 text-lg font-bold text-text-heading">{title}</h2>
        <p className="mt-1 text-sm leading-6 text-muted">{description}</p>
      </div>
      {context && (
        <span className="shrink-0 self-start rounded-full border border-primary/25 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
          {context}
        </span>
      )}
    </div>
  );
}

function pathRange(months) {
  if (!months || months.length === 0) return 'No periods';
  const first = formatPeriod(months[0]);
  const last = formatPeriod(months[months.length - 1]);
  return months.length === 1 ? first : `${first} → ${last}`;
}
