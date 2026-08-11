import React from 'react';
import { Activity, Calendar, HelpCircle, Menu } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import ArtifactStatusBadge from './ArtifactStatusBadge';
import { conciseRunId } from '../features/overview/overviewUtils';

const routeCopy = {
  '/': ['Overview Dashboard', 'Monitor validated run metrics and community structure.'],
  '/communities': ['Communities', 'Browse monthly community partitions and inspect one community in structural and semantic detail.'],
  '/network': ['Communities', 'Browse monthly community partitions and inspect one community in structural and semantic detail.'],
  '/thematic': ['Thematic Analysis', 'Inspect LDA topics and downstream theme labels for the selected run.'],
  '/evolution': ['Community Evolution', 'Follow persistent community paths through structure, membership, and themes.'],
  '/run-history': ['Run History', 'Compare compatible completed runs and longitudinal artifacts.'],
  '/comparative': ['Comparative Analysis', 'Compare compatible platform runs using shared analytical definitions.'],
  '/top-communities': ['Communities', 'Browse monthly community partitions and inspect one community in structural and semantic detail.'],
  '/data-reports': ['Research Data & Reports', 'Inspect persisted analytical data, provenance, and verified outputs from the selected run.'],
  '/evidence': ['Research Data & Reports', 'Inspect persisted analytical data, provenance, and verified outputs from the selected run.'],
  '/data': ['Research Data & Reports', 'Inspect persisted analytical data, provenance, and verified outputs from the selected run.'],
  '/reports': ['Research Data & Reports', 'Inspect persisted analytical data, provenance, and verified outputs from the selected run.'],
  '/methodology': ['Methodology', 'Understand the analytical pipeline, data model, and configured methods.'],
};

export default function Topbar({
  selectedRunId,
  selectedRun,
  runs,
  onRunChange,
  metric,
  onMetricChange,
  health,
  verification,
  toggleSidebar,
  isSidebarCollapsed,
  selectedPlatform,
  onPlatformChange,
  facets,
}) {
  const location = useLocation();
  const [title, subtitle] = routeCopy[location.pathname] || routeCopy['/'];
  const showMetric = !['/thematic', '/evolution', '/transitions', '/data-reports', '/evidence', '/data', '/reports', '/methodology'].includes(location.pathname);
  const helpTarget = `/methodology${location.search}`;

  return (
    <header className="page-header sticky top-0 z-30 shrink-0 border-b border-border/80 bg-bg/95 backdrop-blur-md p-4 sm:p-5 mb-5 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={toggleSidebar}
            aria-label={isSidebarCollapsed ? 'Open navigation' : 'Close navigation'}
            aria-expanded={!isSidebarCollapsed}
            className="lg:hidden p-2 text-muted hover:text-text-heading bg-surface-soft border border-border rounded-xl transition-colors"
          >
            <Menu size={20} />
          </button>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-text-heading tracking-tight">{title}</h1>
            <p className="text-xs sm:text-sm text-muted/90 mt-0.5 hidden sm:block">{subtitle}</p>
          </div>
        </div>

        <div className="flex items-center flex-wrap gap-2.5 self-end sm:self-auto">
          {health && (
            <span
              className="flex items-center gap-1.5 text-xs text-muted/90 bg-surface-soft/80 px-2.5 py-1 rounded-full border border-border/60"
              title={`API ${health.status} · schema ${health.schema_version}`}
            >
              <span
                className={`w-2 h-2 rounded-full shrink-0 ${
                  health.status === 'ok' || health.status === 'healthy'
                    ? 'bg-success animate-pulse-glow'
                    : 'bg-warning'
                }`}
                aria-label={`API ${health.status}`}
              />
              <span className="hidden sm:inline font-medium">
                API {health.status === 'ok' || health.status === 'healthy' ? 'live' : health.status}
              </span>
            </span>
          )}
          {verification && (
            <ArtifactStatusBadge
              label={verification.ok ? 'Run verified' : 'Verification failed'}
              status={verification.ok ? 'verified' : 'warning'}
              title={verification.ok
                ? `${verification.checked_artifacts} artifacts verified`
                : verification.error || 'Artifact integrity verification failed'}
            />
          )}
          <Link
            to={helpTarget}
            aria-label="Open methodology help"
            className="p-2 text-muted hover:text-text-heading hover:bg-surface-soft rounded-xl border border-border/60 transition-colors"
          >
            <HelpCircle size={20} />
          </Link>
        </div>
      </div>

      <div className="flex flex-col md:flex-row md:flex-wrap items-start md:items-center justify-between gap-3 pt-3 border-t border-border/40 mt-3 w-full">
        <div className="control-panel w-full md:w-auto bg-surface-soft/90 border border-border/80 rounded-xl p-1 flex-col sm:flex-row flex-wrap overflow-hidden">
          {facets?.platforms?.length > 0 && (
            <label className="flex items-center px-2.5 py-1.5 gap-2 w-full sm:w-auto min-w-0 overflow-hidden border-b sm:border-b-0 sm:border-r border-border/60 pb-2 sm:pb-1.5">
              <span className="sr-only">Platform</span>
              <select
                aria-label="Platform"
                className="bg-transparent border-none text-xs sm:text-sm text-text-heading font-semibold focus:outline-none cursor-pointer pr-2 w-full min-w-0 truncate capitalize"
                value={selectedPlatform || ''}
                onChange={(event) => onPlatformChange(event.target.value)}
              >
                {facets.platforms.map((platform) => (
                  <option key={platform} value={platform} className="bg-surface text-text-heading capitalize">
                    {platform}
                  </option>
                ))}
              </select>
            </label>
          )}

          <label className={`flex items-center px-2.5 py-1.5 gap-2 w-full sm:w-auto min-w-0 overflow-hidden ${showMetric ? 'border-b sm:border-b-0 sm:border-r border-border/60 pb-2 sm:pb-1.5' : ''}`}>
            <Calendar size={16} className="text-primary shrink-0" aria-hidden="true" />
            <span className="sr-only">Analysis run</span>
            <select
              aria-label="Analysis run"
              className="bg-transparent border-none text-xs sm:text-sm text-text-heading font-semibold focus:outline-none cursor-pointer pr-2 w-full min-w-0 truncate"
              value={selectedRunId}
              onChange={(event) => onRunChange(event.target.value)}
              disabled={runs.length === 0}
            >
              {runs.length === 0 && <option value="">No completed runs available</option>}
              {runs.map((run) => (
                <option key={run.run_id} value={run.run_id} className="bg-surface text-text-heading">
                  {formatRunLabel(run)}
                </option>
              ))}
            </select>
          </label>

          {showMetric && (
            <label className="flex items-center px-2.5 py-1.5 gap-2 w-full sm:w-auto min-w-0 shrink-0">
              <Activity size={16} className="text-secondary shrink-0" aria-hidden="true" />
              <span className="sr-only">Affinity metric</span>
              <select
                aria-label="Affinity metric"
                className="bg-transparent border-none text-xs sm:text-sm text-text-heading font-semibold focus:outline-none cursor-pointer pr-2 w-full sm:w-auto min-w-0"
                value={metric}
                onChange={(event) => onMetricChange(event.target.value)}
              >
                <option value="if" className="bg-surface text-text-heading">Interaction Frequency (IF)</option>
                <option value="wif" className="bg-surface text-text-heading">Weighted Interaction Frequency (WIF)</option>
              </select>
            </label>
          )}
        </div>
        {selectedRun && (
          <span className="text-[11px] font-mono text-muted/80 truncate max-w-full block" title={selectedRun.run_id} aria-live="polite">
            Selected run: {conciseRunId(selectedRun.run_id)}
          </span>
        )}
      </div>
    </header>
  );
}

function formatRunLabel(run) {
  const platform = run.platform || 'unknown platform';
  const contentType = run.content_type || 'unknown content';
  const dateRange = run.date_start || run.date_end
    ? `${run.date_start || 'unknown'} → ${run.date_end || 'unknown'}`
    : run.year && run.month
      ? `${run.year}-${String(run.month).padStart(2, '0')}`
      : 'undated';
  return `${platform} · ${contentType} · ${dateRange} · ${conciseRunId(run.run_id)}`;
}
