import { Link } from 'react-router-dom';
import type { ThemesResponse } from '../../types/api';
import ArtifactUnavailableState from '../../components/states/ArtifactUnavailableState';
import ErrorState from '../../components/states/ErrorState';
import LoadingState from '../../components/states/LoadingState';
import { selectedMonthThemeSummary } from '../themes/themeModel';
import { formatCount, formatPeriod } from './overviewUtils';

interface TopThemesPanelProps {
  period: string;
  themes?: ThemesResponse | null;
  hasArtifact?: boolean;
  isLoading?: boolean;
  error?: unknown;
  onRetry?: () => void;
  search?: string;
}

export default function TopThemesPanel({
  period,
  themes,
  hasArtifact = true,
  isLoading = false,
  error,
  onRetry,
  search = '',
}: TopThemesPanelProps) {
  if (isLoading) return <LoadingState title="Loading selected-month themes" />;
  if (!hasArtifact) {
    return (
      <ArtifactUnavailableState
        artifactName="Selected-month themes"
        message="The selected run does not list monthly theme artifacts."
        action={<Link className="text-primary hover:underline" to={`/methodology${search}`}>Why this artifact is optional</Link>}
      />
    );
  }
  if (error) return <ErrorState error={error} title="Selected-month themes could not be loaded" onRetry={onRetry} />;

  const summary = selectedMonthThemeSummary(themes);
  const periodLabel = formatPeriod(period);

  if (summary.incomplete) {
    return (
      <section className="panel overview-top-themes-panel">
        <PanelHeading periodLabel={periodLabel} />
        <div className="overview-insight-safe-cap" role="status">
          <p className="font-semibold text-text-heading">Complete monthly ranking unavailable</p>
          <p>
            The API returned {formatCount(summary.returnedRecords)} of {formatCount(summary.totalRecords)} theme records.
            A partial top-five ranking would be misleading, so no bars are shown.
          </p>
          <Link className="text-primary hover:underline" to={`/thematic${search}`}>Open Thematic Analysis</Link>
        </div>
      </section>
    );
  }

  return (
    <section className="panel overview-top-themes-panel">
      <PanelHeading periodLabel={periodLabel} />
      {summary.themes.length === 0 ? (
        <div className="overview-insight-empty">
          <div>
            <p className="font-semibold text-text-heading">No theme summary available</p>
            <p className="mt-2 text-sm text-muted">No themed matched community pairs were returned for this month.</p>
          </div>
        </div>
      ) : (
        <div className="overview-top-themes-list">
          {summary.themes.map((theme) => (
            <article className="overview-top-theme" key={theme.name}>
              <div className="overview-top-theme__heading">
                <h4 title={theme.name}>{theme.name}</h4>
                <strong>{theme.percentage.toFixed(1)}%</strong>
              </div>
              <p>
                {formatCount(theme.communityCount)} of {formatCount(summary.totalThemedCommunityPairs)} themed communities
              </p>
              <div className="overview-top-theme__bar" aria-label={`${theme.name}: ${theme.communityCount} of ${summary.totalThemedCommunityPairs} themed community pairs`}>
                <span style={{ width: `${Math.max(2, theme.percentage)}%`, backgroundColor: theme.color }} />
              </div>
              {theme.keywords.length > 0 && (
                <div className="overview-top-theme__keywords" aria-label={`Supporting LDA keywords for ${theme.name}`}>
                  {theme.keywords.map((keyword) => <span key={keyword}>{keyword}</span>)}
                </div>
              )}
            </article>
          ))}
        </div>
      )}
      {summary.totalThemedCommunityPairs > 0 && (
        <p className="overview-top-themes-panel__note">
          Denominator: {formatCount(summary.totalThemedCommunityPairs)} distinct matched IF/WIF community pairs with at least one theme.
          A pair may carry multiple themes, so percentages need not sum to 100%.
        </p>
      )}
    </section>
  );
}

function PanelHeading({ periodLabel }: { periodLabel: string }) {
  return (
    <div>
      <h3 className="text-sm font-bold text-text-heading">Top Themes · {periodLabel}</h3>
      <p className="mt-1 text-xs text-muted">
        Top five exact theme labels by distinct matched community pair. Theme labels remain downstream of LDA keywords.
      </p>
    </div>
  );
}
