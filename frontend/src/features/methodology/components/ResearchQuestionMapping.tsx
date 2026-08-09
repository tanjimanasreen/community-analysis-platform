import { ArrowRight, ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { RQ_METHOD_MAPPING } from '../methodologyContent';

export default function ResearchQuestionMapping({ search }: { search: string }) {
  return (
    <div className="panel p-5 sm:p-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Traceability</p>
        <h2 className="mt-1 text-lg font-bold text-text-heading">From Method to Research Questions</h2>
      </div>
      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {RQ_METHOD_MAPPING.map((item) => (
          <Link
            key={item.rq}
            to={`${item.route}${search}`}
            className="group rounded-2xl border border-border/70 bg-surface-soft/35 p-4 transition-colors hover:border-primary/40 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <div className="flex items-center gap-2 text-xs font-bold text-primary">
              <span>{item.method}</span>
              <ArrowRight size={14} aria-hidden="true" />
              <span>{item.rq}</span>
            </div>
            <div className="mt-3 flex items-end justify-between gap-3">
              <p className="text-xs leading-5 text-muted">{item.outcome}</p>
              <ArrowUpRight size={15} className="shrink-0 text-muted group-hover:text-primary" aria-hidden="true" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
