import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  BrainCircuit,
  MessageSquareText,
  Network,
  Sparkles,
  Tags,
} from 'lucide-react';
import { Link } from 'react-router-dom';

const STEPS = [
  {
    id: 'messages',
    title: 'Community Messages',
    detail: 'Matched IF/WIF community text provides the evidence used for topic modeling.',
    icon: MessageSquareText,
  },
  {
    id: 'lda',
    title: 'LDA Topic Extraction',
    detail: 'Saved unigram and bigram LDA topics produce the keyword evidence for interpretation.',
    icon: BrainCircuit,
  },
  {
    id: 'labels',
    title: 'Generated Theme Labels',
    detail: 'The configured provider converts LDA keyword evidence into readable general-theme labels.',
    icon: Sparkles,
  },
  {
    id: 'embeddings',
    title: 'Semantic Embeddings',
    detail: 'all-MiniLM-L6-v2 represents generated general-theme labels for semantic grouping.',
    icon: Network,
  },
  {
    id: 'canonical',
    title: 'HDBSCAN Canonicalization',
    detail: 'Monthly HDBSCAN groups related labels; monthly noise stays auditable. A second HDBSCAN pass links representatives into canonical families.',
    icon: Tags,
  },
  {
    id: 'progression',
    title: 'Ranking & Progression',
    detail: 'Up to five canonical themes per month are ranked by matched-community coverage and tracked by canonical ID.',
    icon: Activity,
  },
] as const;

interface Props {
  methodologyHref: string;
}

export default function ThematicMethodologyOverview({ methodologyHref }: Props) {
  return (
    <div className="panel p-5 sm:p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">RQ2 · semantic analysis</p>
          <h2 className="mt-1 text-lg font-bold text-text-heading">How these results are derived</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">
            The dashboard preserves the thesis evidence chain: statistical topic evidence is created first, readable labels are generated downstream, and semantic clustering organizes related labels for monthly comparison.
          </p>
        </div>
        <Link
          to={methodologyHref}
          className="inline-flex shrink-0 items-center gap-2 self-start rounded-xl border border-border bg-surface-soft/40 px-3 py-2 text-xs font-semibold text-text-heading transition-colors hover:border-primary/40 hover:text-primary"
        >
          View full methodology
          <ArrowUpRight size={14} aria-hidden="true" />
        </Link>
      </div>

      <ol className="mt-5 grid gap-3 md:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">
        {STEPS.map((step, index) => {
          const Icon = step.icon;
          return (
            <li key={step.id} className="relative min-w-0">
              <article className="flex h-full flex-col rounded-2xl border border-border/70 bg-surface-soft/30 p-4">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[10px] font-bold tracking-[0.14em] text-primary">{String(index + 1).padStart(2, '0')}</span>
                  <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <Icon size={16} aria-hidden="true" />
                  </span>
                </div>
                <h3 className="mt-3 text-sm font-bold leading-5 text-text-heading">{step.title}</h3>
                <p className="mt-2 text-xs leading-5 text-muted">{step.detail}</p>
              </article>
              {index < STEPS.length - 1 && (
                <ArrowRight
                  className="absolute -right-2.5 top-1/2 z-10 hidden -translate-y-1/2 text-border xl:block"
                  size={18}
                  aria-hidden="true"
                />
              )}
            </li>
          );
        })}
      </ol>

      <dl className="mt-4 grid gap-2 text-xs sm:grid-cols-3">
        <MethodContract label="Analytical foundation" value="LDA-derived topic evidence" />
        <MethodContract label="Interpretation layer" value="Configured provider theme labels" />
        <MethodContract label="Cross-month organization" value="Semantic HDBSCAN canonicalization" />
      </dl>
    </div>
  );
}

function MethodContract({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/70 bg-bg/20 px-3 py-2.5">
      <dt className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted">{label}</dt>
      <dd className="mt-1 font-semibold text-text-heading">{value}</dd>
    </div>
  );
}
