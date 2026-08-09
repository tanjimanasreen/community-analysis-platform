import { ArrowUpRight, GitBranch, MessageSquareText, Network, UsersRound } from 'lucide-react';
import { Link } from 'react-router-dom';
import { RESEARCH_QUESTIONS } from '../methodologyContent';

const rqIcons = {
  RQ1: Network,
  RQ2: MessageSquareText,
  RQ3: GitBranch,
  RQ4: UsersRound,
};

export default function ResearchQuestionGrid({ search }: { search: string }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {RESEARCH_QUESTIONS.map((rq) => {
        const Icon = rqIcons[rq.id];
        return (
          <Link
            key={rq.id}
            to={`${rq.route}${search}`}
            aria-label={`${rq.id}: ${rq.question}`}
            className="group flex min-h-48 flex-col rounded-2xl border border-border/70 bg-surface p-4 transition-colors hover:border-primary/45 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <div className="flex items-start justify-between gap-3">
              <span className="rounded-full border border-primary/25 bg-primary/10 px-2.5 py-1 text-[11px] font-bold text-primary">{rq.id}</span>
              <span className="rounded-xl bg-surface-soft p-2 text-muted transition-colors group-hover:text-primary"><Icon size={18} aria-hidden="true" /></span>
            </div>
            <p className="mt-4 text-sm font-semibold leading-6 text-text-heading">{rq.question}</p>
            <div className="mt-auto flex items-end justify-between gap-3 pt-5">
              <span className="text-xs font-semibold text-primary">{rq.focus}</span>
              <ArrowUpRight size={16} className="text-muted transition-colors group-hover:text-primary" aria-hidden="true" />
            </div>
          </Link>
        );
      })}
    </div>
  );
}
