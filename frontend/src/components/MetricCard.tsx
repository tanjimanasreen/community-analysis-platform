import type { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: number | string | null;
  detail?: string;
  source: string;
  icon: LucideIcon;
  colorClass: string;
  bgClass: string;
  format?: (value: number | string) => string;
  /** When true renders a shimmer skeleton instead of the value */
  isLoading?: boolean;
}

export default function MetricCard({
  title,
  value,
  detail,
  source,
  icon: Icon,
  colorClass,
  bgClass,
  format = String,
  isLoading = false,
}: MetricCardProps) {
  const available = value !== null && value !== undefined;

  if (isLoading) {
    return (
      <article
        className="panel shimmer-placeholder"
        aria-hidden="true"
      >
        <div className="flex justify-between items-start mb-4">
          <div className="shimmer w-10 h-10 rounded-lg" />
          <div className="shimmer w-5 h-5 rounded-full" />
        </div>
        <div className="space-y-3">
          <div className="shimmer h-3 w-24 rounded" />
          <div className="shimmer h-7 w-16 rounded" />
          {detail !== undefined && <div className="shimmer h-3 w-32 rounded" />}
        </div>
      </article>
    );
  }

  return (
    <article
      className="panel relative overflow-hidden group hover:border-primary/40 transition-all duration-200 animate-fade-in-up flex flex-col justify-between"
      title={`Source: ${source}`}
    >
      {/* Ambient glow blob constrained within card */}
      <div
        className={`absolute top-0 right-0 w-28 h-28 ${bgClass} opacity-15 blur-2xl -mr-6 -mt-6 group-hover:opacity-30 transition-opacity duration-300 pointer-events-none`}
        aria-hidden="true"
      />

      <div className="flex justify-between items-start mb-3 relative z-10">
        <div className={`w-10 h-10 rounded-xl ${bgClass} bg-opacity-20 flex items-center justify-center border border-white/5 shadow-inner`}>
          <Icon size={20} className={colorClass} aria-hidden="true" />
        </div>
        <span
          className="w-5 h-5 rounded-full border border-border/80 bg-surface-soft/60 flex items-center justify-center text-muted text-xs cursor-help select-none shrink-0 hover:text-text-heading hover:border-primary/50 transition-colors"
          aria-label={`Source: ${source}`}
        >
          i
        </span>
      </div>

      <div className="relative z-10 flex-1 flex flex-col justify-end">
        <h3 className="text-muted text-xs font-semibold uppercase tracking-wider mb-1.5">{title}</h3>
        <div
          className={`text-2xl lg:text-3xl font-extrabold tracking-tight mb-1 transition-all duration-300 ${
            available ? 'text-text-heading' : 'text-muted/80 text-sm font-medium'
          }`}
        >
          {available ? format(value) : 'Unavailable for this run'}
        </div>
        {detail && <p className="text-xs text-muted/90 leading-relaxed">{detail}</p>}
      </div>
    </article>
  );
}
