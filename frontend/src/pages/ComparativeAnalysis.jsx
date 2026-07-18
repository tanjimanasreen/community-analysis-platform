import { Lightbulb, TrendingUp, ShieldPlus, Palette, Users, Shield, Database } from 'lucide-react';
import EvolutionChart from '../components/charts/EvolutionChart';

export default function ComparativeAnalysisPage() {

  return (
    <div className="flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

        {/* Twitter/X Card */}
        <div className="bg-panel border border-border rounded-xl p-6 flex items-center justify-between shadow-sm">
          <div className="flex flex-col items-center gap-2">
            <div className="w-16 h-16 rounded-2xl bg-blue-500/10 flex items-center justify-center text-blue-500 text-4xl">
              <span className="font-bold">𝕏</span>
            </div>
            <p className="text-sm font-bold text-blue-500">Twitter/X</p>
          </div>
          <div className="flex gap-8 text-center flex-1 justify-end">
            <div className="flex flex-col items-start text-left">
              <p className="text-sm font-medium text-muted mb-1">Active Communities</p>
              <h3 className="text-2xl font-bold text-text-heading">742</h3>
              <p className="text-[10px] text-success font-medium">↑ 8.7% vs Apr 1 - Apr 30</p>
            </div>
            <div className="flex flex-col items-start text-left">
              <p className="text-sm font-medium text-muted mb-1">Total Messages</p>
              <h3 className="text-2xl font-bold text-text-heading">4.91M</h3>
              <p className="text-[10px] text-success font-medium">↑ 12.1% vs Apr 1 - Apr 30</p>
            </div>
            <div className="flex flex-col items-start text-left">
              <p className="text-sm font-medium text-muted mb-1">Persistence Score (WIF)</p>
              <h3 className="text-2xl font-bold text-text-heading">0.63</h3>
              <p className="text-[10px] text-success font-medium">↑ 8.7% vs Apr 1 - Apr 30</p>
            </div>
            <div className="flex flex-col items-start text-left">
              <p className="text-sm font-medium text-muted mb-1">Thematic Diversity</p>
              <h3 className="text-2xl font-bold text-text-heading">7.1</h3>
              <p className="text-[10px] text-success font-medium">↑ 4.5% vs Apr 1 - Apr 30</p>
            </div>
          </div>
        </div>

        {/* Telegram Card */}
        <div className="bg-panel border border-border rounded-xl p-6 flex items-center justify-between shadow-sm">
          <div className="flex flex-col items-center gap-2">
             <div className="w-16 h-16 rounded-2xl bg-purple-500/10 flex items-center justify-center text-purple-500 text-5xl">
              <span className="font-bold">✈</span>
            </div>
            <p className="text-sm font-bold text-purple-500">Telegram</p>
          </div>
          <div className="flex gap-8 text-center flex-1 justify-end">
            <div className="flex flex-col items-start text-left">
              <p className="text-sm font-medium text-muted mb-1">Active Communities</p>
              <h3 className="text-2xl font-bold text-text-heading">506</h3>
              <p className="text-[10px] text-success font-medium">↑ 5.4% vs Apr 1 - Apr 30</p>
            </div>
            <div className="flex flex-col items-start text-left">
              <p className="text-sm font-medium text-muted mb-1">Total Messages</p>
              <h3 className="text-2xl font-bold text-text-heading">3.76M</h3>
              <p className="text-[10px] text-success font-medium">↑ 15.3% vs Apr 1 - Apr 30</p>
            </div>
            <div className="flex flex-col items-start text-left">
              <p className="text-sm font-medium text-muted mb-1">Persistence Score (WIF)</p>
              <h3 className="text-2xl font-bold text-text-heading">0.69</h3>
              <p className="text-[10px] text-success font-medium">↑ 5.4% vs Apr 1 - Apr 30</p>
            </div>
            <div className="flex flex-col items-start text-left">
              <p className="text-sm font-medium text-muted mb-1">Thematic Diversity</p>
              <h3 className="text-2xl font-bold text-text-heading">5.2</h3>
              <p className="text-[10px] text-success font-medium">↑ 3.1% vs Apr 1 - Apr 30</p>
            </div>
          </div>
        </div>

      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        <div className="lg:col-span-2 xl:col-span-3 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <EvolutionChart title="Message Volume Over Time" />
          <EvolutionChart title="Persistence Score (WIF) Over Time" />

          {/* Theme Distribution Bar Chart Mockup */}
          <div className="bg-panel border border-border rounded-xl p-6">
            <h3 className="text-lg font-bold text-text-heading mb-1">Theme Distribution <span className="text-muted font-normal text-sm">(by Message Volume)</span></h3>
            <p className="text-sm text-muted mb-6">Share of total messages by dominant theme</p>

            <div className="flex justify-between gap-8">
              <div className="w-1/2">
                <p className="text-sm font-bold text-blue-500 mb-4">Twitter/X</p>
                <div className="flex flex-col gap-3 text-sm">
                  <div className="flex items-center justify-between"><span className="w-24 text-text-heading text-xs">Personal Support</span> <div className="flex-1 mx-2 h-2 bg-panel-soft rounded-full"><div className="h-full bg-blue-500 rounded-full" style={{width: '22%'}}></div></div> <span className="text-blue-500 font-medium text-xs">22%</span></div>
                  <div className="flex items-center justify-between"><span className="w-24 text-text-heading text-xs">Current Events</span> <div className="flex-1 mx-2 h-2 bg-panel-soft rounded-full"><div className="h-full bg-blue-500 rounded-full" style={{width: '18%'}}></div></div> <span className="text-muted text-xs">18%</span></div>
                  <div className="flex items-center justify-between"><span className="w-24 text-text-heading text-xs">Civic Discourse</span> <div className="flex-1 mx-2 h-2 bg-panel-soft rounded-full"><div className="h-full bg-blue-500 rounded-full" style={{width: '16%'}}></div></div> <span className="text-muted text-xs">16%</span></div>
                  <div className="flex items-center justify-between"><span className="w-24 text-text-heading text-xs">Education</span> <div className="flex-1 mx-2 h-2 bg-panel-soft rounded-full"><div className="h-full bg-blue-500 rounded-full" style={{width: '13%'}}></div></div> <span className="text-muted text-xs">13%</span></div>
                  <div className="flex items-center justify-between"><span className="w-24 text-text-heading text-xs">Emotional Topics</span> <div className="flex-1 mx-2 h-2 bg-panel-soft rounded-full"><div className="h-full bg-blue-500 rounded-full" style={{width: '11%'}}></div></div> <span className="text-muted text-xs">11%</span></div>
                  <div className="flex items-center justify-between"><span className="w-24 text-text-heading text-xs">News Discussion</span> <div className="flex-1 mx-2 h-2 bg-panel-soft rounded-full"><div className="h-full bg-blue-500 rounded-full" style={{width: '9%'}}></div></div> <span className="text-muted text-xs">9%</span></div>
                  <div className="flex items-center justify-between"><span className="w-24 text-text-heading text-xs">Other</span> <div className="flex-1 mx-2 h-2 bg-panel-soft rounded-full"><div className="h-full bg-muted/30 rounded-full" style={{width: '11%'}}></div></div> <span className="text-muted text-xs">11%</span></div>
                </div>
              </div>
              <div className="w-1/2">
                <p className="text-sm font-bold text-purple-500 mb-4">Telegram</p>
                <div className="flex flex-col gap-3 text-sm">
                  <div className="flex items-center justify-between"><span className="w-24 text-text-heading text-xs">Personal Support</span> <div className="flex-1 mx-2 h-2 bg-panel-soft rounded-full"><div className="h-full bg-purple-500 rounded-full" style={{width: '24%'}}></div></div> <span className="text-muted text-xs">24%</span></div>
                  <div className="flex items-center justify-between"><span className="w-24 text-text-heading text-xs">Current Events</span> <div className="flex-1 mx-2 h-2 bg-panel-soft rounded-full"><div className="h-full bg-purple-500 rounded-full" style={{width: '19%'}}></div></div> <span className="text-muted text-xs">19%</span></div>
                  <div className="flex items-center justify-between"><span className="w-24 text-text-heading text-xs">Education</span> <div className="flex-1 mx-2 h-2 bg-panel-soft rounded-full"><div className="h-full bg-purple-500 rounded-full" style={{width: '16%'}}></div></div> <span className="text-muted text-xs">16%</span></div>
                  <div className="flex items-center justify-between"><span className="w-24 text-text-heading text-xs">Civic Discourse</span> <div className="flex-1 mx-2 h-2 bg-panel-soft rounded-full"><div className="h-full bg-purple-500 rounded-full" style={{width: '12%'}}></div></div> <span className="text-muted text-xs">12%</span></div>
                  <div className="flex items-center justify-between"><span className="w-24 text-text-heading text-xs">Emotional Topics</span> <div className="flex-1 mx-2 h-2 bg-panel-soft rounded-full"><div className="h-full bg-purple-500 rounded-full" style={{width: '11%'}}></div></div> <span className="text-muted text-xs">11%</span></div>
                  <div className="flex items-center justify-between"><span className="w-24 text-text-heading text-xs">News Discussion</span> <div className="flex-1 mx-2 h-2 bg-panel-soft rounded-full"><div className="h-full bg-purple-500 rounded-full" style={{width: '7%'}}></div></div> <span className="text-muted text-xs">7%</span></div>
                  <div className="flex items-center justify-between"><span className="w-24 text-text-heading text-xs">Other</span> <div className="flex-1 mx-2 h-2 bg-panel-soft rounded-full"><div className="h-full bg-muted/30 rounded-full" style={{width: '11%'}}></div></div> <span className="text-muted text-xs">11%</span></div>
                </div>
              </div>
            </div>
          </div>

          {/* Theme Overlap Venn Diagram Mockup */}
          <div className="bg-panel border border-border rounded-xl p-6 relative overflow-hidden flex flex-col justify-between">
            <div>
              <h3 className="text-lg font-bold text-text-heading mb-1">Theme Overlap</h3>
              <p className="text-sm text-muted mb-6">Overlap in dominant themes by message volume</p>
            </div>

            <div className="relative h-48 flex items-center justify-center -mt-8">
              {/* Fake Venn */}
              <div className="absolute w-44 h-44 rounded-full bg-blue-500/10 border-2 border-blue-500/20 -translate-x-12 flex flex-col items-center justify-center pl-8 text-center mix-blend-screen">
                <span className="text-blue-500 font-bold text-xs">Twitter/X<br/>Exclusive</span>
                <span className="text-2xl font-bold text-text-heading mt-1">32%</span>
              </div>
              <div className="absolute w-44 h-44 rounded-full bg-purple-500/10 border-2 border-purple-500/20 translate-x-12 flex flex-col items-center justify-center pr-8 text-center mix-blend-screen">
                <span className="text-purple-500 font-bold text-xs">Telegram<br/>Exclusive</span>
                <span className="text-2xl font-bold text-text-heading mt-1">22%</span>
              </div>
              <div className="absolute z-10 flex flex-col items-center text-center">
                <span className="text-indigo-400 font-bold text-xs">Shared<br/>Themes</span>
                <span className="text-3xl font-bold text-text-heading mt-1">46%</span>
              </div>
            </div>

            <div className="flex justify-center gap-6 mt-4 text-[10px] text-muted font-medium">
              <span className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-blue-500"></span> Exclusive to Twitter/X</span>
              <span className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-indigo-500"></span> Shared Themes</span>
              <span className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-purple-500"></span> Exclusive to Telegram</span>
            </div>
          </div>

        </div>

        {/* Right column */}
        <div className="flex flex-col gap-6">
          <div className="bg-panel border border-border rounded-xl p-6">
             <div className="flex items-center gap-2 mb-4">
               <Lightbulb className="text-blue-500" size={20} />
               <h3 className="text-sm font-bold text-text-heading">Key Findings</h3>
             </div>

             <div className="flex flex-col gap-5">
               <div className="flex gap-4">
                 <div className="w-8 h-8 rounded-full bg-blue-500/10 text-blue-500 flex items-center justify-center shrink-0"><TrendingUp size={16} /></div>
                 <div>
                   <p className="text-xs font-bold text-text-heading mb-1">Higher Message Volume on Twitter/X</p>
                   <p className="text-[10px] text-muted leading-relaxed">Twitter/X generated 30% more messages than Telegram during the selected period.</p>
                 </div>
               </div>
               <div className="flex gap-4">
                 <div className="w-8 h-8 rounded-full bg-purple-500/10 text-purple-500 flex items-center justify-center shrink-0"><ShieldPlus size={16} /></div>
                 <div>
                   <p className="text-xs font-bold text-text-heading mb-1">Stronger Persistence on Telegram</p>
                   <p className="text-[10px] text-muted leading-relaxed">Telegram communities show a higher persistence score throughout the month.</p>
                 </div>
               </div>
               <div className="flex gap-4">
                 <div className="w-8 h-8 rounded-full bg-green-500/10 text-green-500 flex items-center justify-center shrink-0"><Palette size={16} /></div>
                 <div>
                   <p className="text-xs font-bold text-text-heading mb-1">Broader Thematic Diversity on Twitter/X</p>
                   <p className="text-[10px] text-muted leading-relaxed">Twitter/X communities cover a wider range of themes compared to Telegram.</p>
                 </div>
               </div>
               <div className="flex gap-4">
                 <div className="w-8 h-8 rounded-full bg-orange-500/10 text-orange-500 flex items-center justify-center shrink-0"><Users size={16} /></div>
                 <div>
                   <p className="text-xs font-bold text-text-heading mb-1">Related But Distinct Audiences</p>
                   <p className="text-[10px] text-muted leading-relaxed">Both platforms share overlapping themes, but engagement patterns differ significantly.</p>
                 </div>
               </div>
             </div>
          </div>

          <div className="bg-panel border border-border rounded-xl p-6">
            <h3 className="text-sm font-bold text-text-heading mb-4 flex items-center gap-2">
              <Database size={16} className="text-blue-500" />
              Data Summary
            </h3>
            <div className="flex flex-col gap-3 text-xs">
              <div className="flex justify-between border-b border-border/30 pb-2">
                <span className="text-muted">Time Range</span>
                <span className="text-text-heading font-medium">May 1 - May 31, 2024</span>
              </div>
              <div className="flex justify-between border-b border-border/30 pb-2">
                <span className="text-muted">Platforms</span>
                <span className="text-text-heading font-medium">Twitter/X vs Telegram</span>
              </div>
              <div className="flex justify-between border-b border-border/30 pb-2">
                <span className="text-muted">Affinity Metric</span>
                <span className="text-text-heading font-medium">WIF</span>
              </div>
              <div className="flex justify-between border-b border-border/30 pb-2">
                <span className="text-muted">Min Community Size</span>
                <span className="text-text-heading font-medium">50</span>
              </div>
              <div className="flex justify-between border-b border-border/30 pb-2">
                <span className="text-muted">Total Communities</span>
                <span className="text-text-heading font-medium">1,248</span>
              </div>
              <div className="flex justify-between border-b border-border/30 pb-2">
                <span className="text-muted">Total Messages</span>
                <span className="text-text-heading font-medium">8.67M</span>
              </div>
            </div>

            <div className="mt-4 pt-4 flex items-center justify-between">
              <span className="text-xs text-muted">Data Source Status</span>
              <span className="text-xs font-medium text-success flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-success flex items-center justify-center text-[8px] text-white">✓</div> All Systems Operational
              </span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
