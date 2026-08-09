import type { EvolutionPath } from '../../../types/api';
import { formatCount, formatPeriod } from '../../overview/overviewUtils';

interface Props {
  path: EvolutionPath;
}

export default function SelectedPathContext({ path }: Props) {
  const start = path.steps[0];
  const end = path.steps[path.steps.length - 1];

  return (
    <section
      className="mt-5 rounded-2xl border border-primary/30 bg-primary/5 p-4"
      aria-label={`Selected path ${path.display_order} context`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">Selected path</p>
          <h3 className="mt-1 text-base font-bold text-text-heading">
            Path {path.display_order}
            <span className="ml-2 text-sm font-semibold text-muted">
              {formatRange(path.months)} · {path.duration} months
            </span>
          </h3>
        </div>
        <span className="rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-semibold text-primary">Shared detail context</span>
      </div>

      <div className="mt-4 overflow-x-auto pb-1">
        <div className="flex min-w-max items-center">
          {path.steps.map((step, index) => (
            <div key={`${step.step_index}-${step.community_key}`} className="flex items-center">
              {index > 0 && (
                <div className="mx-2 flex min-w-[72px] flex-col items-center gap-1">
                  <span className="rounded-full border border-primary/25 bg-bg/50 px-2 py-0.5 text-[11px] font-semibold text-text-heading">
                    {step.jaccard_from_previous?.toFixed(2) ?? '—'}
                  </span>
                  <span className="h-0.5 w-full rounded-full bg-primary/60" aria-hidden="true" />
                </div>
              )}
              <div className="rounded-xl border border-primary/30 bg-surface/70 px-3 py-2 text-center">
                <p className="text-xs font-bold text-text-heading">C{step.community_id}</p>
                <p className="mt-0.5 text-[11px] text-muted">{formatPeriod(step.month)}</p>
                <p className="mt-1 text-[11px] font-semibold text-primary">{formatCount(step.member_count)} members</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <dl className="mt-4 grid gap-3 border-t border-primary/15 pt-4 sm:grid-cols-3">
        <ContextMetric label="Duration" value={`${path.duration} months`} />
        <ContextMetric label="Average Jaccard" value={path.average_jaccard.toFixed(2)} />
        <ContextMetric
          label="Members"
          value={`${formatCount(start?.member_count ?? 0)} → ${formatCount(end?.member_count ?? 0)}`}
        />
      </dl>
    </section>
  );
}

function ContextMetric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold text-muted">{label}</dt>
      <dd className="mt-1 text-sm font-bold text-text-heading">{value}</dd>
    </div>
  );
}

function formatRange(months: string[]): string {
  if (months.length === 0) return 'No periods';
  const first = formatPeriod(months[0]);
  const last = formatPeriod(months[months.length - 1]);
  return months.length === 1 ? first : `${first} → ${last}`;
}
