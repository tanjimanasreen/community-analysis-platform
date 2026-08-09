import type { ThemeProgressionLink, ThemeProgressionPath } from './themeProgressionModel';
import { periodLabel } from './themeTrendModel';

interface Props {
  paths: ThemeProgressionPath[];
  selectedPathId: string | null;
  onSelectPath: (pathId: string) => void;
}

export default function ThemeProgressionTimeline({ paths, selectedPathId, onSelectPath }: Props) {
  if (paths.length === 0) {
    return <p className="mt-5 text-sm text-muted">No persistent transition path is available in the selected range.</p>;
  }

  const periods = [...new Set(paths.flatMap((path) => path.nodes.map((node) => node.period)))].sort();
  const maxRetained = Math.max(1, ...paths.flatMap((path) => path.links.map((link) => link.retainedCount ?? 0)));
  const gridStyle = {
    gridTemplateColumns: `repeat(${periods.length}, minmax(10rem, 1fr))`,
    minWidth: `${periods.length * 180}px`,
  };

  return (
    <div className="mt-5 overflow-x-auto pb-2" aria-label="Persistent community theme paths by month">
      <div className="grid gap-5 px-4 text-xs font-semibold text-muted" style={gridStyle} aria-hidden="true">
        {periods.map((period) => <span key={period}>{periodLabel(period)}</span>)}
      </div>
      <div className="mt-2 space-y-4">
        {paths.map((path, index) => {
          const nodesByPeriod = new Map(path.nodes.map((node) => [node.period, node]));
          const linksBySource = new Map(path.links.map((link) => [link.sourceKey, link]));
          const selected = selectedPathId === path.id;
          return (
            <button
              key={path.id}
              type="button"
              aria-pressed={selected}
              onClick={() => onSelectPath(path.id)}
              className={`block w-full rounded-xl border p-4 text-left ${selected ? 'border-primary bg-primary/10' : 'border-border bg-bg/20 hover:bg-surface-soft/40'}`}
            >
              <div className="mb-4 flex flex-wrap items-center justify-between gap-2 text-xs">
                <span className="font-semibold text-text-heading">Persistent path {index + 1}</span>
                <span className="text-muted">{path.distinctMonthCount} months · avg Jaccard {path.averageJaccard.toFixed(2)} · retained {path.totalRetainedMembers ?? 'unavailable'}</span>
              </div>
              <div className="grid gap-5" style={gridStyle}>
                {periods.map((period) => {
                  const node = nodesByPeriod.get(period);
                  if (!node) {
                    return <div key={period} className="min-h-28 rounded-lg border border-dashed border-border/60" aria-label={`${periodLabel(period)} has no node in this path`} />;
                  }
                  const link = linksBySource.get(node.key);
                  return (
                    <div key={node.key} className="relative min-w-0">
                      <div className="relative z-10 min-h-28 rounded-lg border border-border bg-surface-soft/70 p-3">
                        <p className="text-xs font-semibold text-primary">Community {node.communityId}</p>
                        <p className="mt-2 break-words text-sm font-semibold text-text-heading">{node.labels.join(' · ') || 'Theme unavailable'}</p>
                        <p className="mt-2 line-clamp-2 text-xs text-muted">{node.keywords.slice(0, 5).join(', ') || 'LDA keywords unavailable'}</p>
                        {link && <LinkEvidence link={link} />}
                      </div>
                      {link && (
                        <span
                          className="pointer-events-none absolute left-full top-1/2 w-5 -translate-y-1/2 rounded-full bg-primary"
                          style={{
                            height: `${link.retainedCount === null ? 2 : 2 + (link.retainedCount / maxRetained) * 6}px`,
                            opacity: 0.25 + Math.min(1, Math.max(0, link.jaccard)) * 0.75,
                          }}
                          aria-hidden="true"
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function LinkEvidence({ link }: { link: ThemeProgressionLink }) {
  return (
    <p className="mt-3 border-t border-border/60 pt-2 text-xs text-muted">
      Next: Jaccard {link.jaccard.toFixed(2)} · retained {link.retainedCount ?? 'unavailable'}
    </p>
  );
}
