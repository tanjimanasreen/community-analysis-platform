import type { PathMembershipRecord } from '../../../types/api';
import { formatCount } from '../../overview/overviewUtils';

interface Props { records: PathMembershipRecord[]; }

export default function MemberMobilityFlow({ records }: Props) {
  const maxCount = Math.max(1, ...records.flatMap((record) => [record.member_count, record.existing_count, record.new_count, record.reappearing_count, record.lost_count]));
  if (records.length === 0) return <p className="text-sm text-muted">No member-mobility records are available for this path.</p>;

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_260px]">
      <div className="space-y-3">
        {records.map((record, index) => {
          const trulyNew = Math.max(0, record.new_count - record.reappearing_count);
          return (
            <article key={record.community_key} className="rounded-2xl border border-border/70 bg-surface-soft/25 p-4">
              <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
                <div>
                  <p className="text-sm font-bold text-text-heading">{record.month} · Community {record.community_id}</p>
                  <p className="text-xs text-muted">{formatCount(record.member_count)} members{record.size_delta === null ? '' : ` · ${record.size_delta >= 0 ? '+' : ''}${record.size_delta} vs previous month`}</p>
                </div>
                {index === 0 && <span className="rounded-full bg-primary/10 px-2 py-1 text-[11px] font-semibold text-primary">Path start</span>}
              </div>
              <div className="space-y-2">
                {index === 0 ? (
                  <MobilityBar label="Baseline members" value={record.member_count} max={maxCount} tone="success" />
                ) : (
                  <>
                    <MobilityBar label="Retained" value={record.existing_count} max={maxCount} tone="success" />
                    <MobilityBar label="Newly joined" value={trulyNew} max={maxCount} tone="primary" />
                    <MobilityBar label="Reappeared" value={record.reappearing_count} max={maxCount} tone="secondary" />
                    <MobilityBar label="Exited after prior month" value={record.lost_count} max={maxCount} tone="danger" />
                  </>
                )}
              </div>
            </article>
          );
        })}
      </div>
      <aside className="rounded-2xl border border-border/70 bg-bg/20 p-4 text-sm">
        <h3 className="font-bold text-text-heading">How to read mobility</h3>
        <p className="mt-2 leading-6 text-muted">
          Retained members occur in both consecutive communities. Newly joined members have not appeared earlier in this path; reappeared members return after at least one-month absence. Exited members were present in the prior step but not the current one.
        </p>
        <p className="mt-3 text-xs text-muted">
          The underlying thesis calculation reports reappearing members as a subset of the current-minus-previous set. The display separates that subset so categories are visually non-overlapping.
        </p>
      </aside>
    </div>
  );
}

function MobilityBar({ label, value, max, tone }: { label: string; value: number; max: number; tone: 'success' | 'primary' | 'secondary' | 'danger' }) {
  const width = value === 0 ? 0 : Math.max(4, Math.round((value / max) * 100));
  const classes = { success: 'bg-success', primary: 'bg-primary', secondary: 'bg-secondary', danger: 'bg-danger' } as const;
  return (
    <div className="grid grid-cols-[130px_minmax(0,1fr)_48px] items-center gap-2 text-xs">
      <span className="text-muted">{label}</span>
      <span className="h-2.5 overflow-hidden rounded-full bg-bg/60"><span className={`block h-full rounded-full ${classes[tone]}`} style={{ width: `${width}%` }} /></span>
      <strong className="text-right text-text-heading">{formatCount(value)}</strong>
    </div>
  );
}
