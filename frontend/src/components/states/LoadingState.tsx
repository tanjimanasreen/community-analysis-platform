interface LoadingStateProps {
  title?: string;
  message?: string;
}

export default function LoadingState({
  title = 'Loading dashboard data',
  message = 'Reading the selected run from the dashboard API.',
}: LoadingStateProps) {
  return (
    <section
      className="min-h-56 rounded-2xl border border-border bg-panel/80 p-8 flex items-center justify-center"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="max-w-md text-center">
        <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-border border-t-primary" />
        <h2 className="text-lg font-semibold text-text-heading">{title}</h2>
        <p className="mt-2 text-sm text-muted">{message}</p>
      </div>
    </section>
  );
}
