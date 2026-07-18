import { CheckCircle2, CircleAlert, Database, Wifi } from 'lucide-react';

interface ArtifactStatusBadgeProps {
  label: string;
  status: 'healthy' | 'verified' | 'warning' | 'neutral';
  title?: string;
}

const styles = {
  healthy: 'border-success/30 bg-success/10 text-success',
  verified: 'border-primary/30 bg-primary/10 text-primary',
  warning: 'border-warning/30 bg-warning/10 text-warning',
  neutral: 'border-border bg-panel text-muted',
};

const icons = {
  healthy: Wifi,
  verified: CheckCircle2,
  warning: CircleAlert,
  neutral: Database,
};

export default function ArtifactStatusBadge({
  label,
  status,
  title,
}: ArtifactStatusBadgeProps) {
  const Icon = icons[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-[11px] font-medium ${styles[status]}`}
      title={title}
    >
      <Icon size={12} aria-hidden="true" />
      {label}
    </span>
  );
}
