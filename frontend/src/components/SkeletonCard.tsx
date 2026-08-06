interface SkeletonCardProps {
  /** Number of shimmer rows to render inside the card */
  rows?: number;
  /** Show a tall "chart" placeholder instead of rows */
  chart?: boolean;
  className?: string;
}

/**
 * Reusable shimmer skeleton used as a loading placeholder for any card.
 * Uses the `.shimmer` utility class defined in index.css.
 */
export default function SkeletonCard({
  rows = 3,
  chart = false,
  className = '',
}: SkeletonCardProps) {
  return (
    <div
      className={`bg-panel border border-border rounded-xl p-5 overflow-hidden ${className}`}
      aria-hidden="true"
    >
      {/* Icon + title row */}
      <div className="flex items-center gap-3 mb-4">
        <div className="shimmer w-10 h-10 rounded-lg" />
        <div className="shimmer h-4 w-32 rounded" />
      </div>

      {chart ? (
        /* Chart placeholder */
        <div className="shimmer w-full h-48 rounded-lg" />
      ) : (
        /* Text row placeholders */
        <div className="space-y-3">
          {Array.from({ length: rows }).map((_, i) => (
            <div
              key={i}
              className="shimmer h-3 rounded"
              style={{ width: `${85 - i * 12}%` }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
