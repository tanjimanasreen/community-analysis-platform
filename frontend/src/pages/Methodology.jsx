import React from 'react';
import { HelpCircle } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import PageNavigationRail from '../components/PageNavigationRail';
import AimScopePanel from '../features/methodology/components/AimScopePanel';
import MethodologyWorkflow from '../features/methodology/components/MethodologyWorkflow';
import NetworkArchitecture from '../features/methodology/components/NetworkArchitecture';
import ReproducibilityPanel from '../features/methodology/components/ReproducibilityPanel';
import ResearchQuestionGrid from '../features/methodology/components/ResearchQuestionGrid';
import ResearchQuestionMapping from '../features/methodology/components/ResearchQuestionMapping';
import SystemArchitecture from '../features/methodology/components/SystemArchitecture';
import { methodologyRunView } from '../features/methodology/methodologyModel';
import { useMethodologyData } from '../features/methodology/useMethodologyData';

const METHODOLOGY_SECTIONS = [
  { id: 'methodology-overview', label: 'Aim & Scope', icon: 'kpis' },
  { id: 'methodology-rqs', label: 'Research Questions', icon: 'themes' },
  { id: 'methodology-workflow', label: 'Workflow', icon: 'continuity' },
  { id: 'methodology-system', label: 'System Architecture', icon: 'metadata' },
  { id: 'methodology-network', label: 'Network Architecture', icon: 'network' },
  { id: 'methodology-rq-map', label: 'Method → RQs', icon: 'trends' },
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
        <section id="methodology-overview" className="scroll-mt-6" tabIndex={-1}>
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
                defaultValue="methodology-overview"
                onChange={(event) => jumpToSection(event.target.value)}
                className="mt-1 w-full rounded-xl border border-border bg-surface px-3 py-2.5 text-sm font-semibold text-text-heading"
              >
                {METHODOLOGY_SECTIONS.map((section) => <option key={section.id} value={section.id}>{section.label}</option>)}
              </select>
            </label>
          </div>

          <div className="mt-5"><AimScopePanel /></div>
        </section>

        <section id="methodology-rqs" className="scroll-mt-6" tabIndex={-1}>
          <SectionHeading
            icon={HelpCircle}
            eyebrow="Research questions"
            title="Four questions guide the analysis"
            description="Each question maps directly to a dashboard analysis while preserving the thesis wording."
          />
          <div className="mt-4"><ResearchQuestionGrid search={search} /></div>
        </section>

        <section id="methodology-workflow" className="scroll-mt-6" tabIndex={-1}>
          <MethodologyWorkflow />
        </section>

        <section id="methodology-system" className="scroll-mt-6" tabIndex={-1}>
          <SystemArchitecture />
        </section>

        <section id="methodology-network" className="scroll-mt-6" tabIndex={-1}>
          <NetworkArchitecture />
        </section>

        <section id="methodology-rq-map" className="scroll-mt-6" tabIndex={-1}>
          <ResearchQuestionMapping search={search} />
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

      <div className="pointer-events-none sticky top-0 z-40 ml-4 hidden h-screen w-14 shrink-0 flex-col justify-center md:flex lg:ml-6">
        <PageNavigationRail sections={METHODOLOGY_SECTIONS} />
      </div>
    </div>
  );
}

function SectionHeading({ icon: Icon, eyebrow, title, description }) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary"><Icon size={18} aria-hidden="true" /></span>
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">{eyebrow}</p>
        <h2 className="mt-1 text-lg font-bold text-text-heading">{title}</h2>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">{description}</p>
      </div>
    </div>
  );
}
