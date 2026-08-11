import { Database, Download, FileText, Search, ShieldCheck } from 'lucide-react';
import { useMemo, useState } from 'react';
import { getArtifactDownloadUrl, getReportUrl } from '../../api/reports';
import ArtifactStatusBadge from '../../components/ArtifactStatusBadge';
import EmptyState from '../../components/states/EmptyState';
import type { ArtifactMetadata, VerificationResponse } from '../../types/api';
import {
  artifactFilterOptions,
  filterArtifacts,
  hasInlineReport,
  isDownloadableArtifact,
} from '../reports/artifactLibrary';
import { formatBytes, formatCount } from '../overview/overviewUtils';

interface RunOutputsProps {
  runId: string;
  verification: VerificationResponse | null;
  artifacts: ArtifactMetadata[];
  selectedKey: string | null;
  onSelect: (artifact: ArtifactMetadata) => void;
}

interface OutputGroup {
  id: 'published' | 'data' | 'provenance';
  label: string;
  description: string;
  icon: typeof FileText;
  artifacts: ArtifactMetadata[];
}

export default function RunOutputs({
  runId,
  verification,
  artifacts,
  selectedKey,
  onSelect,
}: RunOutputsProps) {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [stage, setStage] = useState('');
  const [mediaType, setMediaType] = useState('');
  const options = artifactFilterOptions(artifacts);
  const filtered = filterArtifacts(artifacts, { query, category, stage, mediaType });
  const inlineReportAvailable = hasInlineReport(artifacts);
  const groups = useMemo(() => groupOutputs(filtered), [filtered]);

  return (
    <div>
      <div className="border-b border-border p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="max-w-3xl text-sm leading-6 text-muted">
            Filter manifest-listed outputs below. Intermediate artifacts remain inspectable for provenance but are not downloadable.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <ArtifactStatusBadge
              label={verification?.ok ? 'Run verified' : 'Verification unavailable'}
              status={verification?.ok ? 'verified' : 'warning'}
            />
            {inlineReportAvailable && (
              <a
                href={getReportUrl(runId)}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white hover:bg-primary/90"
              >
                <FileText size={14} aria-hidden="true" /> Open report
              </a>
            )}
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 2xl:grid-cols-4">
          <label className="text-xs font-medium text-muted">
            Search metadata
            <span className="relative mt-1 block">
              <Search size={15} className="pointer-events-none absolute left-3 top-2.5 text-muted" aria-hidden="true" />
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
        <div className="divide-y divide-border">
          {groups.map((group) => {
            const GroupIcon = group.icon;
            return (
              <section key={group.id} aria-labelledby={`output-group-${group.id}`}>
                <div className="flex items-start gap-3 bg-surface-soft/35 px-5 py-3">
                  <GroupIcon size={16} className="mt-0.5 text-primary" aria-hidden="true" />
                  <div>
                    <h4 id={`output-group-${group.id}`} className="text-xs font-bold text-text-heading">{group.label}</h4>
                    <p className="mt-0.5 text-[11px] text-muted">{group.description} · {group.artifacts.length} artifact{group.artifacts.length === 1 ? '' : 's'}</p>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-left text-xs">
                    <thead className="border-b border-border bg-bg/20 text-muted">
                      <tr>
                        <th className="px-5 py-3">Artifact</th>
                        <th className="hidden px-4 py-3 2xl:table-cell">Category</th>
                        <th className="hidden px-4 py-3 2xl:table-cell">Media type</th>
                        <th className="px-4 py-3">Stage</th>
                        <th className="px-4 py-3">Rows</th>
                        <th className="px-4 py-3">Bytes</th>
                        <th className="px-5 py-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {group.artifacts.map((artifact) => (
                        <tr
                          key={artifact.key}
                          className={`cursor-pointer border-b border-border/40 align-top hover:bg-surface-soft/30 ${selectedKey === artifact.key ? 'bg-primary/10' : ''}`}
                          onClick={() => onSelect(artifact)}
                          onKeyDown={(event) => {
                            if (event.key === 'Enter' || event.key === ' ') {
                              event.preventDefault();
                              onSelect(artifact);
                            }
                          }}
                          tabIndex={0}
                        >
                          <td className="px-5 py-3">
                            <p className="font-semibold text-text-heading">{artifact.key}</p>
                            <p className="mt-1 max-w-md break-all font-mono text-[11px] text-muted">{artifact.path}</p>
                          </td>
                          <td className="hidden px-4 py-3 2xl:table-cell"><span className="rounded-full border border-border px-2 py-1 text-[11px] text-text-heading">{artifact.category}</span></td>
                          <td className="hidden px-4 py-3 text-muted 2xl:table-cell">{artifact.media_type}</td>
                          <td className="px-4 py-3 text-muted">{artifact.stage ?? 'Unavailable'}</td>
                          <td className="px-4 py-3 text-text-heading">{artifact.rows === null ? 'Unavailable' : formatCount(artifact.rows)}</td>
                          <td className="px-4 py-3 text-text-heading">{formatBytes(artifact.byte_size)}</td>
                          <td className="px-5 py-3 text-right" onClick={(event) => event.stopPropagation()}>
                            {isDownloadableArtifact(artifact) ? (
                              <a
                                href={getArtifactDownloadUrl(runId, artifact.key)}
                                className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-[11px] font-semibold text-primary hover:bg-surface-soft"
                              >
                                <Download size={13} aria-hidden="true" /> Download
                              </a>
                            ) : (
                              <span className="text-[11px] text-muted" title="Intermediate artifacts are intentionally unavailable through the download endpoint.">Not downloadable</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

function groupOutputs(artifacts: ArtifactMetadata[]): OutputGroup[] {
  const published = artifacts.filter((artifact) => artifact.category === 'report');
  const provenance = artifacts.filter((artifact) => artifact.category === 'intermediate');
  const data = artifacts.filter((artifact) => artifact.category !== 'report' && artifact.category !== 'intermediate');
  return [
    {
      id: 'published',
      label: 'Published outputs',
      description: 'Report artifacts already produced by the selected run',
      icon: FileText,
      artifacts: published,
    },
    {
      id: 'data',
      label: 'Analytical data & metadata',
      description: 'Canonical manifest-listed data supporting downstream analysis',
      icon: Database,
      artifacts: data,
    },
    {
      id: 'provenance',
      label: 'Advanced provenance',
      description: 'Intermediate stage handoffs retained for auditability',
      icon: ShieldCheck,
      artifacts: provenance,
    },
  ].filter((group) => group.artifacts.length > 0);
}

function FilterSelect({
  label,
  value,
  values,
  onChange,
}: {
  label: string;
  value: string;
  values: string[];
  onChange: (value: string) => void;
}) {
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
