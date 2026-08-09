import { ArrowDown, BarChart3, Database, FileCheck2, Network, UsersRound } from 'lucide-react';
import { SYSTEM_STAGES } from '../methodologyContent';

const stageIcons = {
  ingestion: Database,
  network: Network,
  community: UsersRound,
  analyses: BarChart3,
  delivery: FileCheck2,
};

export default function SystemArchitecture() {
  return (
    <div className="panel p-5 sm:p-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Supporting implementation</p>
          <h2 className="mt-1 text-lg font-bold text-text-heading">System Architecture</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">The production system preserves the thesis pipeline while separating ingestion, analysis, persisted artifacts, and dashboard delivery.</p>
        </div>
        <span className="self-start rounded-full border border-border bg-surface-soft px-3 py-1 text-[11px] font-semibold text-muted">Current implementation</span>
      </div>

      <div className="mt-6 grid items-stretch gap-2 lg:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr_auto_1fr]">
        {SYSTEM_STAGES.map((stage, index) => {
          const Icon = stageIcons[stage.id];
          return (
            <div key={stage.id} className="contents">
              <article className="rounded-2xl border border-border/70 bg-surface-soft/35 p-4 text-center">
                <div className="mx-auto flex items-center justify-center gap-2">
                  <span className="rounded-full border border-primary/25 bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary">{stage.code}</span>
                  <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary"><Icon size={18} aria-hidden="true" /></span>
                </div>
                <h3 className="mt-3 text-sm font-bold text-text-heading">{stage.title}</h3>
                <p className="mt-1 text-xs leading-5 text-muted">{stage.detail}</p>
              </article>
              {index < SYSTEM_STAGES.length - 1 && (
                <div className="flex items-center justify-center py-1 text-border lg:py-0">
                  <ArrowDown className="lg:-rotate-90" size={18} aria-hidden="true" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      <p className="mt-4 text-xs leading-5 text-muted">
        <strong className="text-text-heading">Historical note:</strong> the thesis implementation used Neo4j. The current project keeps the same conceptual graph boundary with configurable storage and Memgraph Community Edition as the default local target.
      </p>
    </div>
  );
}
