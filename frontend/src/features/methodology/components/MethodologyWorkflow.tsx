import { ArrowRight, BrainCircuit, Database, GitCompareArrows, Network, ScanSearch, Sparkles, UsersRound } from 'lucide-react';
import { WORKFLOW_STEPS } from '../methodologyContent';

const stepIcons = {
  'data-ingestion': Database,
  'interaction-network': Network,
  'community-extraction': UsersRound,
  'structural-analysis': GitCompareArrows,
  'topic-modeling': BrainCircuit,
  'theme-interpretation': Sparkles,
  'longitudinal-analysis': ScanSearch,
};

const dimensionClass = {
  Foundation: 'border-border bg-surface-soft text-muted',
  Structural: 'border-primary/25 bg-primary/10 text-primary',
  Semantic: 'border-secondary/25 bg-secondary/10 text-secondary',
  Temporal: 'border-warning/25 bg-warning/10 text-warning',
};

export default function MethodologyWorkflow() {
  return (
    <div className="panel p-5 sm:p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Research pipeline</p>
          <h2 className="mt-1 text-lg font-bold text-text-heading">Methodological Workflow</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">
            One analytical sequence connects interaction structure, community discourse, and longitudinal change.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-[11px] font-semibold">
          {(['Structural', 'Semantic', 'Temporal'] as const).map((dimension) => (
            <span key={dimension} className={`rounded-full border px-3 py-1 ${dimensionClass[dimension]}`}>{dimension}</span>
          ))}
        </div>
      </div>

      <ol className="mt-6 grid gap-3 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
        {WORKFLOW_STEPS.map((step, index) => {
          const Icon = stepIcons[step.id as keyof typeof stepIcons];
          return (
            <li key={step.id} className="relative min-w-0">
              <article className="flex h-full flex-col rounded-2xl border border-border/70 bg-surface-soft/35 p-4">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11px] font-bold tracking-[0.12em] text-primary">{step.number}</span>
                  <span className="rounded-xl bg-bg/40 p-2 text-primary"><Icon size={17} aria-hidden="true" /></span>
                </div>
                <h3 className="mt-4 text-sm font-bold leading-5 text-text-heading">{step.title}</h3>
                <p className="mt-2 text-xs leading-5 text-muted">{step.description}</p>
                <span className={`mt-auto self-start rounded-full border px-2.5 py-1 pt-1 text-[10px] font-semibold ${dimensionClass[step.dimension]}`}>
                  {step.dimension}
                </span>
              </article>
              {index < WORKFLOW_STEPS.length - 1 && (
                <ArrowRight className="absolute -right-2.5 top-1/2 z-10 hidden -translate-y-1/2 text-border xl:block" size={18} aria-hidden="true" />
              )}
            </li>
          );
        })}
      </ol>

      <div className="mt-5 rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 text-xs leading-5 text-muted">
        <strong className="text-text-heading">Semantic order is preserved:</strong> LDA produces topic-keyword evidence first; configured provider labels are downstream interpretations of that evidence.
      </div>
    </div>
  );
}
