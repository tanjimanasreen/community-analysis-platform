import {
  ArrowDown,
  ArrowRight,
  BrainCircuit,
  Database,
  GitCompareArrows,
  Network,
  ScanSearch,
  UsersRound,
  type LucideIcon,
} from 'lucide-react';
import { WORKFLOW_BRANCHES, WORKFLOW_FOUNDATION, type ResearchDimension } from '../methodologyContent';

const foundationIcons: Record<string, LucideIcon> = {
  'platform-data': Database,
  'interaction-network': Network,
  affinity: GitCompareArrows,
  louvain: UsersRound,
};

const branchIcons: Record<string, LucideIcon> = {
  structural: GitCompareArrows,
  semantic: BrainCircuit,
  temporal: ScanSearch,
};

const branchClass: Record<ResearchDimension, string> = {
  Structural: 'border-primary/30 bg-primary/5 text-primary',
  Semantic: 'border-secondary/30 bg-secondary/5 text-secondary',
  Temporal: 'border-warning/30 bg-warning/5 text-warning',
};

export default function MethodologyWorkflow() {
  return (
    <div className="panel p-5 sm:p-6">
      <div className="max-w-3xl">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Research pipeline</p>
        <h2 className="mt-1 text-lg font-bold text-text-heading">Methodological Workflow</h2>
        <p className="mt-1 text-sm leading-6 text-muted">A shared monthly network foundation feeds structural, semantic, and temporal analyses.</p>
      </div>

      <ol className="mt-6 grid items-stretch gap-2 md:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr]" aria-label="Shared methodological foundation">
        {WORKFLOW_FOUNDATION.map((step, index) => {
          const Icon = foundationIcons[step.id];
          return (
            <li key={step.id} className="contents">
              <div className="flex min-w-0 items-center gap-3 rounded-xl border border-border/70 bg-surface-soft/35 p-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon size={17} aria-hidden="true" /></span>
                <div className="min-w-0">
                  <h3 className="text-xs font-bold text-text-heading">{step.title}</h3>
                  <p className="mt-0.5 text-[11px] leading-4 text-muted">{step.detail}</p>
                </div>
              </div>
              {index < WORKFLOW_FOUNDATION.length - 1 && (
                <div className="flex items-center justify-center text-border" aria-hidden="true">
                  <ArrowDown size={17} className="md:hidden" />
                  <ArrowRight size={17} className="hidden md:block" />
                </div>
              )}
            </li>
          );
        })}
      </ol>

      <div className="mx-auto my-4 h-5 w-px bg-border" aria-hidden="true" />
      <div className="relative" role="group" aria-label="Analytical branches">
        <div className="absolute left-[16.66%] right-[16.66%] top-0 hidden h-px bg-border lg:block" aria-hidden="true" />
        <div className="grid gap-3 pt-3 lg:grid-cols-3">
          {WORKFLOW_BRANCHES.map((branch) => {
            const Icon = branchIcons[branch.id];
            return (
              <article key={branch.id} className={`relative rounded-2xl border p-4 ${branchClass[branch.dimension]}`}>
                <span className="absolute left-1/2 top-[-13px] hidden h-3 w-px -translate-x-1/2 bg-border lg:block" aria-hidden="true" />
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-surface/80"><Icon size={16} aria-hidden="true" /></span>
                    <h3 className="text-sm font-bold text-text-heading">{branch.dimension}</h3>
                  </div>
                  <div className="flex gap-1">
                    {branch.rqs.map((rq) => <span key={rq} className="rounded-full border border-border/60 bg-surface/70 px-2 py-0.5 text-[10px] font-bold">{rq}</span>)}
                  </div>
                </div>
                <p className="mt-2 text-xs leading-5 text-muted">{branch.summary}</p>
                <ol className="mt-4 space-y-2">
                  {branch.steps.map((step, index) => (
                    <li key={step} className="flex items-center gap-2 text-xs font-semibold text-text-heading">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-border/60 bg-surface/70 text-[9px]">{index + 1}</span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ol>
                {branch.id === 'semantic' && (
                  <p className="mt-4 border-t border-border/60 pt-3 text-[11px] leading-4 text-muted">
                    LDA produces topic-keyword evidence first; generated theme interpretation remains downstream.
                  </p>
                )}
                {branch.id === 'temporal' && (
                  <div role="note" className="mt-4 flex items-center gap-2 border-t border-border/60 pt-3 text-[11px] leading-4 text-muted" aria-label="Generated themes contribute to longitudinal theme similarity">
                    <span className="font-semibold text-text-heading">Generated themes</span>
                    <ArrowRight size={13} className="shrink-0" aria-hidden="true" />
                    <span>Theme similarity</span>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      </div>
    </div>
  );
}
