import { Database, Search } from 'lucide-react';
import {
  EVIDENCE_GROUPS,
  EVIDENCE_VIEWS,
  type EvidenceView,
} from './evidenceModel';

interface EvidenceNavigatorProps {
  view: EvidenceView;
  onViewChange: (view: EvidenceView) => void;
  communitySearchDraft: string;
  onCommunitySearchDraftChange: (value: string) => void;
  onApplyCommunitySearch: () => void;
  onClearCommunitySearch: () => void;
}

export default function EvidenceNavigator({
  view,
  onViewChange,
  communitySearchDraft,
  onCommunitySearchDraftChange,
  onApplyCommunitySearch,
  onClearCommunitySearch,
}: EvidenceNavigatorProps) {
  const definition = EVIDENCE_VIEWS[view];
  const activeGroup = EVIDENCE_GROUPS.find((group) => group.id === definition.dimension) ?? EVIDENCE_GROUPS[0];

  return (
    <section className="panel p-4" aria-label="Research data navigation">
      <div className="flex items-start gap-3">
        <Database size={18} className="mt-0.5 shrink-0 text-primary" aria-hidden="true" />
        <div className="min-w-0">
          <h2 className="text-sm font-bold text-text-heading">Research Data</h2>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-muted">
            Choose a thesis dimension, then inspect the persisted analytical data supporting that analysis.
          </p>
        </div>
      </div>

      <nav className="mt-4" aria-label="Research data views">
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4" role="group" aria-label="Research dimensions">
          {EVIDENCE_GROUPS.map((group) => {
            const selected = activeGroup.id === group.id;
            return (
              <button
                type="button"
                key={group.id}
                aria-pressed={selected}
                onClick={() => { if (!selected) onViewChange(group.views[0]); }}
                className={`rounded-xl border px-3 py-2.5 text-left transition-colors ${selected ? 'border-primary/40 bg-primary/10 text-primary' : 'border-border text-muted hover:bg-surface-soft hover:text-text-heading'}`}
              >
                <span className="block text-[10px] font-bold uppercase tracking-[0.14em]">{group.label}</span>
                <span className="mt-1 block text-[11px] font-medium">
                  {group.views.length === 1 ? EVIDENCE_VIEWS[group.views[0]].shortLabel : `${group.views.length} data views`}
                </span>
              </button>
            );
          })}
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-border pt-3" role="group" aria-label={`${activeGroup.label} data views`}>
          <span className="mr-1 text-[10px] font-bold uppercase tracking-[0.14em] text-muted/80">Data view</span>
          {activeGroup.views.map((viewId) => {
            const item = EVIDENCE_VIEWS[viewId];
            const selected = view === viewId;
            return (
              <button
                type="button"
                key={viewId}
                aria-pressed={selected}
                onClick={() => onViewChange(viewId)}
                className={`rounded-lg px-3 py-2 text-xs font-semibold transition-colors ${selected ? 'bg-primary/10 text-primary' : 'border border-border text-muted hover:bg-surface-soft hover:text-text-heading'}`}
              >
                {item.shortLabel}
              </button>
            );
          })}
        </div>
      </nav>

      {definition.supportsCommunitySearch && (
        <form
          className="mt-3 flex flex-col gap-3 border-t border-border pt-3 md:flex-row md:items-end"
          onSubmit={(event) => {
            event.preventDefault();
            onApplyCommunitySearch();
          }}
        >
          <label className="w-full text-xs font-semibold text-text-heading md:max-w-xs" htmlFor="evidence-community-search">
            Exact community ID
            <div className="relative mt-1.5">
              <Search size={14} className="pointer-events-none absolute left-3 top-2.5 text-muted" aria-hidden="true" />
              <input
                id="evidence-community-search"
                value={communitySearchDraft}
                onChange={(event) => onCommunitySearchDraftChange(event.target.value)}
                placeholder="Community ID"
                className="w-full rounded-lg border border-border bg-bg py-2 pl-9 pr-3 text-xs text-text-heading"
              />
            </div>
          </label>
          <div className="flex gap-2">
            <button type="submit" className="rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white hover:bg-primary/90">Apply</button>
            <button type="button" onClick={onClearCommunitySearch} className="rounded-lg border border-border px-4 py-2 text-xs font-semibold text-muted hover:bg-surface-soft">Clear</button>
          </div>
          <p className="max-w-xl text-[11px] leading-4 text-muted md:ml-auto md:pb-1">
            Applied as an exact server-side community filter for the selected month. It does not change the thesis dimension or affinity definition.
          </p>
        </form>
      )}
    </section>
  );
}
