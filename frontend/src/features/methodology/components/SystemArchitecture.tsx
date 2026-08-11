import { ArrowDown, BarChart3, Database, FileCheck2, Layers3, Server, type LucideIcon } from 'lucide-react';
import { SYSTEM_LAYERS } from '../methodologyContent';

const layerIcons: Record<string, LucideIcon> = {
  sources: Database,
  graph: Layers3,
  analysis: BarChart3,
  artifacts: FileCheck2,
  api: Server,
  interface: BarChart3,
};

export default function SystemArchitecture() {
  return (
    <div className="panel p-5 sm:p-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Software realization</p>
          <h2 className="mt-1 text-lg font-bold text-text-heading">System Implementation</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">The research logic is executed through a layered, artifact-first production architecture.</p>
        </div>
        <span className="self-start rounded-full border border-border bg-surface-soft px-3 py-1 text-[11px] font-semibold text-muted">Current implementation</span>
      </div>

      <ol className="mx-auto mt-6 max-w-4xl" aria-label="System implementation layers">
        {SYSTEM_LAYERS.map((layer, index) => {
          const Icon = layerIcons[layer.id];
          return (
            <li key={layer.id}>
              <div className="grid gap-2 rounded-xl border border-border/70 bg-surface-soft/30 p-3 sm:grid-cols-[44px_minmax(150px,0.45fr)_1fr] sm:items-center sm:gap-4">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon size={17} aria-hidden="true" /></span>
                <h3 className="text-xs font-bold uppercase tracking-[0.08em] text-text-heading">{layer.title}</h3>
                <p className="text-xs leading-5 text-muted">{layer.detail}</p>
              </div>
              {index < SYSTEM_LAYERS.length - 1 && (
                <div className="flex h-5 items-center justify-center text-border" aria-hidden="true"><ArrowDown size={16} /></div>
              )}
            </li>
          );
        })}
      </ol>

      <div className="mt-5 grid gap-2 border-t border-border/70 pt-4 text-xs sm:grid-cols-2">
        <p className="text-muted"><strong className="text-text-heading">Thesis implementation:</strong> Neo4j.</p>
        <p className="text-muted"><strong className="text-text-heading">Current graph-store boundary:</strong> configurable, with Memgraph Community Edition as the default local target.</p>
      </div>
    </div>
  );
}
