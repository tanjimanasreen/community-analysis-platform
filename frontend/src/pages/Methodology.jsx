import React from 'react';
import ArtifactValue from '../components/ArtifactValue';
import {
  ArrowRight,
  BarChart2,
  BrainCircuit,
  Database,
  FileText,
  HelpCircle,
  Network,
  Scale,
  Send,
  Users,
} from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import ErrorState from '../components/states/ErrorState';
import LoadingState from '../components/states/LoadingState';
import {
  methodologyRunView,
  THESIS_BASELINE,
} from '../features/methodology/methodologyModel';
import { useMethodologyData } from '../features/methodology/useMethodologyData';

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

  return (
    <div className="flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
      <header className="panel p-5">
        <h1 className="text-xl font-bold text-text-heading">Methodology and run provenance</h1>
        <p className="mt-1 max-w-4xl text-sm text-muted">
          The thesis baseline and the selected run's resolved metadata are shown separately. The dashboard is a read-only view over generated artifacts and never runs community detection, LDA, or theme generation in the browser.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard icon={Send} label="Platforms covered" value="Telegram + Twitter/X" />
        <SummaryCard icon={Network} label="Pipeline components" value="4 stages" />
        <SummaryCard icon={BarChart2} label="Affinity metrics" value="IF & WIF" />
        <SummaryCard icon={BrainCircuit} label="Semantic order" value="LDA → theme labels" />
      </div>

      <section className="panel p-6">
        <h2 className="text-lg font-bold text-text-heading">System architecture</h2>
        <div className="mt-6 grid grid-cols-1 items-start gap-4 md:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr]">
          <ArchitectureStep letter="A" icon={Database} title="Data ingestion" description="Platform CSV data is normalized and stored through the graph-store boundary." />
          <ArrowRight className="mx-auto mt-14 hidden text-border md:block" />
          <ArchitectureStep letter="B" icon={Network} title="Interaction network" description="Monthly creator → spreader snapshots exclude self-shares and preserve platform-specific interaction types." />
          <ArrowRight className="mx-auto mt-14 hidden text-border md:block" />
          <ArchitectureStep letter="C" icon={Users} title="Community extraction" description="NetworkX and Louvain use the preserved IF and WIF edge-weight definitions." />
          <ArrowRight className="mx-auto mt-14 hidden text-border md:block" />
          <ArchitectureStep letter="D" icon={BarChart2} title="Community analyses" description="Structural statistics, LDA topics, downstream themes, and longitudinal artifacts are generated." />
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <section className="panel p-6 xl:col-span-2">
          <h2 className="text-lg font-bold text-text-heading">Thesis baseline and protected defaults</h2>
          <p className="mt-1 text-sm text-muted">These values describe the preserved thesis behavior. Selected runs may record documented experiment overrides, shown in the run-specific section below.</p>
          <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
            <BaselineGroup title="Graph thresholds" entries={Object.entries(THESIS_BASELINE.graph_thresholds)} />
            <BaselineGroup title="Louvain" entries={Object.entries(THESIS_BASELINE.louvain)} />
            <BaselineGroup title="LDA" entries={Object.entries(THESIS_BASELINE.lda)} />
            <BaselineGroup title="Temporal analysis" entries={Object.entries(THESIS_BASELINE.temporal)} />
          </div>
        </section>

        <section className="panel p-6">
          <h2 className="text-lg font-bold text-text-heading">Affinity definitions</h2>
          <div className="mt-5 space-y-4">
            <DefinitionCard
              icon={Users}
              title="Interaction Frequency (IF)"
              text="shared_post: the total number of posts produced by an author and shared by a follower."
            />
            <DefinitionCard
              icon={Scale}
              title="Weighted Interaction Frequency (WIF)"
              text="weighted_post = shared_post / total_post, where total_post is the author's produced-post count."
            />
          </div>
        </section>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <section className="panel p-6 xl:col-span-2">
          <h2 className="text-lg font-bold text-text-heading">Semantic workflow</h2>
          <ol className="mt-5 grid grid-cols-1 gap-3 text-sm text-muted md:grid-cols-3">
            <WorkflowStep number="1" text="Clean, normalize, tokenize, and lemmatize community text." />
            <WorkflowStep number="2" text="Run unigram and bigram LDA with preserved topic-model defaults." />
            <WorkflowStep number="3" text="Pass LDA keywords to a configured downstream provider for readable theme labels." />
          </ol>
          <div className="mt-5 rounded-xl border border-primary/20 bg-primary/5 p-4 text-sm text-muted">
            Provider-generated theme labels do not replace LDA topics. They are downstream interpretations of the LDA keyword evidence. The selected run's provider and model are read from run metadata rather than inferred from the thesis baseline.
          </div>
        </section>

        <section className="panel p-6">
          <div className="flex items-center gap-2"><HelpCircle size={18} className="text-primary" /><h2 className="text-lg font-bold text-text-heading">Research questions</h2></div>
          <ol className="mt-5 space-y-4 text-sm text-muted">
            <li><strong className="text-text-heading">RQ1.</strong> What is the impact of different user affinities on community detection?</li>
            <li><strong className="text-text-heading">RQ2.</strong> What topics do these communities engage with?</li>
            <li><strong className="text-text-heading">RQ3.</strong> How do communities evolve over time?</li>
            <li><strong className="text-text-heading">RQ4.</strong> How do individuals migrate between communities?</li>
          </ol>
        </section>
      </div>

      <section className="panel p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-bold text-text-heading">Selected run: resolved metadata</h2>
            <p className="mt-1 text-sm text-muted">Values below come from the run catalog, overview configuration metadata, overview model metadata, and manifest artifact list.</p>
          </div>
          <span className="rounded-full border border-border px-3 py-1 text-xs font-medium text-muted">{data.selectedRunId || 'No run selected'}</span>
        </div>

        {(data.overviewQuery.isPending || data.artifactsQuery.isPending) ? (
          <div className="mt-5"><LoadingState title="Loading selected-run methodology metadata" /></div>
        ) : data.overviewQuery.error || data.artifactsQuery.error ? (
          <div className="mt-5"><ErrorState error={data.overviewQuery.error || data.artifactsQuery.error} title="Selected-run metadata could not be loaded" /></div>
        ) : (
          <div className="mt-5 grid grid-cols-1 gap-6 xl:grid-cols-3">
            <MetadataPanel title="Run and dataset" entries={runView.run} />
            <MetadataPanel title="Resolved configuration" entries={runView.configuration} unavailable="Resolved configuration metadata is absent; the dashboard does not assume baseline defaults were used." />
            <MetadataPanel title="Provider and models" entries={runView.models} unavailable="Provider/model metadata unavailable for this run." />
          </div>
        )}

        <div className="mt-6 rounded-xl border border-border bg-surface-soft/40 p-4">
          <h3 className="text-sm font-bold text-text-heading">Available artifact categories</h3>
          <div className="mt-3 flex flex-wrap gap-2">
            {runView.artifactCategories.length > 0 ? runView.artifactCategories.map((category) => (
              <span key={category} className="rounded-full border border-border bg-bg px-3 py-1 text-xs font-medium text-text-heading">{category}</span>
            )) : <span className="text-sm text-muted">No artifact categories are listed.</span>}
          </div>
        </div>
      </section>

       <section className="rounded-xl border border-border bg-surface p-6">
        <div className="flex items-center gap-2"><FileText size={18} className="text-primary" /><h2 className="text-lg font-bold text-text-heading">Explore the methodology through artifacts</h2></div>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <MethodLink to={`/network${search}`} label="Interaction networks" description="IF/WIF graph structure and communities" />
          <MethodLink to={`/thematic${search}`} label="LDA and themes" description="Matched/partial topics and downstream labels" />
          <MethodLink to={`/transitions${search}`} label="Evolution artifacts" description="Jaccard transitions, mobility, and similarity" />
          <MethodLink to={`/reports${search}`} label="Artifact library" description="Read-only manifest-backed downloads" />
        </div>
      </section>
    </div>
  );
}

function SummaryCard({ icon: Icon, label, value }) {
  return (
    <article className="panel p-5 flex items-center gap-4">
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary"><Icon size={22} /></div>
      <div><p className="text-xs font-medium text-muted">{label}</p><p className="font-bold text-text-heading">{value}</p></div>
    </article>
  );
}

function ArchitectureStep({ letter, icon: Icon, title, description }) {
  return (
    <div className="flex flex-col items-center text-center">
      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-bold text-white">{letter}</div>
      <div className="mt-4 flex h-16 w-16 items-center justify-center rounded-xl border border-primary/20 bg-primary/10 text-primary"><Icon size={30} /></div>
      <h3 className="mt-4 text-sm font-bold text-text-heading">{title}</h3>
      <p className="mt-2 text-xs leading-relaxed text-muted">{description}</p>
    </div>
  );
}

function BaselineGroup({ title, entries }) {
  return (
    <div className="rounded-xl border border-border bg-surface-soft/40 p-4">
       <h3 className="text-sm font-bold text-text-heading">{title}</h3>
       <dl className="mt-3 grid grid-cols-1 gap-2 text-xs">
         {entries.map(([key, value]) => (
           <div key={key} className="flex items-start justify-between gap-4"><dt className="text-muted">{key}</dt><dd className="break-all font-mono font-semibold text-text-heading">{String(value)}</dd></div>
         ))}
       </dl>
     </div>
  );
}

function DefinitionCard({ icon: Icon, title, text }) {
  return (
     <div className="flex gap-3 rounded-xl border border-border bg-surface-soft/40 p-4">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon size={18} /></div>
      <div><h3 className="text-sm font-bold text-text-heading">{title}</h3><p className="mt-1 text-xs leading-relaxed text-muted">{text}</p></div>
    </div>
  );
}

function WorkflowStep({ number, text }) {
  return (
     <li className="flex gap-3 rounded-xl border border-border bg-surface-soft/40 p-4">
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-white">{number}</span>
      <span>{text}</span>
    </li>
  );
}

function MetadataPanel({ title, entries, unavailable = 'Metadata unavailable.' }) {
  return (
     <div className="rounded-xl border border-border bg-surface-soft/40 p-4">
       <h3 className="text-sm font-bold text-text-heading">{title}</h3>
       {entries.length > 0 ? (
         <dl className="mt-3 space-y-3">
           {entries.map(([key, value]) => (
             <div key={key}><dt className="break-all text-[11px] text-muted">{key}</dt><dd className="mt-1 break-words text-sm font-semibold text-text-heading"><ArtifactValue value={value} /></dd></div>
           ))}
         </dl>
       ) : <p className="mt-3 text-sm text-muted">{unavailable}</p>}
     </div>
  );
}

function MethodLink({ to, label, description }) {
  return (
     <Link to={to} className="rounded-xl border border-border bg-surface-soft/40 p-4 hover:border-primary/40 hover:bg-primary/5">
      <p className="text-sm font-bold text-text-heading">{label}</p>
      <p className="mt-1 text-xs text-muted">{description}</p>
    </Link>
  );
}
