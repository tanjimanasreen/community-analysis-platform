import { Activity, Clock3, MessageSquareText, Network, Send, Target } from 'lucide-react';
import { AIM, RESEARCH_DIMENSIONS, SCOPE_ITEMS } from '../methodologyContent';

const dimensionIcons = {
  Structural: Network,
  Semantic: MessageSquareText,
  Temporal: Clock3,
};

export default function AimScopePanel() {
  return (
    <div className="panel p-5 sm:p-6">
      <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-2xl border border-border/70 bg-surface-soft/35 p-5">
          <div className="flex items-center gap-2 text-primary">
            <Target size={18} aria-hidden="true" />
            <h2 className="text-sm font-bold uppercase tracking-[0.12em]">Aim</h2>
          </div>
          <p className="mt-3 max-w-3xl text-base font-semibold leading-7 text-text-heading">{AIM}</p>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            {RESEARCH_DIMENSIONS.map((dimension) => {
              const Icon = dimensionIcons[dimension.id];
              return (
                <div key={dimension.id} className="rounded-xl border border-border/70 bg-bg/30 p-3">
                  <div className="flex items-center gap-2">
                    <span className="rounded-lg bg-primary/10 p-1.5 text-primary"><Icon size={15} aria-hidden="true" /></span>
                    <p className="text-xs font-bold text-text-heading">{dimension.id}</p>
                  </div>
                  <p className="mt-2 text-[11px] leading-5 text-muted">{dimension.description}</p>
                </div>
              );
            })}
          </div>
        </div>

        <div className="rounded-2xl border border-border/70 bg-surface-soft/35 p-5">
          <div className="flex items-center gap-2 text-primary">
            <Send size={18} aria-hidden="true" />
            <h2 className="text-sm font-bold uppercase tracking-[0.12em]">Scope</h2>
          </div>
          <dl className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
            {SCOPE_ITEMS.map((item, index) => {
              const Icon = index === 0 ? Send : index === 1 ? Activity : index === 2 ? Clock3 : Network;
              return (
                <div key={item.label} className="rounded-xl border border-border/60 bg-bg/25 p-3">
                  <dt className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
                    <Icon size={14} aria-hidden="true" />
                    {item.label}
                  </dt>
                  <dd className="mt-1.5 text-sm font-semibold text-text-heading">{item.value}</dd>
                </div>
              );
            })}
          </dl>
        </div>
      </div>
    </div>
  );
}
