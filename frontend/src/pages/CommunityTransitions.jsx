import React, { useEffect } from 'react';
import { ChevronLeft, ChevronRight, Download, GitBranch, RefreshCcw, ShieldCheck, Users } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { getArtifactDownloadUrl } from '../api/reports';
import { normalizeApiError } from '../api/errors';
import SimilarityMatrix from '../components/SimilarityMatrix';
import MetricCard from '../components/MetricCard';
import TransitionsSankey from '../components/charts/TransitionsSankey';
import ArtifactUnavailableState from '../components/states/ArtifactUnavailableState';
import ErrorState from '../components/states/ErrorState';
import LoadingState from '../components/states/LoadingState';
import {
  downloadCsv,
  membershipChangesCsv,
  transitionCommonCount,
  transitionsCsv,
} from '../features/evolution/transitionModel';
import { useTransitionData } from '../features/evolution/useTransitionData';
import { formatCount } from '../features/overview/overviewUtils';
import { clampPageOffset, nextPageOffset, pageRange, previousPageOffset } from '../utils/pagination';

const TRANSITION_LIMIT = 200;
const TRANSITION_OFFSET_PARAM = 'transitionOffset';

export default function CommunityTransitionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedOffset = Number(searchParams.get(TRANSITION_OFFSET_PARAM) ?? 0);
  const transitionOffset = Number.isFinite(requestedOffset) && requestedOffset >= 0
    ? Math.floor(requestedOffset / TRANSITION_LIMIT) * TRANSITION_LIMIT
    : 0;
  const data = useTransitionData(TRANSITION_LIMIT, transitionOffset);
  const transitions = data.transitionsQuery.data?.records ?? [];
  const persistent = data.persistentQuery.data?.communities ?? [];
  const membership = data.membershipQuery.data?.records ?? [];
  const averageJaccard = transitions.length > 0
    ? transitions.reduce((sum, record) => sum + record.jaccard_score, 0) / transitions.length
    : null;
  const retained = membership.reduce((sum, record) => sum + record.retained_count, 0);
  const transitionTotal = data.transitionsQuery.data?.total ?? 0;
  const responseOffset = data.transitionsQuery.data?.offset ?? transitionOffset;
  const responseLimit = data.transitionsQuery.data?.limit ?? TRANSITION_LIMIT;

  const setTransitionOffset = (offset) => {
    const next = new URLSearchParams(searchParams);
    const safeOffset = Math.max(0, Math.floor(offset));
    if (safeOffset === 0) next.delete(TRANSITION_OFFSET_PARAM);
    else next.set(TRANSITION_OFFSET_PARAM, String(safeOffset));
    setSearchParams(next);
  };

  useEffect(() => {
    if (transitionTotal > 0 && responseOffset >= transitionTotal) {
      setTransitionOffset(clampPageOffset(responseOffset, transitionTotal, responseLimit));
    }
  // Search params are intentionally updated only when the server confirms an out-of-range page.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [transitionTotal, responseOffset, responseLimit]);

  return (
    <div className="flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
      <header className="panel p-5">
        <h1 className="text-xl font-bold text-text-heading">Community transitions and member mobility</h1>
        <p className="mt-1 max-w-4xl text-sm text-muted">
          Every panel reads a separate optional longitudinal artifact. A missing transition, membership, persistence, or similarity artifact does not prevent the other panels from rendering.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Transition records"
          value={data.transitionsQuery.data?.total ?? null}
          detail={`${transitions.length} records loaded on this page`}
          source="GET /runs/{run_id}/transitions"
          icon={GitBranch}
          colorClass="text-blue-500"
          bgClass="bg-blue-500"
          format={(value) => formatCount(value)}
        />
        <MetricCard
          title="Average Jaccard"
          value={averageJaccard}
          detail="Mean across loaded transition records"
          source="TransitionRecord.jaccard_score"
          icon={RefreshCcw}
          colorClass="text-purple-500"
          bgClass="bg-purple-500"
          format={(value) => Number(value).toFixed(3)}
        />
        <MetricCard
          title="Persistent community sets"
          value={data.persistentQuery.data?.total ?? null}
          detail="Connected transition components"
          source="GET /runs/{run_id}/persistent-communities"
          icon={ShieldCheck}
          colorClass="text-green-500"
          bgClass="bg-green-500"
          format={(value) => formatCount(value)}
        />
        <MetricCard
          title="Retained memberships"
          value={data.membershipQuery.data ? retained : null}
          detail="Sum of retained_count across available membership-change records"
          source="GET /runs/{run_id}/membership-changes"
          icon={Users}
          colorClass="text-orange-500"
          bgClass="bg-orange-500"
          format={(value) => formatCount(value)}
        />
      </div>

      <OptionalQueryPanel
        query={data.transitionsQuery}
        artifactName="Community transitions"
        loadingTitle="Loading transition records"
      >
        <TransitionsSankey records={transitions} maxLinks={60} />
      </OptionalQueryPanel>

      <section className="panel p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-sm font-bold text-text-heading">Transition records</h2>
            <p className="mt-1 text-xs text-muted">The table preserves the canonical start/end community IDs and member-overlap fields.</p>
          </div>
          {transitions.length > 0 && (
            <button
              type="button"
               onClick={() => downloadCsv(transitionsCsv(transitions), `${data.selectedRunId}-transitions-${responseOffset + 1}-${responseOffset + transitions.length}.csv`)}
               className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text-heading hover:bg-surface-soft"
             >
              <Download size={14} /> Export loaded transitions
            </button>
          )}
        </div>
        <OptionalQueryPanel
          query={data.transitionsQuery}
          artifactName="Community transitions"
          loadingTitle="Loading transition table"
          plain
        >
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-border text-xs text-muted">
                <tr>
                  <th className="px-3 py-3">Start</th>
                  <th className="px-3 py-3">End</th>
                  <th className="px-3 py-3">Jaccard</th>
                  <th className="px-3 py-3">Common members</th>
                  <th className="px-3 py-3">Start members</th>
                  <th className="px-3 py-3">End members</th>
                </tr>
              </thead>
              <tbody>
                {transitions.map((record, index) => (
                  <tr key={`${record.start_month}-${record.start_month_community}-${record.end_month}-${record.end_month_community}-${index}`} className="border-b border-border/40">
                    <td className="px-3 py-3 text-text-heading">{record.start_month} / {String(record.start_month_community)}</td>
                    <td className="px-3 py-3 text-text-heading">{record.end_month} / {String(record.end_month_community)}</td>
                    <td className="px-3 py-3 font-semibold text-text-heading">{record.jaccard_score.toFixed(3)}</td>
                    <td className="px-3 py-3 text-muted">{transitionCommonCount(record) ?? 'Unavailable'}</td>
                    <td className="px-3 py-3 text-muted">{record.total_start_month_members ?? 'Unavailable'}</td>
                    <td className="px-3 py-3 text-muted">{record.total_end_month_members ?? 'Unavailable'}</td>
                  </tr>
                ))}
                {transitions.length === 0 && <tr><td colSpan={6} className="px-3 py-8 text-center text-muted">No transition records.</td></tr>}
              </tbody>
            </table>
          </div>
          {data.transitionsQuery.data && (
            <div className="mt-4 flex flex-col gap-3 border-t border-border pt-4 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs text-muted">
                Showing {pageRange(responseOffset, responseLimit, transitionTotal)}. The Sankey and CSV export use this loaded page; the Sankey displays at most 60 links ranked by Jaccard within the page.
              </p>
              {transitionTotal > responseLimit && (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={responseOffset === 0}
                    onClick={() => setTransitionOffset(previousPageOffset(responseOffset, responseLimit))}
                    className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text-heading disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <ChevronLeft size={14} /> Previous
                  </button>
                  <button
                    type="button"
                    disabled={responseOffset + responseLimit >= transitionTotal}
                    onClick={() => setTransitionOffset(nextPageOffset(responseOffset, transitionTotal, responseLimit))}
                    className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text-heading disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Next <ChevronRight size={14} />
                  </button>
                </div>
              )}
            </div>
          )}
        </OptionalQueryPanel>
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <section className="panel p-5">
          <h2 className="text-sm font-bold text-text-heading">Persistent community sets</h2>
          <p className="mt-1 text-xs text-muted">Duration is represented by the number of distinct months in each transition component.</p>
          <OptionalQueryPanel query={data.persistentQuery} artifactName="Persistent communities" loadingTitle="Loading persistent communities" plain>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-border text-xs text-muted">
                  <tr><th className="px-3 py-3">Persistent ID</th><th className="px-3 py-3">Months</th><th className="px-3 py-3">Duration</th><th className="px-3 py-3">Transitions</th><th className="px-3 py-3">Average Jaccard</th></tr>
                </thead>
                <tbody>
                  {persistent.map((record) => (
                    <tr key={record.persistent_id} className="border-b border-border/40">
                      <td className="px-3 py-3 font-mono text-xs text-text-heading">{record.persistent_id}</td>
                      <td className="px-3 py-3 text-muted">{record.months.join(', ') || 'Unavailable'}</td>
                      <td className="px-3 py-3 text-text-heading">{record.months.length}</td>
                      <td className="px-3 py-3 text-text-heading">{record.transition_count}</td>
                      <td className="px-3 py-3 font-semibold text-text-heading">{record.average_jaccard.toFixed(3)}</td>
                    </tr>
                  ))}
                  {persistent.length === 0 && <tr><td colSpan={5} className="px-3 py-8 text-center text-muted">No persistent community sets.</td></tr>}
                </tbody>
              </table>
            </div>
          </OptionalQueryPanel>
        </section>

        <section className="panel p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-sm font-bold text-text-heading">Membership changes</h2>
              <p className="mt-1 text-xs text-muted">Only retained, joined, exited, start, and end counts exposed by the API are shown.</p>
            </div>
            {membership.length > 0 && (
              <button
                type="button"
                 onClick={() => downloadCsv(membershipChangesCsv(membership), `${data.selectedRunId}-membership-changes.csv`)}
                 className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text-heading hover:bg-surface-soft"
               >
                <Download size={14} /> Export membership changes
              </button>
            )}
          </div>
          <OptionalQueryPanel query={data.membershipQuery} artifactName="Membership changes" loadingTitle="Loading membership changes" plain>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-border text-xs text-muted">
                  <tr><th className="px-3 py-3">Transition</th><th className="px-3 py-3">Retained</th><th className="px-3 py-3">Joined</th><th className="px-3 py-3">Exited</th><th className="px-3 py-3">Start → end</th></tr>
                </thead>
                <tbody>
                  {membership.map((record, index) => (
                    <tr key={`${record.start_month}-${record.start_community}-${record.end_month}-${record.end_community}-${index}`} className="border-b border-border/40">
                      <td className="px-3 py-3 text-text-heading">{record.start_month}:{record.start_community} → {record.end_month}:{record.end_community}</td>
                      <td className="px-3 py-3 text-text-heading">{record.retained_count}</td>
                      <td className="px-3 py-3 text-text-heading">{record.joined_count}</td>
                      <td className="px-3 py-3 text-text-heading">{record.exited_count}</td>
                      <td className="px-3 py-3 text-muted">{record.start_count} → {record.end_count}</td>
                    </tr>
                  ))}
                  {membership.length === 0 && <tr><td colSpan={5} className="px-3 py-8 text-center text-muted">No membership-change records.</td></tr>}
                </tbody>
              </table>
            </div>
          </OptionalQueryPanel>
        </section>
      </div>

      <section className="panel p-5">
        <h2 className="text-sm font-bold text-text-heading">Theme similarity</h2>
        <p className="mt-1 text-xs text-muted">Cosine-similarity values and visualization artifacts are read from the selected run; no embeddings are computed in the browser.</p>
        <OptionalQueryPanel query={data.similarityQuery} artifactName="Theme similarity" loadingTitle="Loading theme similarity" plain>
          <div className="mt-4">
            {data.similarityQuery.data?.matrix && data.similarityQuery.data.labels.length > 0 ? (
              <SimilarityMatrix matrix={data.similarityQuery.data.matrix} labels={data.similarityQuery.data.labels} />
            ) : (
              <div className="flex flex-wrap gap-2">
                {(data.similarityQuery.data?.artifacts ?? []).map((artifact) => (
                  <a
                    key={artifact.artifact_key}
                    href={getArtifactDownloadUrl(data.selectedRunId, artifact.artifact_key)}
                    className="rounded-lg border border-border px-3 py-2 text-sm font-medium text-primary hover:bg-surface-soft"
                  >
                    Open {artifact.path}
                  </a>
                ))}
              </div>
            )}
          </div>
        </OptionalQueryPanel>
      </section>
    </div>
  );
}

function OptionalQueryPanel({ query, artifactName, loadingTitle, children, plain = false }) {
  if (query.isPending) return plain ? <div className="mt-4"><LoadingState title={loadingTitle} /></div> : <LoadingState title={loadingTitle} />;
  if (query.error) {
    const normalized = normalizeApiError(query.error);
    if (normalized.code === 'ARTIFACT_NOT_AVAILABLE' || normalized.code === 'ARTIFACT_MISSING') {
      return <div className={plain ? 'mt-4' : ''}><ArtifactUnavailableState artifactName={artifactName} message={`${artifactName} was not generated for the selected run.`} /></div>;
    }
    return <div className={plain ? 'mt-4' : ''}><ErrorState error={query.error} title={`${artifactName} could not be loaded`} onRetry={() => void query.refetch()} /></div>;
  }
  return children;
}
