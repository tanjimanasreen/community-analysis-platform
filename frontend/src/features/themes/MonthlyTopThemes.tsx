import { ArrowDown, ArrowUp, Minus } from 'lucide-react';
import type { MonthlyThemeTrendResponse, MonthlyThemeTrendSummary } from '../../types/api';
import { periodLabel } from './themeTrendModel';
import { stableThemeColor } from './themeModel';

interface MonthlyTopThemesProps {
  response?: MonthlyThemeTrendResponse | null;
  previous?: MonthlyThemeTrendSummary | null;
  selectedTheme?: string | null;
  onSelectTheme: (name: string | null) => void;
  limit?: number;
}

export default function MonthlyTopThemes({
  response,
  previous,
  selectedTheme = null,
  onSelectTheme,
  limit = 5,
}: MonthlyTopThemesProps) {
  if (!response) return null;
  if (!response.complete) {
    return <Incomplete message="The selected month is incomplete, so no ranking is shown." />;
  }

  const themes = response.themes.slice(0, Math.max(0, limit));
  const previousRanks = new Map(
    (previous?.themes ?? []).map((theme, index) => [theme.name, index + 1]),
  );

  return (
    <section className="panel p-5" aria-labelledby="monthly-theme-heading">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="monthly-theme-heading" className="text-sm font-bold text-text-heading">
            Top Themes · {periodLabel(response.period)}
          </h2>
          <p className="mt-1 text-xs text-muted">
            Exact labels ranked by distinct matched IF/WIF community-pair coverage.
          </p>
        </div>
        <span className="rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
          {response.total_themed_community_pairs} themed matched pairs
        </span>
      </div>

      {themes.length === 0 ? (
        <p className="mt-5 text-sm text-muted">No themed matched community pairs are available for this month.</p>
      ) : (
        <div className="mt-5 space-y-3">
          {themes.map((theme, index) => {
            const rank = index + 1;
            const previousRank = previousRanks.get(theme.name);
            const movement = previousRank ? previousRank - rank : null;
            const selected = selectedTheme === theme.name;
            return (
              <button
                key={theme.name}
                type="button"
                aria-pressed={selected}
                onClick={() => onSelectTheme(selected ? null : theme.name)}
                className={`block w-full rounded-xl border p-4 text-left transition-colors ${selected ? 'border-primary bg-primary/10' : 'border-border bg-bg/20 hover:bg-surface-soft/40'}`}
              >
                <div className="flex items-start gap-3">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-surface-soft text-xs font-bold text-text-heading">{rank}</span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h3 className="break-words text-sm font-semibold text-text-heading">{theme.name}</h3>
                      <span className="text-xs font-semibold text-text-heading">{theme.percentage.toFixed(1)}%</span>
                    </div>
                    <p className="mt-1 text-xs text-muted">
                      {theme.community_count} of {response.total_themed_community_pairs} themed matched pairs
                    </p>
                    <div className="mt-3 h-2.5 rounded-full bg-surface-soft" aria-hidden="true">
                      <span
                        className="block h-2.5 rounded-full"
                        style={{ width: `${Math.max(2, theme.percentage)}%`, backgroundColor: stableThemeColor(theme.name) }}
                      />
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2" aria-label={`Supporting LDA keywords for ${theme.name}`}>
                      {theme.keywords.slice(0, 5).map((keyword) => (
                        <span key={keyword} className="rounded-full border border-border bg-surface-soft/60 px-2.5 py-1 text-xs text-muted">{keyword}</span>
                      ))}
                      {theme.keywords.length === 0 && <span className="text-xs text-muted">Keyword evidence unavailable</span>}
                    </div>
                  </div>
                  <RankMovement movement={movement} />
                </div>
              </button>
            );
          })}
        </div>
      )}

      <p className="mt-4 text-xs text-muted">
        A pair may carry more than one exact label, so percentages need not sum to 100%. {response.excluded_records_without_pair} source records without either community ID were excluded.
      </p>
    </section>
  );
}

function RankMovement({ movement }: { movement: number | null }) {
  if (movement === null) return <span className="sr-only">No prior-month rank</span>;
  if (movement > 0) return <span title={`Up ${movement}`} className="flex items-center gap-1 text-xs text-success"><ArrowUp size={14} />{movement}</span>;
  if (movement < 0) return <span title={`Down ${Math.abs(movement)}`} className="flex items-center gap-1 text-xs text-warning"><ArrowDown size={14} />{Math.abs(movement)}</span>;
  return <span title="No rank change" className="text-muted"><Minus size={14} /></span>;
}

function Incomplete({ message }: { message: string }) {
  return <section className="panel p-5"><p role="status" className="text-sm text-muted">{message}</p></section>;
}
