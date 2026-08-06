import React from 'react';
import { useState } from 'react';
import { Database, Download, FileText, Search, ShieldCheck } from 'lucide-react';
import { getArtifactDownloadUrl, getReportUrl } from '../api/reports';
import ArtifactStatusBadge from '../components/ArtifactStatusBadge';
import EmptyState from '../components/states/EmptyState';
import ErrorState from '../components/states/ErrorState';
import LoadingState from '../components/states/LoadingState';
import {
  artifactFilterOptions,
  filterArtifacts,
  groupArtifactCounts,
  hasInlineReport,
  isDownloadableArtifact,
} from '../features/reports/artifactLibrary';
import { useArtifactLibrary } from '../features/reports/useArtifactLibrary';
import { formatBytes, formatCount } from '../features/overview/overviewUtils';

export default function ReportsPage() {
  const data = useArtifactLibrary();
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [stage, setStage] = useState('');
  const [mediaType, setMediaType] = useState('');
  const artifacts = data.artifactsQuery.data?.artifacts ?? [];
  const options = artifactFilterOptions(artifacts);
  const filtered = filterArtifacts(artifacts, { query, category, stage, mediaType });
  const counts = groupArtifactCounts(artifacts);
  const inlineReportAvailable = hasInlineReport(artifacts);

  if (data.artifactsQuery.isPending) {
    return <LoadingState title="Loading artifact library" />;
  }
  if (data.artifactsQuery.error) {
    return <ErrorState error={data.artifactsQuery.error} title="Artifact library could not be loaded" onRetry={() => void data.artifactsQuery.refetch()} />;
  }

  return (
    <div className="flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
      <header className="panel p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-xl font-bold text-text-heading">Read-only artifact library</h1>
            <p className="mt-1 max-w-3xl text-sm text-muted">
              This dashboard does not create, schedule, edit, delete, or share reports. It lists verified artifacts already produced by the selected run.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <ArtifactStatusBadge
              label={data.verification?.ok ? 'Run verified' : 'Verification unavailable'}
              status={data.verification?.ok ? 'verified' : 'warning'}
            />
            {inlineReportAvailable && (
              <a
                href={getReportUrl(data.selectedRunId)}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90"
              >
                <FileText size={16} /> Open report
              </a>
            )}
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard label="All artifacts" value={artifacts.length} icon={Database} />
        <SummaryCard label="Data artifacts" value={counts.data ?? 0} icon={FileText} />
        <SummaryCard label="Report artifacts" value={counts.report ?? 0} icon={Download} />
        <SummaryCard label="Intermediate artifacts" value={counts.intermediate ?? 0} icon={ShieldCheck} detail="Listed but not downloadable" />
      </div>

      <section className="panel">
        <div className="border-b border-border p-5">
          <h2 className="text-lg font-bold text-text-heading">Artifacts for {data.selectedRunId}</h2>
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
            <label className="text-xs font-medium text-muted">
              Search metadata
              <span className="relative mt-1 block">
                <Search size={15} className="pointer-events-none absolute left-3 top-2.5 text-muted" />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Key, path, category..."
                  className="w-full rounded-lg border border-border bg-bg py-2 pl-9 pr-3 text-sm text-text-heading"
                />
              </span>
            </label>
            <FilterSelect label="Category" value={category} values={options.categories} onChange={setCategory} />
            <FilterSelect label="Stage" value={stage} values={options.stages} onChange={setStage} />
            <FilterSelect label="Media type" value={mediaType} values={options.mediaTypes} onChange={setMediaType} />
          </div>
          <p className="mt-3 text-xs text-muted">Showing {filtered.length} of {artifacts.length} manifest-listed artifacts.</p>
        </div>

        {artifacts.length === 0 ? (
          <div className="p-5"><EmptyState title="No artifacts listed" message="The selected completed run manifest contains no artifacts." /></div>
        ) : filtered.length === 0 ? (
          <div className="p-5"><EmptyState title="No artifacts match these filters" message="Adjust the metadata filters to see available records." /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
               <thead className="border-b border-border bg-surface-soft/40 text-xs text-muted">
                <tr>
                  <th className="px-5 py-4">Artifact</th>
                  <th className="px-4 py-4">Category</th>
                  <th className="px-4 py-4">Media type</th>
                  <th className="px-4 py-4">Schema</th>
                  <th className="px-4 py-4">Stage</th>
                  <th className="px-4 py-4">Rows</th>
                  <th className="px-4 py-4">Bytes</th>
                  <th className="px-5 py-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((artifact) => (
                   <tr key={artifact.key} className="border-b border-border/40 align-top hover:bg-surface-soft/30">
                    <td className="px-5 py-4">
                      <p className="font-semibold text-text-heading">{artifact.key}</p>
                      <p className="mt-1 max-w-md break-all font-mono text-[11px] text-muted">{artifact.path}</p>
                    </td>
                    <td className="px-4 py-4"><span className="rounded-full border border-border px-2 py-1 text-xs text-text-heading">{artifact.category}</span></td>
                    <td className="px-4 py-4 text-muted">{artifact.media_type}</td>
                    <td className="px-4 py-4 text-muted">{artifact.schema_version}</td>
                    <td className="px-4 py-4 text-muted">{artifact.stage ?? 'Unavailable'}</td>
                    <td className="px-4 py-4 text-text-heading">{artifact.rows === null ? 'Unavailable' : formatCount(artifact.rows)}</td>
                    <td className="px-4 py-4 text-text-heading">{formatBytes(artifact.byte_size)}</td>
                    <td className="px-5 py-4 text-right">
                      {isDownloadableArtifact(artifact) ? (
                        <a
                          href={getArtifactDownloadUrl(data.selectedRunId, artifact.key)}
                           className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs font-semibold text-primary hover:bg-surface-soft"
                        >
                          <Download size={14} /> Download
                        </a>
                      ) : (
                        <span className="text-xs text-muted" title="Intermediate artifacts are intentionally unavailable through the download endpoint.">Not downloadable</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel p-5">
        <h2 className="text-sm font-bold text-text-heading">Verification and download behavior</h2>
        <p className="mt-2 text-sm text-muted">
          The application-level verification gate prevents analytical routes from opening when a manifest or artifact fails validation. File links use the backend's native inline-report and manifest-key download endpoints so media type and content disposition remain server-controlled.
        </p>
      </section>
    </div>
  );
}

function SummaryCard({ label, value, icon: Icon, detail }) {
  return (
    <article className="panel p-5">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon size={20} /></div>
        <div>
          <p className="text-xs font-medium text-muted">{label}</p>
          <p className="text-2xl font-bold text-text-heading">{formatCount(value)}</p>
          {detail && <p className="mt-1 text-[11px] text-muted">{detail}</p>}
        </div>
      </div>
    </article>
  );
}

function FilterSelect({ label, value, values, onChange }) {
  return (
    <label className="text-xs font-medium text-muted">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-heading"
      >
        <option value="">All</option>
        {values.map((item) => <option key={item} value={item}>{item}</option>)}
      </select>
    </label>
  );
}
