import { Network, BarChart2, BrainCircuit, Database, Users, FileText, Send, HelpCircle, ArrowRight, Scale } from 'lucide-react';

export default function MethodologyPage() {
  return (
    <div className="flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
      {/* Top 4 KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {/* Card 1: Platforms Covered */}
        <div className="bg-panel border border-border rounded-xl p-5 shadow-sm flex items-center gap-4">
          <div className="flex -space-x-2">
            <div className="w-10 h-10 rounded-full bg-blue-50 border-2 border-white flex items-center justify-center text-blue-500 z-10">
               <Send size={18} />
            </div>
            <div className="w-10 h-10 rounded-full bg-gray-100 border-2 border-white flex items-center justify-center text-gray-800">
               <span className="font-bold text-lg">X</span>
            </div>
          </div>
          <div>
            <p className="text-xs font-medium text-muted">Platforms Covered</p>
            <h3 className="text-base font-bold text-text-heading">Telegram + Twitter/X</h3>
          </div>
        </div>
        
        {/* Card 2: Pipeline Components */}
        <div className="bg-panel border border-border rounded-xl p-5 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-purple-50 flex items-center justify-center text-purple-600">
            <Network size={24} />
          </div>
          <div>
            <p className="text-xs font-medium text-muted">Pipeline Components</p>
            <h3 className="text-base font-bold text-text-heading">4 Stages</h3>
          </div>
        </div>
        
        {/* Card 3: Affinity Metrics */}
        <div className="bg-panel border border-border rounded-xl p-5 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-green-50 flex items-center justify-center text-green-600">
            <BarChart2 size={24} />
          </div>
          <div>
            <p className="text-xs font-medium text-muted">Affinity Metrics</p>
            <h3 className="text-base font-bold text-text-heading">IF & WIF</h3>
          </div>
        </div>
        
        {/* Card 4: Semantic Workflow */}
        <div className="bg-panel border border-border rounded-xl p-5 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-orange-50 flex items-center justify-center text-orange-500">
            <BrainCircuit size={24} />
          </div>
          <div>
            <p className="text-xs font-medium text-muted">Semantic Workflow</p>
            <h3 className="text-base font-bold text-text-heading">LDA + GPT-4</h3>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* System Architecture */}
        <div className="xl:col-span-2 bg-panel border border-border rounded-xl p-6 shadow-sm">
          <h3 className="text-lg font-bold text-text-heading mb-6">System Architecture</h3>
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            
            {/* Step A */}
            <div className="flex-1 flex flex-col items-center text-center">
              <div className="w-6 h-6 rounded-full bg-blue-500 text-white flex items-center justify-center text-xs font-bold mb-4 z-10 relative shadow-md">A</div>
              <div className="w-16 h-16 rounded-xl bg-blue-50 flex items-center justify-center text-blue-600 mb-4 border border-blue-100">
                <Database size={32} />
              </div>
              <h4 className="font-bold text-sm text-text-heading mb-2">Data Ingestion</h4>
              <p className="text-xs text-muted leading-relaxed">CSV platform data ingested into a centralized graph repository</p>
            </div>
            
            <ArrowRight className="text-border hidden md:block shrink-0" />
            
            {/* Step B */}
            <div className="flex-1 flex flex-col items-center text-center">
              <div className="w-6 h-6 rounded-full bg-purple-500 text-white flex items-center justify-center text-xs font-bold mb-4 z-10 relative shadow-md">B</div>
              <div className="w-16 h-16 rounded-xl bg-purple-50 flex items-center justify-center text-purple-600 mb-4 border border-purple-100">
                <Network size={32} />
              </div>
              <h4 className="font-bold text-sm text-text-heading mb-2">Interaction Network Extraction</h4>
              <p className="text-xs text-muted leading-relaxed">Monthly snapshots of creator → spreader interactions; self-shares removed</p>
            </div>
            
            <ArrowRight className="text-border hidden md:block shrink-0" />

            {/* Step C */}
            <div className="flex-1 flex flex-col items-center text-center">
              <div className="w-6 h-6 rounded-full bg-green-500 text-white flex items-center justify-center text-xs font-bold mb-4 z-10 relative shadow-md">C</div>
              <div className="w-16 h-16 rounded-xl bg-green-50 flex items-center justify-center text-green-600 mb-4 border border-green-100">
                <Users size={32} />
              </div>
              <h4 className="font-bold text-sm text-text-heading mb-2">Community Extraction</h4>
              <p className="text-xs text-muted leading-relaxed">NetworkX + Louvain community detection using IF and WIF edge weights</p>
            </div>
            
            <ArrowRight className="text-border hidden md:block shrink-0" />

            {/* Step D */}
            <div className="flex-1 flex flex-col items-center text-center">
              <div className="w-6 h-6 rounded-full bg-orange-500 text-white flex items-center justify-center text-xs font-bold mb-4 z-10 relative shadow-md">D</div>
              <div className="w-16 h-16 rounded-xl bg-orange-50 flex items-center justify-center text-orange-500 mb-4 border border-orange-100">
                <BarChart2 size={32} />
              </div>
              <h4 className="font-bold text-sm text-text-heading mb-2">Community Analyses</h4>
              <p className="text-xs text-muted leading-relaxed">Statistics, comparison, themes, and evolution over time</p>
            </div>
          </div>
        </div>

        {/* Platform Inputs */}
        <div className="xl:col-span-1 bg-panel border border-border rounded-xl p-6 shadow-sm flex flex-col">
          <h3 className="text-lg font-bold text-text-heading mb-6">Platform Inputs</h3>
          <div className="flex-1 flex flex-col gap-6">
            <div className="flex gap-4">
               <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white shrink-0 mt-1 shadow-sm">
                 <Send size={14} />
               </div>
               <div>
                 <h4 className="font-bold text-sm text-text-heading mb-2">Telegram</h4>
                 <ul className="text-xs text-muted list-disc ml-4 space-y-1">
                   <li>Users, messages, channels, forwarded messages</li>
                 </ul>
                 <div className="w-full h-px bg-border my-3 border-dashed border-t"></div>
                 <ul className="text-xs text-muted list-disc ml-4 space-y-1">
                   <li>Forwarded-message interaction network</li>
                 </ul>
               </div>
            </div>

            <div className="flex gap-4">
               <div className="w-8 h-8 rounded-full bg-black flex items-center justify-center text-white shrink-0 mt-1 shadow-sm">
                 <span className="font-bold text-sm">X</span>
               </div>
               <div>
                 <h4 className="font-bold text-sm text-text-heading mb-2">Twitter/X</h4>
                 <ul className="text-xs text-muted list-disc ml-4 space-y-1">
                   <li>Users, retweets/quotes, replies</li>
                 </ul>
                 <div className="w-full h-px bg-border my-3 border-dashed border-t"></div>
                 <ul className="text-xs text-muted list-disc ml-4 space-y-1">
                   <li>Retweet/Quote, Reply, and Combined networks</li>
                 </ul>
               </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
         {/* Affinity Metrics & Community Detection */}
         <div className="xl:col-span-2 bg-panel border border-border rounded-xl p-6 shadow-sm">
           <h3 className="text-lg font-bold text-text-heading mb-5">Affinity Metrics & Community Detection</h3>
           
           <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
             <div className="border border-blue-100 bg-blue-50/30 rounded-xl p-4 flex gap-4">
                <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600 shrink-0">
                  <Users size={20} />
                </div>
                <div>
                  <h4 className="font-bold text-sm text-blue-900 mb-1">Interaction Frequency (IF)</h4>
                  <p className="text-xs text-blue-700/80 leading-relaxed">Total number of posts of an author shared by a follower</p>
                </div>
             </div>
             <div className="border border-purple-100 bg-purple-50/30 rounded-xl p-4 flex gap-4">
                <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center text-purple-600 shrink-0">
                  <Scale size={20} />
                </div>
                <div>
                  <h4 className="font-bold text-sm text-purple-900 mb-1">Weighted Interaction Frequency (WIF)</h4>
                  <p className="text-xs text-purple-700/80 leading-relaxed">Shared posts divided by the author's total produced posts</p>
                </div>
             </div>
           </div>

           <div className="flex flex-wrap items-center gap-3 mb-5">
             <div className="bg-panel-soft text-text-heading border border-border px-3 py-1.5 rounded-lg text-xs font-semibold">min_total_post: 10</div>
             <div className="bg-panel-soft text-text-heading border border-border px-3 py-1.5 rounded-lg text-xs font-semibold">min_shared_post: 5</div>
             <div className="bg-panel-soft text-text-heading border border-border px-3 py-1.5 rounded-lg text-xs font-semibold">Louvain resolution: 1</div>
             <div className="bg-panel-soft text-text-heading border border-border px-3 py-1.5 rounded-lg text-xs font-semibold">seed: 123</div>
           </div>

           <div className="flex items-start gap-2 text-muted text-xs">
             <HelpCircle size={14} className="shrink-0 mt-0.5" />
             <p>Only meaningful interactions retained; self-sharing edges excluded.</p>
           </div>
         </div>

         {/* Theme Analysis Workflow */}
         <div className="xl:col-span-1 bg-panel border border-border rounded-xl p-6 shadow-sm">
           <h3 className="text-lg font-bold text-text-heading mb-5">Theme Analysis Workflow</h3>
           <div className="flex flex-col gap-3 text-sm text-text-heading font-medium mb-6">
             <div className="flex items-center gap-3"><div className="w-5 h-5 rounded-full bg-blue-500 text-white flex items-center justify-center text-[10px] font-bold shrink-0 shadow-sm">1</div>Translate non-English text to English</div>
             <div className="flex items-center gap-3"><div className="w-5 h-5 rounded-full bg-blue-500 text-white flex items-center justify-center text-[10px] font-bold shrink-0 shadow-sm">2</div>Clean text: remove emojis, stopwords, URLs, hashtags</div>
             <div className="flex items-center gap-3"><div className="w-5 h-5 rounded-full bg-blue-500 text-white flex items-center justify-center text-[10px] font-bold shrink-0 shadow-sm">3</div>Tokenize and lemmatize</div>
             <div className="flex items-center gap-3"><div className="w-5 h-5 rounded-full bg-blue-500 text-white flex items-center justify-center text-[10px] font-bold shrink-0 shadow-sm">4</div>Build unigram and bigram dictionaries</div>
             <div className="flex items-center gap-3"><div className="w-5 h-5 rounded-full bg-blue-500 text-white flex items-center justify-center text-[10px] font-bold shrink-0 shadow-sm">5</div>Run LDA topic modeling</div>
             <div className="flex items-center gap-3"><div className="w-5 h-5 rounded-full bg-blue-500 text-white flex items-center justify-center text-[10px] font-bold shrink-0 shadow-sm">6</div>Generate readable themes with GPT-4</div>
           </div>
           
           <div className="flex flex-col gap-3">
             <div className="flex items-start gap-3">
               <span className="text-xs font-bold text-blue-600 shrink-0 mt-1">For LDA</span>
               <div className="flex flex-wrap gap-2">
                 <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-[10px] font-semibold border border-blue-100">Topics: 15</span>
                 <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-[10px] font-semibold border border-blue-100">random_state: 100</span>
                 <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-[10px] font-semibold border border-blue-100">iterations: 100</span>
                 <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-[10px] font-semibold border border-blue-100">chunksize: 20</span>
                 <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-[10px] font-semibold border border-blue-100">passes: 80</span>
               </div>
             </div>
             <div className="w-full h-px bg-border my-1 border-dashed border-t"></div>
             <div className="flex items-start gap-3">
               <span className="text-xs font-bold text-purple-600 shrink-0 mt-1">For GPT-4</span>
               <div className="flex flex-wrap gap-2">
                 <span className="bg-purple-50 text-purple-700 px-2 py-0.5 rounded text-[10px] font-semibold border border-purple-100">temperature: 0</span>
                 <span className="bg-purple-50 text-purple-700 px-2 py-0.5 rounded text-[10px] font-semibold border border-purple-100">seed: 42</span>
                 <span className="bg-purple-50 text-purple-700 px-2 py-0.5 rounded text-[10px] font-semibold border border-purple-100">max_tokens: 50</span>
                 <span className="bg-purple-50 text-purple-700 px-2 py-0.5 rounded text-[10px] font-semibold border border-purple-100">JSON output</span>
               </div>
             </div>
           </div>
         </div>

         {/* Research Questions */}
         <div className="xl:col-span-1 bg-panel border border-border rounded-xl p-6 shadow-sm">
           <div className="flex items-center gap-3 mb-5">
             <div className="w-8 h-8 rounded-full bg-purple-50 flex items-center justify-center text-purple-600">
               <HelpCircle size={16} />
             </div>
             <h3 className="text-base font-bold text-text-heading">Research Questions</h3>
           </div>
           
           <div className="flex flex-col gap-4">
             <div>
               <p className="text-sm font-medium text-purple-800"><span className="font-bold">RQ1.</span> What is the impact of different user affinities on community detection?</p>
             </div>
             <div className="w-full h-px bg-border border-dashed border-t"></div>
             <div>
               <p className="text-sm font-medium text-purple-800"><span className="font-bold">RQ2.</span> What topics do these communities engage with?</p>
             </div>
             <div className="w-full h-px bg-border border-dashed border-t"></div>
             <div>
               <p className="text-sm font-medium text-purple-800"><span className="font-bold">RQ3.</span> How do communities evolve over time?</p>
             </div>
             <div className="w-full h-px bg-border border-dashed border-t"></div>
             <div>
               <p className="text-sm font-medium text-purple-800"><span className="font-bold">RQ4.</span> How do individuals migrate between communities?</p>
             </div>
           </div>
         </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
         {/* Evolution Analysis */}
         <div className="xl:col-span-3 bg-panel border border-border rounded-xl p-6 shadow-sm">
           <h3 className="text-lg font-bold text-text-heading mb-6">Evolution Analysis</h3>
           <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
             
             {/* Community Similarity Over Time */}
             <div>
               <h4 className="font-bold text-sm text-text-heading mb-2">Community Similarity Over Time</h4>
               <p className="text-xs text-muted mb-4">Persistent communities identified using Jaccard similarity ≥ 0.5</p>
               <div className="h-28 w-full bg-bg rounded-lg border border-border flex items-center justify-center relative overflow-hidden shadow-inner">
                 <div className="absolute w-16 h-16 rounded-full bg-blue-500/40 -translate-x-4 flex items-center justify-center text-xs font-bold text-blue-900 mix-blend-multiply border border-blue-500/50">t</div>
                 <div className="absolute w-16 h-16 rounded-full bg-purple-500/40 translate-x-4 flex items-center justify-center text-xs font-bold text-purple-900 mix-blend-multiply border border-purple-500/50">t+1</div>
                 <div className="absolute bottom-2 text-[10px] font-semibold text-muted">Jaccard ≥ 0.5</div>
               </div>
             </div>

             {/* Member Mobility */}
             <div>
               <h4 className="font-bold text-sm text-text-heading mb-2">Member Mobility</h4>
               <p className="text-xs text-muted mb-4">Track migration, entries, exits, and reappearances across months</p>
               <div className="h-28 w-full bg-bg rounded-lg border border-border flex items-center justify-center relative overflow-hidden shadow-inner">
                 {/* Decorative Sankey Mock */}
                 <div className="absolute left-6 text-[10px] font-medium text-muted flex flex-col justify-between h-20 py-1">
                   <span>t-1</span><span>t</span><span>t+1</span>
                 </div>
                 <svg width="100%" height="100%" viewBox="0 0 100 50" preserveAspectRatio="none" className="ml-10">
                   <path d="M 0 10 C 30 10, 50 40, 80 40" fill="none" stroke="#a78bfa" strokeWidth="6" opacity="0.6"/>
                   <path d="M 0 25 C 30 25, 50 10, 80 10" fill="none" stroke="#60a5fa" strokeWidth="4" opacity="0.6"/>
                   <path d="M 0 40 C 30 40, 50 25, 80 25" fill="none" stroke="#34d399" strokeWidth="5" opacity="0.6"/>
                   <rect x="0" y="5" width="4" height="10" fill="#60a5fa" rx="1" />
                   <rect x="0" y="20" width="4" height="10" fill="#a78bfa" rx="1" />
                   <rect x="0" y="35" width="4" height="10" fill="#34d399" rx="1" />
                   <rect x="80" y="5" width="4" height="10" fill="#60a5fa" rx="1" />
                   <rect x="80" y="20" width="4" height="10" fill="#34d399" rx="1" />
                   <rect x="80" y="35" width="4" height="10" fill="#a78bfa" rx="1" />
                 </svg>
               </div>
             </div>

             {/* Thematic Similarity */}
             <div>
               <h4 className="font-bold text-sm text-text-heading mb-2">Thematic Similarity</h4>
               <p className="text-xs text-muted mb-4">Sentence embeddings + cosine similarity used to compare theme continuity</p>
               <div className="h-28 w-full bg-bg rounded-lg border border-border flex items-center justify-center relative shadow-inner">
                  {/* Decorative Heatmap Mock */}
                  <div className="grid grid-cols-4 grid-rows-4 gap-0.5 w-16 h-16 mr-6">
                    <div className="bg-blue-600 rounded-sm"></div><div className="bg-blue-300 rounded-sm"></div><div className="bg-blue-100 rounded-sm"></div><div className="bg-blue-50 rounded-sm"></div>
                    <div className="bg-blue-200 rounded-sm"></div><div className="bg-blue-500 rounded-sm"></div><div className="bg-blue-200 rounded-sm"></div><div className="bg-blue-100 rounded-sm"></div>
                    <div className="bg-blue-50 rounded-sm"></div><div className="bg-blue-200 rounded-sm"></div><div className="bg-blue-600 rounded-sm"></div><div className="bg-blue-300 rounded-sm"></div>
                    <div className="bg-blue-100 rounded-sm"></div><div className="bg-blue-100 rounded-sm"></div><div className="bg-blue-400 rounded-sm"></div><div className="bg-blue-600 rounded-sm"></div>
                  </div>
                  <div className="absolute right-4 top-4 bottom-4 w-1.5 bg-gradient-to-b from-blue-700 to-blue-50 rounded"></div>
                  <div className="absolute right-1 top-3 text-[8px] text-muted font-medium">1.0</div>
                  <div className="absolute right-1 top-1/2 -translate-y-1/2 text-[8px] text-muted font-medium">0.5</div>
                  <div className="absolute right-1 bottom-3 text-[8px] text-muted font-medium">0</div>
               </div>
             </div>

           </div>
         </div>

         {/* Methodology Notes */}
         <div className="xl:col-span-1 bg-panel border border-border rounded-xl p-6 shadow-sm flex flex-col">
           <div className="flex items-center gap-3 mb-5">
             <div className="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center text-blue-600 shadow-sm">
               <FileText size={16} />
             </div>
             <h3 className="text-base font-bold text-text-heading">Methodology Notes</h3>
           </div>
           
           <ul className="text-sm text-muted list-disc ml-4 space-y-3 flex-1">
             <li>Monthly interaction snapshots</li>
             <li>Cross-platform analytical pipeline</li>
             <li>Deterministic settings for reproducibility</li>
             <li>Community-level outputs for structure, themes, and evolution</li>
           </ul>
         </div>
      </div>
    </div>
  );
}
