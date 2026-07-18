interface SimilarityMatrixProps {
  matrix: number[][];
  labels: string[];
}

function normalizedMatrix(matrix: number[][], labels: string[]): number[][] {
  return labels.map((_, rowIndex) =>
    labels.map((_, columnIndex) => {
      const value = matrix[rowIndex]?.[columnIndex];
      return typeof value === 'number' && Number.isFinite(value) ? value : 0;
    }),
  );
}

export default function SimilarityMatrix({ matrix, labels }: SimilarityMatrixProps) {
  if (labels.length === 0 || matrix.length === 0) return null;
  const values = normalizedMatrix(matrix, labels);

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-separate border-spacing-1 text-xs" aria-label="Theme similarity matrix">
        <caption className="sr-only">
          Cosine-similarity values supplied by the selected run's theme-similarity artifact.
        </caption>
        <thead>
          <tr>
            <th className="p-2 text-left text-muted">Theme</th>
            {labels.map((label, index) => (
              <th key={`${label}-${index}`} className="max-w-28 truncate p-2 text-center text-muted" title={label}>
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {labels.map((label, rowIndex) => (
            <tr key={`${label}-${rowIndex}`}>
              <th className="max-w-40 truncate p-2 text-left font-medium text-text-heading" title={label}>
                {label}
              </th>
              {values[rowIndex].map((value, columnIndex) => (
                <td
                  key={`${rowIndex}-${columnIndex}`}
                  className="min-w-16 rounded p-2 text-center font-semibold text-text-heading"
                  style={{ backgroundColor: `rgba(122, 162, 247, ${Math.max(0.08, Math.min(0.85, value))})` }}
                  title={`${labels[rowIndex]} and ${labels[columnIndex]}: ${value.toFixed(3)}`}
                >
                  {value.toFixed(2)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
