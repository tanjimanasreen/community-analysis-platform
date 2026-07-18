import React, { useEffect, useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, Database, Download, ExternalLink, Search, X } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { normalizeApiError } from '../api/errors';
import { getArtifactDownloadUrl } from '../api/reports';
import ArtifactUnavailableState from '../components/states/ArtifactUnavailableState';
import ErrorState from '../components/states/ErrorState';
import LoadingState from '../components/states/LoadingState';
import {
  EXPLORER_MODES,
  explorerColumns,
  filterLoadedPage,
  isArtifactDownloadable,
  modeSupportsExactCommunitySearch,
  navigationCommunityId,
  recordKey,
  safeDisplayValue,
} from '../features/explorer/explorerModel';
import { useExplorerData } from '../features/explorer/useExplorerData';
import { updateNetworkSearchParams } from '../features/networks/networkModel';
import { nextPageOffset, pageRange, previousPageOffset } from '../utils/pagination';

const DEFAULT_LIMIT = 25;

export default function DataExplorerPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState('communities');
  const [offsets, setOffsets] = useState(() => Object.fromEntries(EXPLORER_MODES.map((item) => [item.id, 0])));
  const [searchDraft, setSearchDraft] = useState('');
  const [search, setSearch] = useState('');
  const [selectedRecord, setSelectedRecord] = useState(null);
  const limit = DEFAULT_LIMIT;
  const offset = offsets[mode] ?? 0;
  const data = useExplorerData({ mode, offset, limit, search });
  const { selectedRunId, metric, query, page, exactCommunitySearch } = data;
  const columns = explorerColumns(mode);
  const records = useMemo(
    () => (exactCommunitySearch ? page?.records ?? [] : filterLoadedPage(page?.records ?? [], search)),
    [exactCommunitySearch, page?.records, search],
  );
  const error = query.error ? normalizeApiError(query.error) : null;

  useEffect(() => {
    if (!page || page.total === 0 || page.offset < page.total) return;
    const lastOffset = Math.floor((page.total - 1) / page.limit) * page.limit;
    setOffsets((current) => ({ ...current, [mode]: lastOffset }));
  }, [mode, page]);

  const changeMode = (nextMode) => {
    setMode(nextMode);
    setSelectedRecord(null);
    setSearch('');
    setSearchDraft('');
  };
  const setOffset = (nextOffset) => {
    setOffsets((current) => ({ ...current, [mode]: Math.max(0, nextOffset) }));
    setSelectedRecord(null);
  };
  const applySearch = (event) => {
    event.preventDefault();
    setSearch(searchDraft.trim());
    setOffset(0);
    setSelectedRecord(null);
  };
  const clearSearch = () => {
    setSearchDraft('');
    setSearch('');
    setOffset(0);
  };

  return (
    <div data-run-id={selectedRunId || undefined} className="grid grid-cols-1 gap-4 max-w-[1800px] mx-auto w-full xl:grid-cols-[230px_minmax(0,1fr)_320px] items-start">
      <aside className="rounded-xl border border-border bg-panel p-4 xl:sticky xl:top-24">
        <div className="flex items-center gap-2">
          <Database size={17} className="text-primary" />
          <h1 className="text-sm font-bold text-text-heading">Artifact Explorer</h1>
        </div>
        <p className="mt-2 text-xs text-muted">Read-only records from the selected canonical run.</p>

        <nav className="mt-5 flex flex-col gap-1" aria-label="Explorer data modes">
          {EXPLORER_MODES.map((item) => (
            <button
              type="button"
              key={item.id}
              onClick={() => changeMode(item.id)}
              className={`rounded-lg px-3 py-2 text-left text-xs font-semibold transition-colors ${mode === item.id ? 'bg-primary/10 text-primary' : 'text-muted hover:bg-panel-soft hover:text-text-heading'}`}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <form onSubmit={applySearch} className="mt-5 border-t border-border pt-5">
          <label className="text-xs font-semibold text-text-heading" htmlFor="explorer-search">
            {modeSupportsExactCommunitySearch(mode) ? 'Exact community ID' : 'Filter this page'}
          </label>
          <div className="relative mt-2">
            <Search size={14} className="pointer-events-none absolute left-3 top-2.5 text-muted" />
            <input
              id="explorer-search"
              value={searchDraft}
              onChange={(event) => setSearchDraft(event.target.value)}
              placeholder={modeSupportsExactCommunitySearch(mode) ? 'Community ID' : 'Text in loaded records'}
              className="w-full rounded-lg border border-border bg-bg py-2 pl-9 pr-3 text-xs text-text-heading"
            />
          </div>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <button type="submit" className="rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white hover:bg-primary/90">Apply</button>
            <button type="button" onClick={clearSearch} className="rounded-lg border border-border px-3 py-2 text-xs font-semibold text-muted hover:bg-panel-soft">Clear</button>
          </div>
          <p className="mt-2 text-[11px] text-muted">
            {modeSupportsExactCommunitySearch(mode)
              ? 'This endpoint applies an exact server-side community filter.'
              : 'This filter checks only the records loaded on the current page.'}
          </p>
        </form>
      </aside>

      <main className="min-w-0 rounded-xl border border-border bg-panel overflow-hidden">
        <div className="flex flex-col gap-2 border-b border-border px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-bold text-text-heading">{EXPLORER_MODES.find((item) => item.id === mode)?.label}</h2>
            <p className="mt-1 text-xs text-muted">Selected metric: {metric.toUpperCase()}</p>
          </div>
          <span className="text-xs text-muted">{pageRange(page?.offset ?? offset, page?.limit ?? limit, page?.total ?? 0)}</span>
        </div>

        {query.isPending ? (
          <div className="p-5"><LoadingState title="Loading artifact records" /></div>
        ) : error?.code === 'ARTIFACT_NOT_AVAILABLE' ? (
          <div className="p-5"><ArtifactUnavailableState artifactName={mode} message={error.message} /></div>
        ) : query.error ? (
          <div className="p-5"><ErrorState error={query.error} title="Explorer records could not be loaded" onRetry={() => void query.refetch()} /></div>
        ) : records.length === 0 ? (
          <div className="p-10 text-center" aria-live="polite">
            <h3 className="font-semibold text-text-heading">No records available</h3>
            <p className="mt-2 text-sm text-muted">No canonical records match this mode, page, and filter.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border bg-panel-soft/40 text-muted">
                  {columns.map((column) => <th key={column.key} className="px-4 py-3 font-semibold">{column.label}</th>)}
                </tr>
              </thead>
              <tbody>
                {records.map((record, index) => {
                  const key = recordKey(record, index);
                  return (
                    <tr
                      key={key}
                      onClick={() => setSelectedRecord(record)}
                      className={`cursor-pointer border-b border-border/40 align-top hover:bg-panel-soft/40 ${selectedRecord === record ? 'bg-primary/10' : ''}`}
                    >
                      {columns.map((column) => (
                        <td key={column.key} className="max-w-xs px-4 py-3 text-muted">
                          <span className="line-clamp-3 whitespace-pre-wrap break-words">{safeDisplayValue(record[column.key])}</span>
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex items-center justify-end gap-2 border-t border-border px-5 py-3">
          <button
            type="button"
            aria-label="Previous explorer page"
            disabled={(page?.offset ?? offset) <= 0}
            onClick={() => setOffset(previousPageOffset(page?.offset ?? offset, limit))}
            className="rounded-md border border-border p-1.5 text-muted hover:bg-panel-soft disabled:opacity-40"
          >
            <ChevronLeft size={15} />
          </button>
          <button
            type="button"
            aria-label="Next explorer page"
            disabled={(page?.offset ?? offset) + (page?.limit ?? limit) >= (page?.total ?? 0)}
            onClick={() => setOffset(nextPageOffset(page?.offset ?? offset, page?.total ?? 0, limit))}
            className="rounded-md border border-border p-1.5 text-muted hover:bg-panel-soft disabled:opacity-40"
          >
            <ChevronRight size={15} />
          </button>
        </div>
      </main>

      <RecordDetails
        record={selectedRecord}
        mode={mode}
        metric={metric}
        runId={selectedRunId}
        onClose={() => setSelectedRecord(null)}
        onViewNetwork={(record) => {
          const communityId = navigationCommunityId(record, metric);
          if (!communityId) return;
          const params = updateNetworkSearchParams(new URLSearchParams(location.search), { communityId });
          navigate(`/network?${params.toString()}`);
        }}
      />
    </div>
  );
}

function RecordDetails({ record, mode, metric, runId, onClose, onViewNetwork }) {
  if (!record) {
    return (
      <aside className="rounded-xl border border-border bg-panel p-6 xl:sticky xl:top-24">
        <h2 className="font-semibold text-text-heading">Record details</h2>
        <p className="mt-2 text-sm text-muted">Select a row to inspect its normalized values and related actions.</p>
      </aside>
    );
  }

  const communityId = navigationCommunityId(record, metric);
  const downloadable = mode === 'artifacts' && isArtifactDownloadable(record);
  const downloadUrl = downloadable && typeof record.key === 'string'
    ? getArtifactDownloadUrl(runId, record.key)
    : null;

  return (
    <aside className="rounded-xl border border-border bg-panel p-5 xl:sticky xl:top-24 xl:max-h-[calc(100vh-120px)] xl:overflow-y-auto">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-text-heading">Normalized record</h2>
          <p className="mt-1 text-xs text-muted">Values are rendered safely without evaluating artifact text.</p>
        </div>
        <button type="button" aria-label="Close record details" onClick={onClose} className="rounded p-1 text-muted hover:bg-panel-soft"><X size={15} /></button>
      </div>

      <dl className="mt-5 space-y-3">
        {Object.entries(record).map(([key, value]) => (
          <div key={key} className="rounded-lg border border-border/70 bg-bg/30 p-3">
            <dt className="text-[11px] font-semibold text-muted">{key}</dt>
            <dd className="mt-1 whitespace-pre-wrap break-words text-xs text-text-heading">{safeDisplayValue(value)}</dd>
          </div>
        ))}
      </dl>

      {communityId && (
        <button
          type="button"
          onClick={() => onViewNetwork(record)}
          className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary/10 px-3 py-2 text-xs font-semibold text-primary hover:bg-primary/15"
        >
          View {metric.toUpperCase()} community {communityId} <ExternalLink size={13} />
        </button>
      )}

      {mode === 'artifacts' && (
        downloadUrl ? (
          <a
            href={downloadUrl}
            className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text-heading hover:bg-panel-soft"
          >
            <Download size={13} /> Download verified artifact
          </a>
        ) : (
          <p className="mt-3 rounded-lg border border-border bg-panel-soft/40 p-3 text-xs text-muted">Intermediate artifacts are not downloadable through the read-only API.</p>
        )
      )}
    </aside>
  );
}
