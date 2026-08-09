import type { DominantThemeTrend } from '../../types/api';
import { periodLabel } from './themeTrendModel';

export default function DominantThemeTimeline({ theme }: { theme?: DominantThemeTrend | null }) {
  if (!theme) {
    return (
      <section className="panel p-5">
        <h2 className="text-sm font-bold text-text-heading">Most Discussed Exact Theme · Timeline</h2>
        <p className="mt-4 text-sm text-muted">No exact theme label is available in the selected range.</p>
      </section>
    );
  }
  const max = Math.max(1, ...theme.series.map((point) => point.community_count));

  return (
    <section className="panel p-5" aria-labelledby="dominant-theme-heading">
      <h2 id="dominant-theme-heading" className="text-sm font-bold text-text-heading">Most Discussed Exact Theme · Timeline</h2>
      <p className="mt-1 text-xs text-muted">Variants and synonyms are not merged.</p>
      <div className="mt-4 rounded-xl border border-primary/30 bg-primary/10 p-4">
        <p className="text-base font-bold text-text-heading">{theme.name}</p>
        <div className="mt-3 grid grid-cols-2 gap-3 text-xs sm:grid-cols-3">
          <Stat label="Community-month count" value={theme.total_community_month_count} />
          <Stat label="Months present" value={theme.months_present} />
          <Stat label="Peak" value={`${periodLabel(theme.peak_period)} · ${theme.peak_month_count}`} />
        </div>
      </div>
      <div className="mt-5 space-y-3" aria-label={`Monthly coverage for ${theme.name}`}>
        {theme.series.map((point) => (
          <div key={point.period} className="grid grid-cols-[5rem_minmax(0,1fr)_4.5rem] items-center gap-3 text-xs">
            <span className="text-muted">{periodLabel(point.period)}</span>
            <div className="h-2.5 rounded-full bg-surface-soft">
              <span className="block h-2.5 rounded-full bg-primary" style={{ width: `${point.community_count === 0 ? 0 : Math.max(2, (point.community_count / max) * 100)}%` }} />
            </div>
            <span className="text-right font-semibold text-text-heading">{point.community_count} · {point.percentage.toFixed(1)}%</span>
          </div>
        ))}
      </div>
      <div className="mt-5">
        <p className="text-xs font-semibold text-muted">Persistent LDA keyword evidence</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {theme.keywords.map((keyword) => <span key={keyword} className="rounded-full border border-border bg-surface-soft/60 px-2.5 py-1 text-xs text-muted">{keyword}</span>)}
          {theme.keywords.length === 0 && <span className="text-xs text-muted">Unavailable</span>}
        </div>
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return <div><p className="text-muted">{label}</p><p className="mt-1 font-bold text-text-heading">{value}</p></div>;
}
