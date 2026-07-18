import type { OverviewResponse } from '../../types/api';
import { formatCount, metadataValue } from './overviewUtils';

export default function TopThemesPanel({ overview }: { overview: OverviewResponse }) {
  const total = overview.top_themes.reduce((sum, theme) => sum + theme.count, 0);
  const provider = metadataValue(overview.model_metadata, [
    'configured_primary_provider',
    'provider',
  ]);
  const model = metadataValue(overview.model_metadata, [
    'configured_primary_model',
    'model',
  ]);

  return (
    <section className="bg-panel border border-border rounded-xl p-5 flex flex-col h-full">
      <div>
        <h3 className="text-sm font-bold text-text-heading">Top Themes</h3>
        <p className="mt-1 text-xs text-muted">Theme labels are downstream of LDA keywords; they do not replace topic modeling.</p>
      </div>
      {overview.top_themes.length === 0 ? (
        <div className="flex-grow min-h-48 flex items-center justify-center text-center">
          <div>
            <p className="font-semibold text-text-heading">No theme summary available</p>
            <p className="mt-2 text-sm text-muted">This run did not return top theme counts.</p>
          </div>
        </div>
      ) : (
        <div className="mt-5 space-y-4">
          {overview.top_themes.slice(0, 6).map((theme) => {
            const percentage = total > 0 ? (theme.count / total) * 100 : 0;
            return (
              <div key={theme.name}>
                <div className="flex items-center justify-between gap-4 text-xs">
                  <span className="font-medium text-text-heading truncate">{theme.name}</span>
                  <span className="text-muted">{formatCount(theme.count)}</span>
                </div>
                <div className="mt-2 h-2.5 rounded-full bg-border overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${Math.max(2, percentage)}%` }}
                    aria-label={`${theme.name}: ${theme.count}`}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
      <dl className="mt-auto pt-5 grid grid-cols-1 gap-2 text-xs">
        <div className="flex justify-between gap-3 border-t border-border pt-3">
          <dt className="text-muted">Provider</dt>
          <dd className="text-text-heading font-medium text-right">{provider || 'Unavailable'}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Model</dt>
          <dd className="text-text-heading font-medium text-right">{model || 'Unavailable'}</dd>
        </div>
      </dl>
    </section>
  );
}
