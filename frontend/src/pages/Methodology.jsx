import React from 'react';
import { useLocation } from 'react-router-dom';
import { PageNavigationRailSlot } from '../components/PageNavigationRail';
import MethodologyWorkflow from '../features/methodology/components/MethodologyWorkflow';
import NetworkArchitecture from '../features/methodology/components/NetworkArchitecture';
import ReproducibilityPanel from '../features/methodology/components/ReproducibilityPanel';
import ResearchFraming from '../features/methodology/components/ResearchFraming';
import SystemArchitecture from '../features/methodology/components/SystemArchitecture';
import { methodologyRunView } from '../features/methodology/methodologyModel';
import { useMethodologyData } from '../features/methodology/useMethodologyData';

const METHODOLOGY_SECTIONS = [
  { id: 'methodology-framing', label: 'Research Framing', icon: 'themes' },
  { id: 'methodology-workflow', label: 'Workflow', icon: 'continuity' },
  { id: 'methodology-network', label: 'Network Models', icon: 'network' },
  { id: 'methodology-system', label: 'Implementation', icon: 'metadata' },
  { id: 'methodology-reproducibility', label: 'Reproducibility', icon: 'provenance' },
];

export default function MethodologyPage() {
  const data = useMethodologyData();
  const location = useLocation();
  const search = location.search;
  const runView = methodologyRunView(
    data.selectedRun,
    data.selectedRunDetail,
    data.overviewQuery.data ?? null,
    data.artifactsQuery.data?.artifacts ?? [],
  );

  const jumpToSection = (id) => {
    const element = document.getElementById(id);
    const container = document.getElementById('main-content');
    if (!element || !container) return;
    const containerRect = container.getBoundingClientRect();
    const elementRect = element.getBoundingClientRect();
    container.scrollTo({
      top: container.scrollTop + elementRect.top - containerRect.top - 20,
      behavior: 'smooth',
    });
    window.requestAnimationFrame(() => element.focus({ preventScroll: true }));
  };

  return (
    <div className="mx-auto flex max-w-[1600px] items-start px-1 sm:px-2">
      <div className="min-w-0 flex-1 space-y-6 pb-16">
        <section id="methodology-framing" className="scroll-mt-6" tabIndex={-1}>
          <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
            <div className="max-w-3xl">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Research design · thesis methodology</p>
              <h1 className="mt-2 text-2xl font-bold text-text-heading sm:text-3xl">Methodology</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
                How communities are constructed, interpreted, and tracked over time across Twitter/X and Telegram.
              </p>
            </div>

            <label className="w-full text-xs font-semibold text-muted md:hidden sm:max-w-xs">
              Jump to section
              <select
                aria-label="Jump to Methodology section"
                defaultValue="methodology-framing"
                onChange={(event) => jumpToSection(event.target.value)}
                className="mt-1 w-full rounded-xl border border-border bg-surface px-3 py-2.5 text-sm font-semibold text-text-heading"
              >
                {METHODOLOGY_SECTIONS.map((section) => <option key={section.id} value={section.id}>{section.label}</option>)}
              </select>
            </label>
          </div>

          <div className="mt-5"><ResearchFraming search={search} /></div>
        </section>

        <section id="methodology-workflow" className="scroll-mt-6" tabIndex={-1}>
          <MethodologyWorkflow />
        </section>

        <section id="methodology-network" className="scroll-mt-6" tabIndex={-1}>
          <NetworkArchitecture />
        </section>

        <section id="methodology-system" className="scroll-mt-6" tabIndex={-1}>
          <SystemArchitecture />
        </section>

        <section id="methodology-reproducibility" className="scroll-mt-6" tabIndex={-1}>
          <ReproducibilityPanel
            selectedRunId={data.selectedRunId}
            runView={runView}
            overviewQuery={data.overviewQuery}
            artifactsQuery={data.artifactsQuery}
            search={search}
          />
        </section>
      </div>

      <PageNavigationRailSlot sections={METHODOLOGY_SECTIONS} />
    </div>
  );
}
