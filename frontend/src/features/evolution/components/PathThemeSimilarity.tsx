import type { EvolutionThemeType, PathThemeSimilarityResponse } from '../../../types/api';
import { normalizedTextList } from '../../../utils/artifactValues';

interface Props {
  similarity: PathThemeSimilarityResponse;
  themeType: EvolutionThemeType;
  onThemeTypeChange: (themeType: EvolutionThemeType) => void;
}

const TYPES: Array<{ value: EvolutionThemeType; label: string }> = [
  { value: 'general', label: 'General' },
  { value: 'absolute', label: 'IF' },
  { value: 'weighted', label: 'WIF' },
];

export default function PathThemeSimilarity({ similarity, themeType, onThemeTypeChange }: Props) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-text-heading">Monthly theme progression</h3>
          <p className="mt-1 text-xs text-muted">Theme labels remain the raw generated evolution evidence; no Plan 039 canonical clustering is applied here.</p>
        </div>
        <div className="inline-flex rounded-xl border border-border bg-bg/30 p-1" aria-label="Theme perspective">
          {TYPES.map((item) => (
            <button
              type="button"
              key={item.value}
              onClick={() => onThemeTypeChange(item.value)}
              aria-pressed={themeType === item.value}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${themeType === item.value ? 'bg-primary text-white' : 'text-muted hover:text-text-heading'}`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {similarity.months.map((month, index) => (
          <article key={`${month}-${similarity.communities[index]}`} className="relative rounded-2xl border border-border/70 bg-surface-soft/25 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-primary">{month}</p>
            <p className="mt-1 text-xs text-muted">{similarity.communities[index]}</p>
            <p className="mt-3 text-sm font-semibold leading-6 text-text-heading">{formatTheme(similarity.themes[index])}</p>
            {index < similarity.months.length - 1 && (
              <p className="mt-3 text-xs text-muted">Next-month similarity <strong className="text-text-heading">{(similarity.matrix[index]?.[index + 1] ?? 0).toFixed(2)}</strong></p>
            )}
          </article>
        ))}
      </div>

      <div>
        <h3 className="text-sm font-bold text-text-heading">Cosine-similarity heatmap</h3>
        <p className="mt-1 text-xs text-muted">Pairwise semantic consistency across every month in the selected persistent path.</p>
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-[560px] border-separate border-spacing-1 text-center text-xs">
            <thead>
              <tr><th className="p-2 text-left text-muted">Month</th>{similarity.months.map((month) => <th key={month} className="p-2 text-muted">{month}</th>)}</tr>
            </thead>
            <tbody>
              {similarity.months.map((month, row) => (
                <tr key={month}>
                  <th className="p-2 text-left font-semibold text-text-heading">{month}</th>
                  {similarity.months.map((column, col) => {
                    const score = similarity.matrix[row]?.[col] ?? 0;
                    return (
                      <td
                        key={`${month}-${column}`}
                        className="rounded-lg border border-border/50 p-3 font-bold text-text-heading"
                        style={{ backgroundColor: `color-mix(in srgb, var(--color-primary) ${Math.round(10 + score * 70)}%, var(--color-surface-soft))` }}
                        title={`${month} vs ${column}: ${score.toFixed(3)}`}
                      >
                        {score.toFixed(2)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-muted">
          Embedding contract: {similarity.embedding_model?.replace('sentence-transformers/', '') || 'Unavailable'}{similarity.embedding_model_revision ? ` @ ${similarity.embedding_model_revision.slice(0, 12)}…` : ''}
        </p>
      </div>
    </div>
  );
}

function formatTheme(value: string | undefined): string {
  const labels = normalizedTextList(value);
  return labels.length > 0 ? labels.join(' · ') : (value || 'No theme label');
}
