import { useState } from 'react';
import { CheckCircle2, ChevronDown } from 'lucide-react';
import type { EvolutionPath } from '../../../types/api';
import { formatCount } from '../../overview/overviewUtils';

interface Props {
  paths: EvolutionPath[];
  selectedPathId: string | null;
  onSelectPath: (pathId: string) => void;
}

const INITIAL_PATHS = 10;

export default function PersistentPathTimeline({ paths, selectedPathId, onSelectPath }: Props) {
  const [showAll, setShowAll] = useState(false);
  const visible = showAll ? paths : paths.slice(0, INITIAL_PATHS);
  const maxMembers = Math.max(1, ...paths.flatMap((path) => path.steps.map((step) => step.member_count)));

  if (paths.length === 0) {
    return <p className="rounded-xl border border-border bg-surface-soft/30 p-6 text-sm text-muted">No persistent paths were materialized for this run.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted" aria-label="Path timeline legend">
        <span>Node size = members</span>
        <span>Connector label = Jaccard</span>
        <span>Connector thickness = retained members</span>
      </div>
      <div className="space-y-2">
        {visible.map((path) => {
          const selected = selectedPathId === path.path_id;
          return (
            <button
              type="button"
              key={path.path_id}
              onClick={() => onSelectPath(path.path_id)}
              aria-pressed={selected}
              aria-label={`Select Path ${path.display_order}, ${path.duration} months, average Jaccard ${path.average_jaccard.toFixed(2)}`}
              className={`w-full rounded-2xl border p-3 text-left transition-colors ${
                selected
                  ? 'border-primary bg-primary/10'
                  : 'border-border bg-surface-soft/25 hover:border-border-light hover:bg-surface-soft/50'
              }`}
            >
              <div className="grid gap-3 xl:grid-cols-[165px_minmax(0,1fr)] xl:items-center">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className={`text-sm font-bold ${selected ? 'text-primary' : 'text-text-heading'}`}>Path {path.display_order}</p>
                    {selected && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-primary">
                        <CheckCircle2 size={12} aria-hidden="true" />
                        Selected
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-muted">{path.duration} months · avg Jaccard {path.average_jaccard.toFixed(2)}</p>
                </div>
                <div className="overflow-x-auto pb-1">
                  <div className="flex min-w-max items-center py-2 pr-2">
                    {path.steps.map((step, index) => {
                      const size = 42 + Math.round(22 * (step.member_count / maxMembers));
                      const prior = index > 0 ? step : null;
                      return (
                        <div key={step.community_key} className="flex items-center">
                          {prior && (
                            <div className="flex min-w-[84px] flex-col items-center px-2" aria-label={`${prior.retained_count ?? 0} retained members; Jaccard ${prior.jaccard_from_previous?.toFixed(2) ?? 'unavailable'}`}>
                              <span className={`mb-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold ${
                                selected ? 'border-primary/35 bg-primary/10 text-text-heading' : 'border-border bg-bg/60 text-text-heading'
                              }`}>
                                {prior.jaccard_from_previous?.toFixed(2) ?? '—'}
                              </span>
                              <span
                                aria-hidden="true"
                                className={`block w-full rounded-full ${selected ? 'bg-primary' : 'bg-primary/35'}`}
                                style={{ height: `${Math.max(2, Math.min(9, 2 + (prior.retained_count ?? 0) / 8))}px` }}
                              />
                            </div>
                          )}
                          <div className="flex flex-col items-center gap-1.5">
                            <span
                              className={`flex items-center justify-center rounded-full border font-bold ${
                                selected
                                  ? 'border-primary bg-primary/20 text-primary'
                                  : 'border-primary/40 bg-primary/10 text-text-heading'
                              }`}
                              style={{ width: size, height: size }}
                            >
                              {formatCount(step.member_count)}
                            </span>
                            <span className="text-[11px] text-muted">{step.month}</span>
                            <span className="max-w-24 truncate text-[11px] font-semibold text-text-heading">C{step.community_id}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
      {paths.length > INITIAL_PATHS && (
        <button type="button" className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline" onClick={() => setShowAll((value) => !value)}>
          {showAll ? 'Show fewer paths' : `Show all ${paths.length} paths`} <ChevronDown size={14} className={showAll ? 'rotate-180' : ''} />
        </button>
      )}
    </div>
  );
}
