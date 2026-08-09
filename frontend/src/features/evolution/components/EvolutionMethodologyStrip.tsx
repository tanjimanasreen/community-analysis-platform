import { BookOpen, GitBranch, Repeat2, Sparkles, UsersRound } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { EvolutionMethodology } from '../../../types/api';

interface Props {
  methodology: EvolutionMethodology;
  search?: string;
}

export default function EvolutionMethodologyStrip({ methodology, search = '' }: Props) {
  const threshold = methodology.transition_threshold;
  const model = methodology.similarity_model || 'paraphrase-MiniLM-L6-v2';
  return (
    <section className="panel p-4 sm:p-5" aria-labelledby="evolution-methodology-heading">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-4xl">
          <div className="flex items-center gap-2 text-primary">
            <BookOpen size={18} aria-hidden="true" />
            <h2 id="evolution-methodology-heading" className="text-sm font-bold text-text-heading">
              How Community Evolution is calculated
            </h2>
          </div>
          <p className="mt-1.5 text-sm leading-5 text-muted">
            Accepted month-to-month transitions form persistent paths; those same paths are then inspected for
            membership movement and sentence-embedding theme continuity.
          </p>
        </div>
        <Link
          className="inline-flex shrink-0 items-center gap-2 self-start rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text-heading hover:bg-surface-soft"
          to={`/methodology${search}`}
        >
          Full methodology
        </Link>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4">
        <MethodItem icon={GitBranch} label="Persistence" value={`Jaccard ≥ ${threshold === null ? 'run default' : threshold.toFixed(2)}`} />
        <MethodItem icon={Repeat2} label="Path construction" value="Start-to-end DFS" />
        <MethodItem icon={UsersRound} label="Member mobility" value="Retained · new · reappeared · exited" />
        <MethodItem icon={Sparkles} label="Theme similarity" value={model.replace('sentence-transformers/', '')} />
      </div>

      <details className="mt-3 rounded-xl border border-border/70 bg-surface-soft/40 px-4 py-2.5 text-sm">
        <summary className="cursor-pointer font-semibold text-text-heading">Resolved analytical contract</summary>
        <dl className="mt-3 grid grid-cols-1 gap-x-6 gap-y-2 text-xs sm:grid-cols-2">
          <Contract label="Content type" value={methodology.content_type || 'Unavailable'} />
          <Contract label="Transition threshold" value={threshold === null ? 'Unavailable' : threshold.toString()} />
          <Contract label="Embedding provider" value={methodology.similarity_provider || 'Configured runtime'} />
          <Contract label="Model revision" value={methodology.similarity_model_revision || 'Unavailable'} mono />
        </dl>
      </details>
    </section>
  );
}

function MethodItem({ icon: Icon, label, value }: { icon: typeof GitBranch; label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/70 bg-bg/20 px-3 py-2.5">
      <div className="flex items-center gap-2 text-xs font-semibold text-muted"><Icon size={15} aria-hidden="true" />{label}</div>
      <p className="mt-1 text-sm font-semibold text-text-heading">{value}</p>
    </div>
  );
}

function Contract({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:justify-between">
      <dt className="text-muted">{label}</dt>
      <dd className={`text-text-heading ${mono ? 'font-mono break-all' : ''}`}>{value}</dd>
    </div>
  );
}
