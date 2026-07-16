import { useOutletContext } from 'react-router-dom';
import { RefreshCcw, Users, ShieldCheck, Star, ArrowRight, TrendingDown, Info, Download } from 'lucide-react';

export default function CommunityTransitionsPage() {
  const { summary } = useOutletContext();

  return (
    <div className="flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-500">
              <RefreshCcw size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted flex items-center gap-1">
                Retention Rate 
                <span className="w-3.5 h-3.5 rounded-full border border-muted flex items-center justify-center text-[8px] cursor-help">i</span>
              </p>
              <h3 className="text-2xl font-bold text-text-heading">64.2%</h3>
            </div>
          </div>
          <p className="text-xs text-success font-medium flex items-center gap-1">↑ 4.8pp <span className="text-muted font-normal">vs Apr 1 - Apr 30</span></p>
        </div>
        
        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-500">
              <Users size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted flex items-center gap-1">
                Members Transitioned 
                <span className="w-3.5 h-3.5 rounded-full border border-muted flex items-center justify-center text-[8px] cursor-help">i</span>
              </p>
              <h3 className="text-2xl font-bold text-text-heading">1.42M</h3>
            </div>
          </div>
          <p className="text-xs text-success font-medium flex items-center gap-1">↑ 12.6% <span className="text-muted font-normal">vs Apr 1 - Apr 30</span></p>
        </div>
        
        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center text-green-500">
              <ShieldCheck size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted flex items-center gap-1">
                Stable Communities 
                <span className="w-3.5 h-3.5 rounded-full border border-muted flex items-center justify-center text-[8px] cursor-help">i</span>
              </p>
              <h3 className="text-2xl font-bold text-text-heading">128</h3>
            </div>
          </div>
          <p className="text-xs text-success font-medium flex items-center gap-1">↑ 9.4% <span className="text-muted font-normal">vs Apr 1 - Apr 30</span></p>
        </div>
        
        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-orange-500/10 flex items-center justify-center text-orange-500">
              <Star size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted flex items-center gap-1">
                New Communities 
                <span className="w-3.5 h-3.5 rounded-full border border-muted flex items-center justify-center text-[8px] cursor-help">i</span>
              </p>
              <h3 className="text-2xl font-bold text-text-heading">74</h3>
            </div>
          </div>
          <p className="text-xs text-success font-medium flex items-center gap-1">↑ 16.7% <span className="text-muted font-normal">vs Apr 1 - Apr 30</span></p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        <div className="xl:col-span-3 flex flex-col gap-6">
          
          {/* Member Overlap Diagram */}
          <div className="bg-panel border border-border rounded-xl p-6 flex flex-col relative overflow-hidden">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-sm font-bold text-text-heading flex items-center gap-2">
                Community Transitions (Member Overlap)
                <div className="w-4 h-4 rounded-full border border-border flex items-center justify-center text-muted text-[10px] cursor-help">i</div>
              </h3>
              <select className="bg-transparent border border-border rounded-lg text-xs text-text-heading font-medium focus:outline-none cursor-pointer py-1 px-2">
                <option>6 Months</option>
                <option>12 Months</option>
              </select>
            </div>
            
            <div className="flex flex-1 min-h-[250px] relative mt-4">
              {/* Legend */}
              <div className="w-32 flex flex-col justify-start gap-4 z-10 pt-8 border-r border-border/50 pr-4">
                <p className="text-xs font-bold text-text-heading mb-1">Community Themes</p>
                <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-blue-500"></span><span className="text-[10px] text-muted font-medium">Current Events</span></div>
                <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-indigo-500"></span><span className="text-[10px] text-muted font-medium">Personal Support</span></div>
                <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-teal-500"></span><span className="text-[10px] text-muted font-medium">Civic Discourse</span></div>
                <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-orange-400"></span><span className="text-[10px] text-muted font-medium">Education</span></div>
                <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-pink-500"></span><span className="text-[10px] text-muted font-medium">Emotional Topics</span></div>
                <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-red-400"></span><span className="text-[10px] text-muted font-medium">News Discussion</span></div>
                <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-gray-400"></span><span className="text-[10px] text-muted font-medium">Other</span></div>
              </div>
              
              {/* Mockup Sankey Container */}
              <div className="flex-1 flex flex-col relative px-4">
                {/* Headers */}
                <div className="flex justify-between w-full text-xs font-bold text-text-heading px-8 pb-4">
                  <span>Dec '23</span>
                  <span>Jan '24</span>
                  <span>Feb '24</span>
                  <span>Mar '24</span>
                  <span>Apr '24</span>
                  <span>May '24</span>
                </div>
                
                {/* Decorative SVG Paths for Sankey flows */}
                <div className="absolute inset-0 top-10 pointer-events-none opacity-20">
                  <svg width="100%" height="100%" preserveAspectRatio="none">
                    <path d="M 50 20 C 150 20, 150 20, 250 20 C 350 20, 350 40, 450 40 C 550 40, 550 20, 650 20" stroke="#3b82f6" strokeWidth="15" fill="none" />
                    <path d="M 50 50 C 150 50, 150 80, 250 80 C 350 80, 350 50, 450 50 C 550 50, 550 80, 650 80" stroke="#6366f1" strokeWidth="15" fill="none" />
                    <path d="M 50 80 C 150 80, 150 50, 250 50 C 350 50, 350 110, 450 110 C 550 110, 550 110, 650 110" stroke="#14b8a6" strokeWidth="15" fill="none" />
                    <path d="M 50 110 C 150 110, 150 110, 250 110 C 350 110, 350 80, 450 80 C 550 80, 550 50, 650 50" stroke="#fb923c" strokeWidth="15" fill="none" />
                  </svg>
                </div>
                
                {/* Mock Nodes Column Data */}
                <div className="flex-1 flex justify-between relative px-8 pb-10">
                  {[1, 2, 3, 4, 5, 6].map((col, index) => (
                    <div key={col} className="flex flex-col gap-2 w-12 z-10">
                      <div className="w-full h-[24px] bg-blue-500 rounded flex items-center justify-center text-[8px] text-white font-bold">{index === 0 ? '1.8K' : index === 5 ? '1.9K' : ''}</div>
                      <div className="w-full h-[22px] bg-indigo-500 rounded flex items-center justify-center text-[8px] text-white font-bold">{index === 0 ? '1.4K' : index === 5 ? '1.5K' : ''}</div>
                      <div className="w-full h-[20px] bg-teal-500 rounded flex items-center justify-center text-[8px] text-white font-bold">{index === 0 ? '1.1K' : index === 5 ? '1.2K' : ''}</div>
                      <div className="w-full h-[18px] bg-orange-400 rounded flex items-center justify-center text-[8px] text-white font-bold">{index === 0 ? '900' : index === 5 ? '950' : ''}</div>
                      <div className="w-full h-[16px] bg-pink-500 rounded flex items-center justify-center text-[8px] text-white font-bold">{index === 0 ? '800' : index === 5 ? '820' : ''}</div>
                      <div className="w-full h-[14px] bg-red-400 rounded flex items-center justify-center text-[8px] text-white font-bold">{index === 0 ? '700' : index === 5 ? '720' : ''}</div>
                      <div className="w-full h-[12px] bg-gray-400 rounded flex items-center justify-center text-[8px] text-white font-bold">{index === 0 ? '600' : index === 5 ? '650' : ''}</div>
                    </div>
                  ))}
                </div>
                
                {/* Bottom Timeline Retention */}
                <div className="border-t border-border/50 pt-3 text-[10px] text-muted font-medium text-center relative flex justify-between px-16">
                   <div className="absolute top-[-10px] left-1/2 -translate-x-1/2 bg-panel px-2 text-xs">
                     % of Members Retained Month over Month
                   </div>
                   <span></span>
                   <span>68.1%</span>
                   <span>66.7%</span>
                   <span>65.3%</span>
                   <span>64.9%</span>
                   <span>64.2%</span>
                </div>
              </div>
            </div>
          </div>

          {/* Transition Matrix */}
          <div className="bg-panel border border-border rounded-xl p-6 flex flex-col">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-sm font-bold text-text-heading flex items-center gap-2">
                Transition Matrix <span className="text-muted font-normal text-xs">(Member Flow Summary)</span>
                <div className="w-4 h-4 rounded-full border border-border flex items-center justify-center text-muted text-[10px] cursor-help">i</div>
              </h3>
              <button className="flex items-center gap-1.5 px-3 py-1.5 border border-border rounded-lg text-xs font-semibold hover:bg-panel-soft transition-colors">
                <Download size={14} /> Download Matrix
              </button>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs min-w-[700px]">
                <thead>
                  <tr className="font-bold text-text-heading border-b border-border">
                    <th className="py-3 px-2">From \ To</th>
                    <th className="py-3 px-2 text-center">Current Events</th>
                    <th className="py-3 px-2 text-center">Personal Support</th>
                    <th className="py-3 px-2 text-center">Civic Discourse</th>
                    <th className="py-3 px-2 text-center">Education</th>
                    <th className="py-3 px-2 text-center">Emotional Topics</th>
                    <th className="py-3 px-2 text-center">News Discussion</th>
                    <th className="py-3 px-2 text-center">Other</th>
                    <th className="py-3 px-2 text-center">Exited</th>
                  </tr>
                </thead>
                <tbody className="text-muted font-medium">
                  <tr className="border-b border-border/30 hover:bg-panel-soft transition-colors">
                    <td className="py-3 px-2 flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-blue-500 shrink-0"></div>Current Events</td>
                    <td className="py-3 px-2 text-center text-blue-900 bg-blue-500/30 font-bold">53.2%</td>
                    <td className="py-3 px-2 text-center">12.8%</td>
                    <td className="py-3 px-2 text-center">9.6%</td>
                    <td className="py-3 px-2 text-center">6.2%</td>
                    <td className="py-3 px-2 text-center">5.1%</td>
                    <td className="py-3 px-2 text-center">7.2%</td>
                    <td className="py-3 px-2 text-center">2.3%</td>
                    <td className="py-3 px-2 text-center">3.6%</td>
                  </tr>
                  <tr className="border-b border-border/30 hover:bg-panel-soft transition-colors">
                    <td className="py-3 px-2 flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-indigo-500 shrink-0"></div>Personal Support</td>
                    <td className="py-3 px-2 text-center">11.7%</td>
                    <td className="py-3 px-2 text-center text-indigo-900 bg-indigo-500/30 font-bold">56.3%</td>
                    <td className="py-3 px-2 text-center">8.4%</td>
                    <td className="py-3 px-2 text-center">5.8%</td>
                    <td className="py-3 px-2 text-center">5.6%</td>
                    <td className="py-3 px-2 text-center">7.9%</td>
                    <td className="py-3 px-2 text-center">2.5%</td>
                    <td className="py-3 px-2 text-center">1.8%</td>
                  </tr>
                  <tr className="border-b border-border/30 hover:bg-panel-soft transition-colors">
                    <td className="py-3 px-2 flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-teal-500 shrink-0"></div>Civic Discourse</td>
                    <td className="py-3 px-2 text-center">9.2%</td>
                    <td className="py-3 px-2 text-center">9.1%</td>
                    <td className="py-3 px-2 text-center text-teal-900 bg-teal-500/30 font-bold">55.8%</td>
                    <td className="py-3 px-2 text-center">7.6%</td>
                    <td className="py-3 px-2 text-center">5.0%</td>
                    <td className="py-3 px-2 text-center">8.9%</td>
                    <td className="py-3 px-2 text-center">2.6%</td>
                    <td className="py-3 px-2 text-center">1.8%</td>
                  </tr>
                  <tr className="border-b border-border/30 hover:bg-panel-soft transition-colors">
                    <td className="py-3 px-2 flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-orange-400 shrink-0"></div>Education</td>
                    <td className="py-3 px-2 text-center">6.5%</td>
                    <td className="py-3 px-2 text-center">6.3%</td>
                    <td className="py-3 px-2 text-center">7.8%</td>
                    <td className="py-3 px-2 text-center text-orange-900 bg-orange-400/30 font-bold">61.2%</td>
                    <td className="py-3 px-2 text-center">4.7%</td>
                    <td className="py-3 px-2 text-center">8.0%</td>
                    <td className="py-3 px-2 text-center">2.7%</td>
                    <td className="py-3 px-2 text-center">2.8%</td>
                  </tr>
                  <tr className="border-b border-border/30 hover:bg-panel-soft transition-colors">
                    <td className="py-3 px-2 flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-pink-500 shrink-0"></div>Emotional Topics</td>
                    <td className="py-3 px-2 text-center">6.1%</td>
                    <td className="py-3 px-2 text-center">6.4%</td>
                    <td className="py-3 px-2 text-center">6.7%</td>
                    <td className="py-3 px-2 text-center">5.3%</td>
                    <td className="py-3 px-2 text-center text-pink-900 bg-pink-500/30 font-bold">62.0%</td>
                    <td className="py-3 px-2 text-center">9.2%</td>
                    <td className="py-3 px-2 text-center">2.6%</td>
                    <td className="py-3 px-2 text-center">1.7%</td>
                  </tr>
                  <tr className="border-b border-border/30 hover:bg-panel-soft transition-colors">
                    <td className="py-3 px-2 flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-red-400 shrink-0"></div>News Discussion</td>
                    <td className="py-3 px-2 text-center">7.6%</td>
                    <td className="py-3 px-2 text-center">8.1%</td>
                    <td className="py-3 px-2 text-center">9.4%</td>
                    <td className="py-3 px-2 text-center">6.1%</td>
                    <td className="py-3 px-2 text-center">5.2%</td>
                    <td className="py-3 px-2 text-center text-red-900 bg-red-400/30 font-bold">57.6%</td>
                    <td className="py-3 px-2 text-center">3.0%</td>
                    <td className="py-3 px-2 text-center">2.9%</td>
                  </tr>
                  <tr className="hover:bg-panel-soft transition-colors">
                    <td className="py-3 px-2 flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-gray-400 shrink-0"></div>Other</td>
                    <td className="py-3 px-2 text-center">5.4%</td>
                    <td className="py-3 px-2 text-center">5.1%</td>
                    <td className="py-3 px-2 text-center">5.6%</td>
                    <td className="py-3 px-2 text-center">4.3%</td>
                    <td className="py-3 px-2 text-center">3.9%</td>
                    <td className="py-3 px-2 text-center">6.2%</td>
                    <td className="py-3 px-2 text-center text-gray-900 bg-gray-400/40 font-bold">62.1%</td>
                    <td className="py-3 px-2 text-center">7.4%</td>
                  </tr>
                </tbody>
              </table>
            </div>
            
            <p className="text-[10px] text-muted mt-4">Values represent the percentage of members transitioning from one theme to another in the next month.</p>
          </div>
        </div>

        {/* Right Sidebar Column */}
        <div className="flex flex-col gap-6">
          
          <div className="bg-panel border border-border rounded-xl p-6">
            <h3 className="text-sm font-bold text-text-heading mb-4 flex items-center gap-2">
              Retention Insights
              <div className="w-4 h-4 rounded-full border border-border flex items-center justify-center text-muted text-[10px] cursor-help">i</div>
            </h3>
            
            <div className="mb-4">
              <p className="text-xs text-muted font-medium mb-1">Retention Rate</p>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-3xl font-bold text-text-heading leading-tight">64.2%</h3>
                  <p className="text-xs text-success font-medium flex items-center gap-0.5">↑ 4.8pp <span className="text-muted font-normal">vs Apr 1 - Apr 30</span></p>
                </div>
                {/* Sparkline Mock */}
                <div className="w-20 h-10">
                  <svg viewBox="0 0 100 30" className="w-full h-full overflow-visible">
                    <path d="M 0 25 L 20 20 L 40 22 L 60 10 L 80 15 L 100 5" stroke="#3b82f6" strokeWidth="2" fill="none" />
                  </svg>
                </div>
              </div>
            </div>
            
            <p className="text-xs text-muted leading-relaxed">
              Overall retention improved this month, with stronger stability in <span className="font-semibold text-text-heading">Education</span> and <span className="font-semibold text-text-heading">Personal Support</span> communities.
            </p>
          </div>
          
          <div className="bg-panel border border-border rounded-xl p-6">
            <h3 className="text-sm font-bold text-text-heading mb-4">Top Transition Paths</h3>
            
            <div className="flex flex-col gap-4 text-xs font-medium">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-muted w-3">1.</span>
                  <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-500"></div> Current Events 
                    <ArrowRight size={10} className="text-muted" /> 
                    Personal Support
                  </div>
                </div>
                <span className="font-bold text-text-heading">12.8%</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-muted w-3">2.</span>
                  <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-red-400"></div> News Discussion 
                    <ArrowRight size={10} className="text-muted" /> 
                    Current Events
                  </div>
                </div>
                <span className="font-bold text-text-heading">10.4%</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-muted w-3">3.</span>
                  <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-teal-500"></div> Civic Discourse 
                    <ArrowRight size={10} className="text-muted" /> 
                    News Discussion
                  </div>
                </div>
                <span className="font-bold text-text-heading">9.3%</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-muted w-3">4.</span>
                  <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-indigo-500"></div> Personal Support 
                    <ArrowRight size={10} className="text-muted" /> 
                    Current Events
                  </div>
                </div>
                <span className="font-bold text-text-heading">9.1%</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-muted w-3">5.</span>
                  <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-orange-400"></div> Education 
                    <ArrowRight size={10} className="text-muted" /> 
                    Civic Discourse
                  </div>
                </div>
                <span className="font-bold text-text-heading">7.8%</span>
              </div>
            </div>
            
            <div className="mt-6 flex justify-end">
              <button className="text-xs text-primary font-medium hover:text-primary/80 transition-colors flex items-center gap-1">
                View all transition paths <ArrowRight size={12} />
              </button>
            </div>
          </div>
          
          <div className="bg-panel border border-border rounded-xl p-6">
            <h3 className="text-sm font-bold text-text-heading mb-4 flex items-center gap-2">
              Churn & Decline Notes
              <div className="w-4 h-4 rounded-full border border-border flex items-center justify-center text-muted text-[10px] cursor-help">i</div>
            </h3>
            
            <div className="flex flex-col gap-4 text-xs text-muted leading-relaxed">
              <div className="flex gap-3">
                <div className="w-6 h-6 rounded-full bg-danger/10 text-danger flex items-center justify-center shrink-0 mt-0.5">
                  <TrendingDown size={12} />
                </div>
                <p><span className="font-semibold text-text-heading">Emotional Topics</span> communities saw a 3.1pp decline in retention.</p>
              </div>
              <div className="flex gap-3">
                <div className="w-6 h-6 rounded-full bg-orange-500/10 text-orange-500 flex items-center justify-center shrink-0 mt-0.5">
                  <ArrowRight size={12} className="rotate-45" />
                </div>
                <p>7.4% of members from Other themes exited the community network.</p>
              </div>
              <div className="flex gap-3">
                <div className="w-6 h-6 rounded-full bg-blue-500/10 text-blue-500 flex items-center justify-center shrink-0 mt-0.5">
                  <Info size={12} />
                </div>
                <p>New Communities grew by 16.7%, driven by Education and Civic Discourse.</p>
              </div>
            </div>
            
            <div className="mt-6 flex justify-end">
              <button className="text-xs text-primary font-medium hover:text-primary/80 transition-colors flex items-center gap-1">
                View churn analysis <ArrowRight size={12} />
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
