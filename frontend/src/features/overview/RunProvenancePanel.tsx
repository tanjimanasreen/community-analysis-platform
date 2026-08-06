import { CheckCircle2, Clipboard, Code2, Database, Timer, type LucideIcon } from 'lucide-react';
import type { OverviewResponse, RunDetail, RunSummary, VerificationResponse } from '../../types/api';
import { formatCount } from './overviewUtils';

type ProvenanceField = [label: string, value: string | number | null | undefined, copyable?: boolean];

interface ProvenanceGroup {
  title: string;
  icon: LucideIcon;
  fields: ProvenanceField[];
}

interface RunProvenancePanelProps {
  overview: OverviewResponse;
  selectedRun: RunSummary | null;
  selectedRunDetail: RunDetail | null;
  verification: VerificationResponse | null;
}

export default function RunProvenancePanel({
  overview,
  selectedRun,
  selectedRunDetail,
  verification,
}: RunProvenancePanelProps) {
  const pipeline = selectedRunDetail?.pipeline ?? {};
  const code = selectedRunDetail?.code ?? {};
  const dataset = selectedRunDetail?.dataset ?? {};
  const startedAt = textValue(pipeline.started_at) ?? selectedRun?.started_at;
  const completedAt = textValue(pipeline.completed_at) ?? selectedRun?.completed_at;
  const groups: ProvenanceGroup[] = [
    {
      title: 'Identity',
      icon: Database,
      fields: [
        ['Run ID', selectedRunDetail?.run_id ?? selectedRun?.run_id, true],
        ['Status', selectedRun?.status ?? selectedRunDetail?.status],
        ['Artifacts', selectedRunDetail ? `${formatCount(selectedRunDetail.artifact_count)} manifest artifacts` : null],
        ['Verification', verification?.ok ? `${formatCount(verification.checked_artifacts)} artifacts verified` : verification?.error ?? null],
      ],
    },
    {
      title: 'Execution',
      icon: Timer,
      fields: [
        ['Started', formatTimestamp(startedAt)],
        ['Completed', formatTimestamp(completedAt)],
        ['Duration', formatDuration(startedAt, completedAt)],
        ['Prefect flow', textValue(pipeline.prefect_flow_run_id), true],
      ],
    },
    {
      title: 'Code and configuration',
      icon: Code2,
      fields: [
        ['Git commit', textValue(code.git_commit), true],
        ['Configuration digest', textValue(code.config_digest), true],
        ['Dataset source hash', textValue(dataset.source_hash), true],
        ['Analysis window', overview.date_start && overview.date_end ? `${overview.date_start} – ${overview.date_end}` : null],
      ],
    },
  ];

  return (
    <section className="panel overview-provenance-panel">
      <div className="overview-section-heading">
        <div>
          <p className="overview-eyebrow">Traceability</p>
          <h2>Run Provenance</h2>
          <p>Execution, code, configuration, and dataset lineage from the validated run manifest.</p>
        </div>
        {verification?.ok && <span className="overview-verified-badge"><CheckCircle2 size={15} /> Verified</span>}
      </div>
      <div className="overview-provenance-grid">
        {groups.map(({ title, icon: Icon, fields }) => (
          <section key={title}>
            <h3><Icon size={16} aria-hidden="true" /> {title}</h3>
            <dl>
              {fields.map(([label, rawValue, copyable = false]) => {
                const value = rawValue === null || rawValue === undefined || rawValue === ''
                  ? 'Unavailable'
                  : String(rawValue);
                return (
                  <div key={String(label)}>
                    <dt>{label}</dt>
                    <dd className={copyable ? 'is-identifier' : ''} title={copyable ? value : undefined}>
                      <span>{copyable ? concise(value) : value}</span>
                      {copyable && value !== 'Unavailable' && <CopyButton label={String(label)} value={value} />}
                    </dd>
                  </div>
                );
              })}
            </dl>
          </section>
        ))}
      </div>
    </section>
  );
}

function CopyButton({ label, value }: { label: string; value: string }) {
  return (
    <button
      type="button"
      className="overview-copy-button"
      aria-label={`Copy ${label}`}
      title={`Copy ${label}`}
      onClick={() => void navigator.clipboard?.writeText(value)}
    >
      <Clipboard size={14} />
    </button>
  );
}

function textValue(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

function concise(value: string): string {
  if (value === 'Unavailable' || value.length <= 22) return value;
  return `${value.slice(0, 10)}…${value.slice(-8)}`;
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return 'Unavailable';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'medium',
    timeZone: 'UTC',
  }).format(date)} UTC`;
}

function formatDuration(start: string | null | undefined, end: string | null | undefined): string {
  if (!start || !end) return 'Unavailable';
  const duration = new Date(end).getTime() - new Date(start).getTime();
  if (!Number.isFinite(duration) || duration < 0) return 'Unavailable';
  const totalSeconds = Math.round(duration / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return [hours ? `${hours}h` : '', minutes ? `${minutes}m` : '', `${seconds}s`].filter(Boolean).join(' ');
}
