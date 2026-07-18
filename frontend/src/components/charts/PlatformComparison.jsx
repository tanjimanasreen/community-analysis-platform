import React from 'react';
import { CalendarRange, Database, GitCommit, Layers3 } from 'lucide-react';
import { conciseRunId, metadataValue } from '../../features/overview/overviewUtils';

export default function PlatformComparison({ selectedRun, selectedRunDetail, overview }) {
  const commit = metadataValue(selectedRunDetail?.code, ['git_commit', 'commit']);
  const configDigest = metadataValue(selectedRunDetail?.code, ['config_digest']);
  const items = [
    { label: 'Run', value: selectedRun ? conciseRunId(selectedRun.run_id) : 'Unavailable', icon: Database },
    { label: 'Platform / content', value: `${overview.platform || 'Unavailable'} / ${overview.content_type || 'Unavailable'}`, icon: Layers3 },
    { label: 'Date range', value: formatRange(overview.date_start, overview.date_end), icon: CalendarRange },
    { label: 'Code provenance', value: commit || configDigest || 'Unavailable', icon: GitCommit },
  ];

  return (
    <section className="bg-panel border border-border rounded-xl p-5 flex flex-col h-full">
      <h3 className="text-sm font-bold text-text-heading">Run Provenance</h3>
      <p className="mt-1 text-xs text-muted">A platform comparison requires explicit compatible run selection and is available on the Comparative route.</p>
      <div className="mt-5 grid grid-cols-1 gap-3">
        {items.map(({ label, value, icon: Icon }) => (
          <div key={label} className="flex items-start gap-3 rounded-lg border border-border bg-panel-soft/40 p-3">
            <Icon size={17} className="text-primary mt-0.5 shrink-0" />
            <div>
              <p className="text-xs text-muted">{label}</p>
              <p className="mt-1 text-sm font-semibold text-text-heading break-all">{value}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function formatRange(start, end) {
  if (!start && !end) return 'Unavailable';
  return `${start || 'Unknown'} – ${end || 'Unknown'}`;
}
