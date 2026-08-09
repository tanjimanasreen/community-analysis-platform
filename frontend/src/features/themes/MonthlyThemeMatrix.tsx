import { ArrowDown, ArrowUp, Minus } from 'lucide-react';
import type { ClusteredThemeTimelineResponse } from '../../types/api';
import { stableThemeColor } from './themeModel';
import { monthlyTopFive, periodLabel } from './themeTrendModel';
import { CompactThemeLabel, ThemeKeywordChip } from './CompactThemeText';

interface Props {
  response?: ClusteredThemeTimelineResponse | null;
  selectedPeriod?: string | null;
  selectedThemeId?: string | null;
  onSelectTheme: (period: string, themeId: string, name: string) => void;
  limit?: number;
}

export default function MonthlyThemeMatrix({
  response,
  selectedPeriod = null,
  selectedThemeId = null,
  onSelectTheme,
  limit = 5,
}: Props) {
  if (!response) return null;
  if (!response.complete) {
    return (
      <section className="panel p-5">
        <p role="status" className="text-sm text-muted">
          The selected timeline is incomplete, so monthly rankings are not shown.
        </p>
      </section>
    );
  }

  const monthly = monthlyTopFive(response, limit);
  const gridStyle = {
    gridTemplateColumns: `repeat(${Math.max(1, monthly.length)}, minmax(17rem, 1fr))`,
    minWidth: monthly.length > 2 ? `${monthly.length * 288}px` : undefined,
  };

  return (
    <section className="panel p-5" aria-labelledby="monthly-theme-matrix-heading">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="monthly-theme-matrix-heading" className="text-lg font-bold text-text-heading">
            Top Themes by Month
          </h2>
          <p className="mt-1 max-w-4xl text-xs text-muted">
            Canonical semantic themes are ranked independently each month by distinct matched IF/WIF community-pair coverage. Prominent keywords come from the upstream general-theme LDA evidence for those pairs.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
            Up to {limit} per month
          </span>
          <span className="rounded-full border border-border bg-bg/30 px-3 py-1 text-xs font-semibold text-muted">
            {monthly.length} {monthly.length === 1 ? 'month' : 'months'}
          </span>
        </div>
      </div>

      {monthly.length === 0 ? (
        <p className="mt-5 text-sm text-muted">No monthly matched-community theme summaries are available.</p>
      ) : (
        <div className="mt-5 overflow-x-auto pb-2">
          <div className="grid gap-4" style={gridStyle}>
            {monthly.map((group) => (
              <article key={group.period} className="rounded-xl border border-border bg-bg/20 p-4">
                <div className="flex items-start justify-between gap-3 border-b border-border/60 pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-text-heading">{periodLabel(group.period)}</h3>
                    <p className="mt-1 text-xs text-muted">
                      {group.totalThemedCommunityPairs} themed matched pairs
                    </p>
                  </div>
                  {selectedPeriod === group.period && (
                    <span className="rounded-full bg-primary/10 px-2 py-1 text-xs font-semibold text-primary">
                      Evidence month
                    </span>
                  )}
                </div>

                {group.themes.length === 0 ? (
                  <p className="mt-4 text-sm text-muted">No themes are available for this month.</p>
                ) : (
                  <ol className="mt-4 space-y-3">
                    {group.themes.map((theme) => {
                      const selected = selectedPeriod === group.period && selectedThemeId === theme.themeId;
                      return (
                        <li key={theme.themeId}>
                          <button
                            type="button"
                            aria-pressed={selected}
                            onClick={() => onSelectTheme(group.period, theme.themeId, theme.name)}
                            className={`block w-full rounded-lg border p-3 text-left transition-colors ${selected ? 'border-primary bg-primary/10' : 'border-border/70 bg-surface-soft/20 hover:bg-surface-soft/50'}`}
                          >
                            <div className="flex items-start gap-3">
                              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-surface-soft text-xs font-bold text-text-heading">
                                {theme.rank}
                              </span>
                              <div className="min-w-0 flex-1">
                                <div className="flex flex-wrap items-start justify-between gap-2">
                                  <CompactThemeLabel text={theme.name} className="text-sm font-semibold text-text-heading" />
                                  <span className="text-xs font-semibold text-text-heading">{theme.percentage.toFixed(1)}%</span>
                                </div>
                                <p className="mt-1 text-xs text-muted">
                                  {theme.communityCount} of {group.totalThemedCommunityPairs} themed matched pairs
                                </p>
                                <div className="mt-2 h-2.5 rounded-full bg-surface-soft" aria-hidden="true">
                                  <span
                                    className="block h-2.5 rounded-full"
                                    style={{
                                      width: `${theme.percentage === 0 ? 0 : Math.max(2, theme.percentage)}%`,
                                      backgroundColor: stableThemeColor(theme.themeId),
                                    }}
                                  />
                                </div>
                                <div className="mt-3 flex flex-wrap gap-1.5" aria-label={`Prominent LDA keywords for ${theme.name}`}>
                                  {theme.keywords.slice(0, 5).map((keyword) => (
                                    <ThemeKeywordChip key={keyword} keyword={keyword} className="bg-bg/40" />
                                  ))}
                                  {theme.keywords.length === 0 && <span className="text-xs text-muted">Keyword evidence unavailable</span>}
                                </div>
                              </div>
                              <RankMovement movement={theme.rankMovement} />
                            </div>
                          </button>
                        </li>
                      );
                    })}
                  </ol>
                )}
                {group.excludedRecordsMissingGeneralTheme > 0 && (
                  <p className="mt-3 text-xs text-muted">
                    {group.excludedRecordsMissingGeneralTheme} matched source records without a saved general theme were excluded from clustering.
                  </p>
                )}
                {group.excludedRecordsAmbiguousGeneralThemeSerialization > 0 && (
                  <p className="mt-2 text-xs text-warning">
                    {group.excludedRecordsAmbiguousGeneralThemeSerialization} matched source {group.excludedRecordsAmbiguousGeneralThemeSerialization === 1 ? 'record contained' : 'records contained'} an ambiguous legacy general-theme serialization and {group.excludedRecordsAmbiguousGeneralThemeSerialization === 1 ? 'was' : 'were'} excluded from semantic clustering.
                  </p>
                )}
              </article>
            ))}
          </div>
        </div>
      )}

      <p className="mt-4 text-xs text-muted">
        Related general GPT labels are clustered upstream and canonicalized across months. A matched pair may still support multiple canonical themes, so percentages within a month need not sum to 100%.
      </p>
    </section>
  );
}

function RankMovement({ movement }: { movement: number | null }) {
  if (movement === null) return <span className="sr-only">Not ranked in the previous month</span>;
  if (movement > 0) {
    return <span title={`Up ${movement} ranks`} className="flex items-center gap-1 text-xs text-success"><ArrowUp size={14} />{movement}</span>;
  }
  if (movement < 0) {
    return <span title={`Down ${Math.abs(movement)} ranks`} className="flex items-center gap-1 text-xs text-warning"><ArrowDown size={14} />{Math.abs(movement)}</span>;
  }
  return <span title="No rank change" className="text-muted"><Minus size={14} /></span>;
}
