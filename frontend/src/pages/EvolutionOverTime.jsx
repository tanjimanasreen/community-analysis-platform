import { useOutletContext } from 'react-router-dom';
import { Users, MessageSquare, ShieldCheck, Calendar, TrendingUp, Shield } from 'lucide-react';
import EvolutionChart from '../components/charts/EvolutionChart';

export default function EvolutionOverTimePage() {
  const { summary } = useOutletContext();

  return (
    <div className="flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric Cards Mockup */}
        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-500">
              <Users size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted flex items-center gap-1">
                Community Growth
                <span className="w-3.5 h-3.5 rounded-full border border-muted flex items-center justify-center text-[8px] cursor-help">i</span>
              </p>
              <h3 className="text-2xl font-bold text-text-heading">1,248</h3>
            </div>
          </div>
          <p className="text-xs text-success font-medium flex items-center gap-1">↑ 12.4% <span className="text-muted font-normal">vs Apr 1 - Apr 30</span></p>
        </div>

        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-500">
              <MessageSquare size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted flex items-center gap-1">
                Message Growth
                <span className="w-3.5 h-3.5 rounded-full border border-muted flex items-center justify-center text-[8px] cursor-help">i</span>
              </p>
              <h3 className="text-2xl font-bold text-text-heading">8.67M</h3>
            </div>
          </div>
          <p className="text-xs text-success font-medium flex items-center gap-1">↑ 18.7% <span className="text-muted font-normal">vs Apr 1 - Apr 30</span></p>
        </div>

        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center text-green-500">
              <ShieldCheck size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted flex items-center gap-1">
                Persistence Trend (WIF)
                <span className="w-3.5 h-3.5 rounded-full border border-muted flex items-center justify-center text-[8px] cursor-help">i</span>
              </p>
              <h3 className="text-2xl font-bold text-text-heading">0.68</h3>
            </div>
          </div>
          <p className="text-xs text-success font-medium flex items-center gap-1">↑ 6.1% <span className="text-muted font-normal">vs Apr 1 - Apr 30</span></p>
        </div>

        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-orange-500/10 flex items-center justify-center text-orange-500">
              <Calendar size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted flex items-center gap-1">
                Peak Activity Month
                <span className="w-3.5 h-3.5 rounded-full border border-muted flex items-center justify-center text-[8px] cursor-help">i</span>
              </p>
              <h3 className="text-2xl font-bold text-text-heading">Mar 2024</h3>
            </div>
          </div>
          <p className="text-xs text-muted font-normal">2.03M Messages</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <EvolutionChart title="Communities Over Time" />
        <EvolutionChart title="Message Volume Over Time" />
        <EvolutionChart title="Persistence Score (WIF) Over Time" />

        {/* Platform Comparison Cards */}
        <div className="bg-panel border border-border rounded-xl p-6 flex flex-col">
          <h3 className="text-sm font-bold text-text-heading mb-4 flex items-center gap-2">
            Platform Comparison <span className="text-muted font-normal text-xs">(May 1 - May 31, 2024)</span>
            <div className="w-3.5 h-3.5 rounded-full border border-border flex items-center justify-center text-muted text-[8px] cursor-help">i</div>
          </h3>

          <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Twitter/X Card */}
            <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-5 flex flex-col justify-between">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-blue-500 font-bold text-xl leading-none">𝕏</span>
                <span className="font-bold text-blue-500">Twitter/X</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <p className="text-xs text-muted font-medium mb-1">Communities</p>
                  <p className="text-lg font-bold text-text-heading">742</p>
                  <p className="text-[10px] text-success font-medium flex items-center gap-0.5">↑ 8.7%</p>
                </div>
                <div>
                  <p className="text-xs text-muted font-medium mb-1">Messages</p>
                  <p className="text-lg font-bold text-text-heading">1.72M</p>
                  <p className="text-[10px] text-success font-medium flex items-center gap-0.5">↑ 14.2%</p>
                </div>
                <div>
                  <p className="text-xs text-muted font-medium mb-1">WIF</p>
                  <p className="text-lg font-bold text-text-heading">0.63</p>
                  <p className="text-[10px] text-success font-medium flex items-center gap-0.5">↑ 5.4%</p>
                </div>
              </div>
            </div>

            {/* Telegram Card */}
            <div className="bg-purple-500/5 border border-purple-500/20 rounded-xl p-5 flex flex-col justify-between">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-purple-500 font-bold text-xl leading-none">✈</span>
                <span className="font-bold text-purple-500">Telegram</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <p className="text-xs text-muted font-medium mb-1">Communities</p>
                  <p className="text-lg font-bold text-text-heading">506</p>
                  <p className="text-[10px] text-success font-medium flex items-center gap-0.5">↑ 12.1%</p>
                </div>
                <div>
                  <p className="text-xs text-muted font-medium mb-1">Messages</p>
                  <p className="text-lg font-bold text-text-heading">1.09M</p>
                  <p className="text-[10px] text-success font-medium flex items-center gap-0.5">↑ 21.3%</p>
                </div>
                <div>
                  <p className="text-xs text-muted font-medium mb-1">WIF</p>
                  <p className="text-lg font-bold text-text-heading">0.53</p>
                  <p className="text-[10px] text-danger font-medium flex items-center gap-0.5">↓ -0.8%</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="bg-panel border border-border rounded-xl p-6 xl:col-span-2 flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-bold text-text-heading flex items-center gap-2">
              Key Milestones & Events
              <div className="w-4 h-4 rounded-full border border-border flex items-center justify-center text-muted text-[10px] cursor-help">i</div>
            </h3>
          </div>
          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left border-collapse min-w-[500px]">
              <thead>
                <tr className="text-xs text-text-heading font-bold border-b border-border">
                  <th className="pb-3">Date</th>
                  <th className="pb-3">Event</th>
                  <th className="pb-3 text-center">Impact</th>
                  <th className="pb-3 text-center">Platforms</th>
                </tr>
              </thead>
              <tbody className="text-sm">
                <tr className="border-b border-border/30 hover:bg-panel-soft transition-colors">
                  <td className="py-4 flex items-center gap-2 whitespace-nowrap"><div className="w-2 h-2 rounded-full bg-primary shrink-0"></div> May 5, 2024</td>
                  <td className="py-4 text-text-heading font-medium">Viral discussion on AI regulation</td>
                  <td className="py-4 text-center text-success flex items-center justify-center gap-1 font-medium"><span className="text-xs">◇</span> High</td>
                  <td className="py-4 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <span className="text-blue-500 font-bold">𝕏</span>
                      <span className="text-primary text-base">✈</span>
                    </div>
                  </td>
                </tr>
                <tr className="border-b border-border/30 hover:bg-panel-soft transition-colors">
                  <td className="py-4 flex items-center gap-2 whitespace-nowrap"><div className="w-2 h-2 rounded-full bg-purple-500 shrink-0"></div> May 14, 2024</td>
                  <td className="py-4 text-text-heading font-medium">New policy announcement sparks debate</td>
                  <td className="py-4 text-center text-success flex items-center justify-center gap-1 font-medium"><span className="text-xs">◇</span> High</td>
                  <td className="py-4 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <span className="text-blue-500 font-bold">𝕏</span>
                      <span className="text-primary text-base">✈</span>
                    </div>
                  </td>
                </tr>
                <tr className="border-b border-border/30 hover:bg-panel-soft transition-colors">
                  <td className="py-4 flex items-center gap-2 whitespace-nowrap"><div className="w-2 h-2 rounded-full bg-orange-500 shrink-0"></div> May 20, 2024</td>
                  <td className="py-4 text-text-heading font-medium">Influencer thread drives community growth</td>
                  <td className="py-4 text-center text-warning flex items-center justify-center gap-1 font-medium"><span className="text-xs">◇</span> Medium</td>
                  <td className="py-4 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <span className="text-blue-500 font-bold">𝕏</span>
                    </div>
                  </td>
                </tr>
                <tr className="hover:bg-panel-soft transition-colors">
                  <td className="py-4 flex items-center gap-2 whitespace-nowrap"><div className="w-2 h-2 rounded-full bg-green-500 shrink-0"></div> May 27, 2024</td>
                  <td className="py-4 text-text-heading font-medium">Community consolidation after event peak</td>
                  <td className="py-4 text-center text-blue-500 flex items-center justify-center gap-1 font-medium"><span className="text-xs">◇</span> Low</td>
                  <td className="py-4 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <span className="text-primary text-base">✈</span>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="flex justify-end mt-4">
            <button className="text-sm text-primary font-medium hover:text-primary/80 transition-colors flex items-center gap-1">
              View all milestones →
            </button>
          </div>
        </div>

        <div className="bg-panel border border-border rounded-xl p-6 flex flex-col">
           <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-bold text-text-heading flex items-center gap-2">
              Trend Notes
              <div className="w-4 h-4 rounded-full border border-border flex items-center justify-center text-muted text-[10px] cursor-help">i</div>
            </h3>
          </div>
          <div className="flex flex-col gap-6 flex-1">
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-full border border-green-500/30 text-green-500 flex items-center justify-center shrink-0">
                <TrendingUp size={16} />
              </div>
              <p className="text-sm text-text-heading leading-relaxed pt-1">Community growth accelerated mid-month, peaking around May 14 driven by policy-related discussions across both platforms.</p>
            </div>

            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-full border border-purple-500/30 text-purple-500 flex items-center justify-center shrink-0">
                <MessageSquare size={16} />
              </div>
              <p className="text-sm text-text-heading leading-relaxed pt-1">Message volume saw its highest surge in the week of May 12-18, with Telegram showing stronger relative growth.</p>
            </div>

            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-full border border-blue-500/30 text-blue-500 flex items-center justify-center shrink-0">
                <Shield size={16} />
              </div>
              <p className="text-sm text-text-heading leading-relaxed pt-1">Persistence (WIF) remained stable overall, while Telegram saw a slight dip toward the end of the month.</p>
            </div>
          </div>

          <div className="flex justify-end mt-6">
            <button className="text-sm text-primary font-medium hover:text-primary/80 transition-colors flex items-center gap-1">
              View detailed analysis →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
