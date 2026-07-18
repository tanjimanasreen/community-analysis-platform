import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  message?: string;
}

export default function EmptyState({
  title = 'No records available',
  message = 'The selected run does not contain records for this view.',
}: EmptyStateProps) {
  return (
    <section
      className="min-h-56 rounded-2xl border border-border bg-panel/80 p-8 flex items-center justify-center"
      aria-live="polite"
    >
      <div className="max-w-md text-center">
        <Inbox className="mx-auto text-muted" size={30} />
        <h2 className="mt-4 text-lg font-semibold text-text-heading">{title}</h2>
        <p className="mt-2 text-sm text-muted">{message}</p>
      </div>
    </section>
  );
}
