import SkeletonCard from '../SkeletonCard';

interface LoadingStateProps {
  title?: string;
  message?: string;
}

/**
 * Full-page loading placeholder. Shows shimmer skeleton cards instead of a
 * plain spinner so the user sees the approximate layout before data arrives.
 */
export default function LoadingState({
  title = 'Loading dashboard data',
  message = 'Reading the selected run from the dashboard API.',
}: LoadingStateProps) {
  return (
    <section
      role="status"
      aria-live="polite"
      aria-busy="true"
      className="space-y-6 animate-fade-in-up"
    >
      {/* Page header shimmer */}
      <div className="flex items-center gap-4">
        <div className="shimmer w-10 h-10 rounded-xl" />
        <div className="space-y-2">
          <div className="shimmer h-5 w-48 rounded" />
          <div className="shimmer h-3 w-72 rounded" />
        </div>
      </div>

      {/* KPI card row shimmer */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <SkeletonCard key={i} rows={2} />
        ))}
      </div>

      {/* Two chart shimmer blocks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SkeletonCard chart />
        <SkeletonCard chart />
      </div>

      {/* Status label */}
      <div className="flex items-center justify-center gap-3 pt-2 text-muted text-sm">
        <div className="w-4 h-4 rounded-full border-2 border-border border-t-primary animate-spin" aria-hidden="true" />
        <span>
          <strong className="text-text-heading">{title}</strong>
          {' — '}
          {message}
        </span>
      </div>
    </section>
  );
}
