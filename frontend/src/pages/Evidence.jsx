import React, { useEffect, useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useLocation, useSearchParams } from 'react-router-dom';
import { normalizeApiError } from '../api/errors';
import ArtifactValue from '../components/ArtifactValue';
import ArtifactUnavailableState from '../components/states/ArtifactUnavailableState';
import EmptyState from '../components/states/EmptyState';
import ErrorState from '../components/states/ErrorState';
import LoadingState from '../components/states/LoadingState';
import EvidenceContextHeader from '../features/evidence/EvidenceContextHeader';
import EvidenceNavigator from '../features/evidence/EvidenceNavigator';
import EvidenceRecordDetails from '../features/evidence/EvidenceRecordDetails';
import RunOutputs from '../features/evidence/RunOutputs';
import {
  EVIDENCE_VIEW_PARAM,
  EVIDENCE_VIEWS,
  evidenceColumns,
  recordKey,
  resolveEvidenceView,
} from '../features/evidence/evidenceModel';
import { useEvidenceData } from '../features/evidence/useEvidenceData';
import { nextPageOffset, pageRange, previousPageOffset } from '../utils/pagination';

const DEFAULT_LIMIT = 25;

export default function EvidencePage() {
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedView = searchParams.get(EVIDENCE_VIEW_PARAM);
  const view = resolveEvidenceView(requestedView);
  const [offsets, setOffsets] = useState(() => Object.fromEntries(
    Object.keys(EVIDENCE_VIEWS).map((key) => [key, 0]),
  ));
  const [communitySearchDraft, setCommunitySearchDraft] = useState('');
  const [communitySearch, setCommunitySearch] = useState('');
  const [selectedRecord, setSelectedRecord] = useState(null);
  const limit = DEFAULT_LIMIT;
  const offset = offsets[view] ?? 0;
  const data = useEvidenceData({ view, offset, limit, communitySearch });
  const definition = data.definition;
  const columns = evidenceColumns(view);
  const page = data.page;
  const records = page?.records ?? [];
  const error = data.query.error ? normalizeApiError(data.query.error) : null;

  useEffect(() => {
    if (requestedView === view) return;
    const next = new URLSearchParams(searchParams);
    next.set(EVIDENCE_VIEW_PARAM, view);
    setSearchParams(next, { replace: true });
  }, [requestedView, searchParams, setSearchParams, view]);

  useEffect(() => {
    setSelectedRecord(null);
  }, [view, data.selectedPeriod, data.metric, communitySearch]);

  useEffect(() => {
    setOffsets(Object.fromEntries(Object.keys(EVIDENCE_VIEWS).map((key) => [key, 0])));
    setCommunitySearch('');
    setCommunitySearchDraft('');
    setSelectedRecord(null);
  }, [data.selectedRunId]);

  useEffect(() => {
    if (!page || page.total === 0 || page.offset < page.total) return;
    const lastOffset = Math.floor((page.total - 1) / page.limit) * page.limit;
    setOffsets((current) => ({ ...current, [view]: lastOffset }));
  }, [page, view]);

  const changeView = (nextView) => {
    const next = new URLSearchParams(searchParams);
    next.set(EVIDENCE_VIEW_PARAM, nextView);
    setSearchParams(next);
    setSelectedRecord(null);
    setCommunitySearch('');
    setCommunitySearchDraft('');
  };

  const setOffset = (nextOffset) => {
    setOffsets((current) => ({ ...current, [view]: Math.max(0, nextOffset) }));
    setSelectedRecord(null);
  };

  const applyCommunitySearch = () => {
    setCommunitySearch(communitySearchDraft.trim());
    setOffset(0);
  };

  const clearCommunitySearch = () => {
    setCommunitySearchDraft('');
    setCommunitySearch('');
    setOffset(0);
  };

  const destination = useMemo(
    () => evidenceDestination(view, location.search, data.selectedPeriod, data.metric),
    [data.metric, data.selectedPeriod, location.search, view],
  );

  const monthlyUnavailable = definition.requiresPeriod
    && !data.overviewQuery.isPending
    && !data.overviewQuery.error
    && data.periods.length === 0;

  return (
    <div
      data-run-id={data.selectedRunId || undefined}
      className="mx-auto w-full max-w-[1800px] space-y-4"
    >
      <EvidenceNavigator
        view={view}
        onViewChange={changeView}
        communitySearchDraft={communitySearchDraft}
        onCommunitySearchDraftChange={setCommunitySearchDraft}
        onApplyCommunitySearch={applyCommunitySearch}
        onClearCommunitySearch={clearCommunitySearch}
      />

      <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="panel min-w-0 overflow-hidden" aria-label="Analytical records">
        <EvidenceContextHeader
          definition={definition}
          periods={data.periods}
          selectedPeriod={data.selectedPeriod}
          onPeriodChange={(period) => {
            setOffset(0);
            setSelectedRecord(null);
            data.setSelectedPeriod(period);
          }}
          metric={data.metric}
          onMetricChange={(metric) => {
            setOffset(0);
            setSelectedRecord(null);
            data.setMetric(metric);
          }}
          destinationHref={destination?.href ?? null}
          destinationLabel={destination?.label ?? null}
        />

        {view === 'outputs' ? (
          data.artifactsQuery.isPending ? (
            <div className="p-5"><LoadingState title="Loading run outputs" /></div>
          ) : data.artifactsQuery.error ? (
            <div className="p-5"><ErrorState error={data.artifactsQuery.error} title="Run outputs could not be loaded" onRetry={() => void data.artifactsQuery.refetch()} /></div>
          ) : (
            <RunOutputs
              runId={data.selectedRunId}
              verification={data.verification}
              artifacts={data.artifactsQuery.data?.artifacts ?? []}
              selectedKey={typeof selectedRecord?.key === 'string' ? selectedRecord.key : null}
              onSelect={(artifact) => setSelectedRecord({ ...artifact })}
            />
          )
        ) : definition.requiresPeriod && data.overviewQuery.isPending ? (
          <div className="p-5"><LoadingState title="Loading available data periods" /></div>
        ) : definition.requiresPeriod && data.overviewQuery.error ? (
          <div className="p-5"><ErrorState error={data.overviewQuery.error} title="Data periods could not be loaded" onRetry={() => void data.overviewQuery.refetch()} /></div>
        ) : monthlyUnavailable ? (
          <div className="p-5"><EmptyState title="No monthly data snapshots" message="The selected run does not publish monthly periods for this data view." /></div>
        ) : data.query.isPending ? (
          <div className="p-5"><LoadingState title="Loading research data" /></div>
        ) : error?.code === 'ARTIFACT_NOT_AVAILABLE' ? (
          <div className="p-5"><ArtifactUnavailableState artifactName={definition.label} message={error.message} /></div>
        ) : data.query.error ? (
          <div className="p-5"><ErrorState error={data.query.error} title="Data records could not be loaded" onRetry={() => void data.query.refetch()} /></div>
        ) : records.length === 0 ? (
          <div className="p-10 text-center" aria-live="polite">
            <h3 className="font-semibold text-text-heading">No data records available</h3>
            <p className="mt-2 text-sm text-muted">No persisted records match the selected data scope.</p>
          </div>
        ) : (
          <EvidenceTable
            records={records}
            columns={columns}
            selectedRecord={selectedRecord}
            onSelect={setSelectedRecord}
          />
        )}

        {view !== 'outputs' && definition.paginated && (
          <div className="flex items-center justify-between gap-3 border-t border-border px-5 py-3">
            <span className="text-xs text-muted">{pageRange(page?.offset ?? offset, page?.limit ?? limit, page?.total ?? 0)}</span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                aria-label="Previous data page"
                disabled={(page?.offset ?? offset) <= 0}
                onClick={() => setOffset(previousPageOffset(page?.offset ?? offset, limit))}
                className="rounded-md border border-border p-1.5 text-muted hover:bg-surface-soft disabled:opacity-40"
              >
                <ChevronLeft size={15} />
              </button>
              <button
                type="button"
                aria-label="Next data page"
                disabled={(page?.offset ?? offset) + (page?.limit ?? limit) >= (page?.total ?? 0)}
                onClick={() => setOffset(nextPageOffset(page?.offset ?? offset, page?.total ?? 0, limit))}
                className="rounded-md border border-border p-1.5 text-muted hover:bg-surface-soft disabled:opacity-40"
              >
                <ChevronRight size={15} />
              </button>
            </div>
          </div>
        )}
        </section>

        <EvidenceRecordDetails
          record={selectedRecord}
          view={view}
          metric={data.metric}
          period={data.selectedPeriod}
          runId={data.selectedRunId}
          currentSearch={location.search}
          communitySearch={communitySearch}
          onClose={() => setSelectedRecord(null)}
        />
      </div>
    </div>
  );
}

function EvidenceTable({ records, columns, selectedRecord, onSelect }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-xs">
        <thead>
          <tr className="border-b border-border bg-surface-soft/40 text-muted">
            {columns.map((column) => <th key={column.key} className="px-4 py-3 font-semibold">{column.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {records.map((record, index) => {
            const key = recordKey(record, index);
            return (
              <tr
                key={key}
                tabIndex={0}
                onClick={() => onSelect(record)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    onSelect(record);
                  }
                }}
                className={`cursor-pointer border-b border-border/40 align-top hover:bg-surface-soft/40 ${selectedRecord === record ? 'bg-primary/10' : ''}`}
              >
                {columns.map((column) => (
                  <td key={column.key} className="max-w-xs px-4 py-3 text-muted">
                    <ArtifactValue value={record[column.key]} compact />
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function evidenceDestination(view, currentSearch, period, metric) {
  const params = new URLSearchParams(currentSearch);
  params.delete(EVIDENCE_VIEW_PARAM);

  switch (view) {
    case 'communities':
      if (period) params.set('period', period);
      params.set('metric', metric);
      params.delete('community');
      return { href: `/communities?${params.toString()}`, label: 'Open Communities analysis' };
    case 'centrality':
      if (period) params.set('period', period);
      params.set('metric', metric);
      return { href: `/?${params.toString()}`, label: 'Open Overview structural context' };
    case 'matched-lda':
    case 'partial-lda':
      if (period) params.set('period', period);
      params.set('topicType', view === 'partial-lda' ? 'partial' : 'matched');
      return { href: `/thematic?${params.toString()}`, label: 'Open Thematic Analysis' };
    case 'themes':
      if (period) params.set('period', period);
      return { href: `/thematic?${params.toString()}`, label: 'Open Thematic Analysis' };
    case 'transitions':
      params.delete('period');
      return { href: `/evolution?${params.toString()}`, label: 'Open Community Evolution' };
    case 'outputs':
      return { href: `/run-history?${params.toString()}`, label: 'Open Run History' };
  }
}
