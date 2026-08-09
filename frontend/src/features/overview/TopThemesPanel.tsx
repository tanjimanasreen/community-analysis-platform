import { Link } from 'react-router-dom';
import type { MonthlyClusteredThemeResponse } from '../../types/api';
import ArtifactUnavailableState from '../../components/states/ArtifactUnavailableState';
import ErrorState from '../../components/states/ErrorState';
import LoadingState from '../../components/states/LoadingState';
import { stableThemeColor } from '../themes/themeModel';
import { ThemeKeywordChip } from '../themes/CompactThemeText';
import { formatCount, formatPeriod } from './overviewUtils';

interface TopThemesPanelProps {
  period: string;
  themes?: MonthlyClusteredThemeResponse | null;
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
        artifactName="Clustered monthly themes"
        message="The selected run does not list upstream clustered-theme artifacts."
        action={<Link className="text-primary hover:underline" to={`/methodology${search}`}>Why this artifact is optional</Link>}
      />
    );
  }
  if (error) return <ErrorState error={error} title="Selected-month themes could not be loaded" onRetry={onRetry} />;

  const topThemes = themes?.themes.slice(0, 5) ?? [];
  const totalPairs = themes?.total_themed_community_pairs ?? 0;
  const periodLabel = formatPeriod(period);

  return (
    <section className="panel overview-top-themes-panel">
      <PanelHeading periodLabel={periodLabel} />
      {topThemes.length === 0 ? (
        <div className="overview-insight-empty">
          <div>
            <p className="font-semibold text-text-heading">No clustered theme summary available</p>
            <p className="mt-2 text-sm text-muted">No clustered themes were published for matched community pairs in this month.</p>
          </div>
        </div>
      ) : (
        <div className="overview-top-themes-list">
          {topThemes.map((theme) => {
            const color = stableThemeColor(theme.theme_id);
            return (
              <article className="overview-top-theme" key={theme.theme_id}>
                <div className="overview-top-theme__heading">
                  <h4 title={theme.name}>{theme.name}</h4>
                  <strong>{theme.percentage.toFixed(1)}%</strong>
                </div>
                <p>
                  {formatCount(theme.community_count)} of {formatCount(totalPairs)} themed matched pairs
                </p>
                <div className="overview-top-theme__bar" aria-label={`${theme.name}: ${theme.community_count} of ${totalPairs} themed community pairs`}>
                  <span style={{ width: `${Math.max(2, theme.percentage)}%`, backgroundColor: color }} />
                </div>
                {theme.keywords.length > 0 && (
                  <div className="overview-top-theme__keywords" aria-label={`Supporting LDA keywords for ${theme.name}`}>
                    {theme.keywords.slice(0, 3).map((keyword) => (
                      <ThemeKeywordChip key={keyword} keyword={keyword} className="overview-top-theme__keyword" />
                    ))}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
      {(themes?.excluded_records_ambiguous_general_theme_serialization ?? 0) > 0 && (
        <p className="overview-top-themes-panel__note text-warning">
          {themes?.excluded_records_ambiguous_general_theme_serialization} matched source {themes?.excluded_records_ambiguous_general_theme_serialization === 1 ? 'record contained' : 'records contained'} an ambiguous legacy general-theme serialization and {themes?.excluded_records_ambiguous_general_theme_serialization === 1 ? 'was' : 'were'} excluded from semantic clustering.
        </p>
      )}
      {totalPairs > 0 && (
        <p className="overview-top-themes-panel__note">
          Denominator: {formatCount(totalPairs)} distinct matched IF/WIF community pairs with at least one general theme.
          Related general GPT labels are clustered and canonicalized upstream; a pair may support multiple canonical themes.
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
        Top five canonical semantic themes by distinct matched community-pair coverage. Labels remain downstream of LDA keywords.
      </p>
    </div>
  );
}
