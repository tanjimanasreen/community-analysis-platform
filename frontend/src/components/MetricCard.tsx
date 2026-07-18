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
}: MetricCardProps) {
  const available = value !== null && value !== undefined;
  return (
    <article className="bg-panel border border-border rounded-xl p-5 shadow-sm relative overflow-hidden group hover:border-border/80 transition-colors">
      <div className={`absolute top-0 right-0 w-24 h-24 ${bgClass} rounded-full blur-2xl opacity-20 -mr-8 -mt-8 group-hover:opacity-30 transition-opacity`} />
      <div className="flex justify-between items-start mb-4 relative z-10">
        <div className={`w-10 h-10 rounded-lg ${bgClass} bg-opacity-20 flex items-center justify-center`}>
          <Icon size={20} className={colorClass} aria-hidden="true" />
        </div>
        <span
          className="w-5 h-5 rounded-full border border-border flex items-center justify-center text-muted text-xs cursor-help"
          title={`Source: ${source}`}
          aria-label={`Source: ${source}`}
        >
          i
        </span>
      </div>
      <div className="relative z-10">
        <h3 className="text-muted text-sm font-medium mb-1">{title}</h3>
        <div className={`text-2xl font-bold mb-2 ${available ? 'text-text-heading' : 'text-muted text-base'}`}>
          {available ? format(value) : 'Unavailable for this run'}
        </div>
        {detail && <p className="text-xs text-muted">{detail}</p>}
      </div>
    </article>
  );
}
