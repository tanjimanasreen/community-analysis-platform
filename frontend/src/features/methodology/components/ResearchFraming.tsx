import { ArrowUpRight, Clock3, MessageSquareText, Network, Target, type LucideIcon } from 'lucide-react';
import { Link } from 'react-router-dom';
import { AIM, RESEARCH_DIMENSIONS, RESEARCH_QUESTIONS, SCOPE_ITEMS, type ResearchDimension } from '../methodologyContent';

const dimensionIcons: Record<ResearchDimension, LucideIcon> = {
  Structural: Network,
  Semantic: MessageSquareText,
  Temporal: Clock3,
};

const dimensionClass: Record<ResearchDimension, string> = {
  Structural: 'border-primary/25 bg-primary/5',
  Semantic: 'border-secondary/25 bg-secondary/5',
  Temporal: 'border-warning/25 bg-warning/5',
};

export default function ResearchFraming({ search }: { search: string }) {
  return (
    <div className="panel p-5 sm:p-6">
      <div className="text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Research framing</p>
        <div className="mx-auto mt-3 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Target size={19} aria-hidden="true" />
        </div>
        <h2 className="mt-3 text-lg font-bold text-text-heading">Research Aim</h2>
        <p className="mx-auto mt-2 max-w-4xl text-sm font-semibold leading-6 text-text-heading">{AIM}</p>
      </div>

      <div className="mt-6 grid gap-3 lg:grid-cols-3">
        {RESEARCH_DIMENSIONS.map((dimension) => {
          const Icon = dimensionIcons[dimension.id];
          const questions = RESEARCH_QUESTIONS.filter((rq) => rq.dimension === dimension.id);
          return (
            <article key={dimension.id} className={`rounded-2xl border p-4 ${dimensionClass[dimension.id]}`}>
              <div className="flex items-center gap-2">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-surface/75 text-primary"><Icon size={16} aria-hidden="true" /></span>
                <div>
                  <h3 className="text-sm font-bold text-text-heading">{dimension.id}</h3>
                  <p className="text-[11px] leading-4 text-muted">{dimension.description}</p>
                </div>
              </div>

              <div className="mt-4 space-y-2">
                {questions.map((rq) => (
                  <Link
                    key={rq.id}
                    to={`${rq.route}${search}`}
                    aria-label={`${rq.id}: ${rq.question}`}
                    className="group block rounded-xl border border-border/60 bg-surface/70 p-3 transition-colors hover:border-primary/40 hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                  >
                    <div className="flex items-start gap-3">
                      <span className="shrink-0 rounded-full border border-primary/25 bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary">{rq.id}</span>
                      <p className="min-w-0 flex-1 text-xs font-semibold leading-5 text-text-heading">{rq.question}</p>
                      <ArrowUpRight size={14} className="mt-0.5 shrink-0 text-muted transition-colors group-hover:text-primary" aria-hidden="true" />
                    </div>
                  </Link>
                ))}
              </div>
            </article>
          );
        })}
      </div>

      <dl className="mt-5 grid gap-x-6 gap-y-3 border-t border-border/70 pt-4 sm:grid-cols-2 xl:grid-cols-4">
        {SCOPE_ITEMS.map((item) => (
          <div key={item.label} className="min-w-0">
            <dt className="text-[10px] font-semibold uppercase tracking-[0.1em] text-muted">{item.label}</dt>
            <dd className="mt-1 text-xs font-semibold leading-5 text-text-heading">{item.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
