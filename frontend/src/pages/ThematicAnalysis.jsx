import { LayoutGrid, Users, Shield, Flame, ExternalLink } from 'lucide-react';

export default function ThematicAnalysisPage() {

  return (
    <div className="flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric Cards */}
        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-500">
              <LayoutGrid size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted">Total Themes</p>
              <h3 className="text-2xl font-bold text-text-heading">18</h3>
            </div>
          </div>
          <p className="text-xs text-success font-medium flex items-center gap-1">↑ 12.5% <span className="text-muted font-normal">vs Apr 1 - Apr 30</span></p>
        </div>
        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-500">
              <Users size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted">Avg Topics per Community</p>
              <h3 className="text-2xl font-bold text-text-heading">7.4</h3>
            </div>
          </div>
          <p className="text-xs text-success font-medium flex items-center gap-1">↑ 9.3% <span className="text-muted font-normal">vs Apr 1 - Apr 30</span></p>
        </div>
        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center text-green-500">
              <Shield size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted">Dominant Theme</p>
              <h3 className="text-xl font-bold text-text-heading">Personal Support</h3>
            </div>
          </div>
          <p className="text-xs text-muted">23.8% of total conversations</p>
        </div>
        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-orange-500/10 flex items-center justify-center text-orange-500">
              <Flame size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted">Emerging Topics</p>
              <h3 className="text-2xl font-bold text-text-heading">46</h3>
            </div>
          </div>
          <p className="text-xs text-success font-medium flex items-center gap-1">↑ 18.2% <span className="text-muted font-normal">vs Apr 1 - Apr 30</span></p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">

        {/* Main Content Area */}
        <div className="xl:col-span-3 flex flex-col gap-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[400px]">
            {/* Theme Distribution Donut */}
            <div className="bg-panel border border-border rounded-xl p-6 relative flex flex-col">
              <h3 className="text-lg font-bold text-text-heading mb-4 flex items-center gap-2">
                Theme Distribution
                <div className="w-4 h-4 rounded-full border border-border flex items-center justify-center text-muted text-[10px] cursor-help">i</div>
              </h3>

              <div className="flex-1 flex items-center justify-center">
                 {/* Fake Donut Chart */}
                 <div className="relative w-64 h-64">
                   <svg viewBox="0 0 100 100" className="w-full h-full transform -rotate-90">
                     <circle cx="50" cy="50" r="40" fill="transparent" stroke="#bb9af7" strokeWidth="20" strokeDasharray="251.2" strokeDashoffset="0"></circle>
                     <circle cx="50" cy="50" r="40" fill="transparent" stroke="#7aa2f7" strokeWidth="20" strokeDasharray="251.2" strokeDashoffset="60"></circle>
                     <circle cx="50" cy="50" r="40" fill="transparent" stroke="#9ece6a" strokeWidth="20" strokeDasharray="251.2" strokeDashoffset="110"></circle>
                     <circle cx="50" cy="50" r="40" fill="transparent" stroke="#e0af68" strokeWidth="20" strokeDasharray="251.2" strokeDashoffset="150"></circle>
                     <circle cx="50" cy="50" r="40" fill="transparent" stroke="#f7768e" strokeWidth="20" strokeDasharray="251.2" strokeDashoffset="180"></circle>
                     <circle cx="50" cy="50" r="40" fill="transparent" stroke="#2ac3de" strokeWidth="20" strokeDasharray="251.2" strokeDashoffset="205"></circle>
                     <circle cx="50" cy="50" r="40" fill="transparent" stroke="#a9b1d6" strokeWidth="20" strokeDasharray="251.2" strokeDashoffset="220"></circle>
                   </svg>
                   <div className="absolute inset-0 flex flex-col items-center justify-center">
                     <span className="text-xs text-muted">Total Conversations</span>
                     <span className="text-xl font-bold text-text-heading">8.67M</span>
                   </div>
                 </div>

                 {/* Legend */}
                 <div className="absolute left-6 top-16 flex flex-col gap-2 text-xs">
                   <div className="flex items-center gap-4 justify-between w-36"><span className="flex items-center gap-1.5 text-muted"><span className="w-2 h-2 rounded-full bg-[#bb9af7]"></span> Personal Support</span> <span className="font-medium text-text-heading">23.8%</span></div>
                   <div className="flex items-center gap-4 justify-between w-36"><span className="flex items-center gap-1.5 text-muted"><span className="w-2 h-2 rounded-full bg-[#7aa2f7]"></span> Current Events</span> <span className="font-medium text-text-heading">18.7%</span></div>
                   <div className="flex items-center gap-4 justify-between w-36"><span className="flex items-center gap-1.5 text-muted"><span className="w-2 h-2 rounded-full bg-[#9ece6a]"></span> Civic Discourse</span> <span className="font-medium text-text-heading">15.6%</span></div>
                   <div className="flex items-center gap-4 justify-between w-36"><span className="flex items-center gap-1.5 text-muted"><span className="w-2 h-2 rounded-full bg-[#e0af68]"></span> Education</span> <span className="font-medium text-text-heading">12.4%</span></div>
                   <div className="flex items-center gap-4 justify-between w-36"><span className="flex items-center gap-1.5 text-muted"><span className="w-2 h-2 rounded-full bg-[#f7768e]"></span> Emotional Topics</span> <span className="font-medium text-text-heading">9.8%</span></div>
                   <div className="flex items-center gap-4 justify-between w-36"><span className="flex items-center gap-1.5 text-muted"><span className="w-2 h-2 rounded-full bg-[#2ac3de]"></span> News Discussion</span> <span className="font-medium text-text-heading">7.3%</span></div>
                   <div className="flex items-center gap-4 justify-between w-36"><span className="flex items-center gap-1.5 text-muted"><span className="w-2 h-2 rounded-full bg-[#a9b1d6]"></span> Other</span> <span className="font-medium text-text-heading">12.4%</span></div>
                 </div>
              </div>
            </div>

            {/* Topic Clusters Bubble Chart */}
            <div className="bg-panel border border-border rounded-xl p-6 relative">
              <h3 className="text-lg font-bold text-text-heading mb-4 flex items-center gap-2">
                Topic Clusters (by Theme)
                <div className="w-4 h-4 rounded-full border border-border flex items-center justify-center text-muted text-[10px] cursor-help">i</div>
              </h3>

              <div className="relative w-full h-[300px] bg-panel-soft rounded-lg flex items-center justify-center overflow-hidden border border-border">
                <span className="text-muted/30 font-medium">Interactive Bubble Chart Mockup</span>
                <div className="absolute right-2 top-2 flex flex-col gap-1">
                  <button className="w-8 h-8 bg-panel border border-border rounded flex items-center justify-center text-muted hover:text-text-heading">⛶</button>
                  <button className="w-8 h-8 bg-panel border border-border rounded flex items-center justify-center text-muted hover:text-text-heading">↓</button>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Keywords Table */}
            <div className="bg-panel border border-border rounded-xl flex flex-col overflow-hidden">
              <div className="p-5 border-b border-border">
                <h3 className="text-lg font-bold text-text-heading flex items-center gap-2">
                  Top Keywords by Theme
                  <div className="w-4 h-4 rounded-full border border-border flex items-center justify-center text-muted text-[10px] cursor-help">i</div>
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-border bg-panel-soft/50 text-xs text-muted font-semibold">
                      <th className="px-5 py-3">Theme</th>
                      <th className="px-5 py-3">Top Keywords</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { theme: 'Personal Support', color: '#bb9af7', keywords: 'support, help, advice, mental health, feel, anxiety, depression' },
                      { theme: 'Current Events', color: '#7aa2f7', keywords: 'election, government, policy, vote, biden, trump, politics' },
                      { theme: 'Civic Discourse', color: '#9ece6a', keywords: 'rights, justice, community, change, equality, activism, voices' },
                      { theme: 'Education', color: '#e0af68', keywords: 'study, learning, school, online, course, exam, tips' },
                      { theme: 'Emotional Topics', color: '#f7768e', keywords: 'anxiety, stress, tired, motivation, upset, overwhelmed, healing' },
                      { theme: 'News Discussion', color: '#2ac3de', keywords: 'breaking, update, reports, media, headlines, news, today' },
                    ].map((row, i) => (
                      <tr key={i} className="border-b border-border/50 hover:bg-panel-soft/30 transition-colors">
                        <td className="px-5 py-3 font-medium whitespace-nowrap">
                          <span className="flex items-center gap-2 text-text-heading">
                            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: row.color }}></span>
                            {row.theme}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-muted text-xs leading-relaxed">{row.keywords}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="p-3 flex justify-center border-t border-border mt-auto">
                <button className="text-sm text-primary font-medium hover:text-primary/80 transition-colors flex items-center gap-1">
                  View all themes and keywords →
                </button>
              </div>
            </div>

            {/* Communities by Theme Heatmap */}
            <div className="bg-panel border border-border rounded-xl flex flex-col overflow-hidden p-5">
              <h3 className="text-lg font-bold text-text-heading flex items-center gap-2 mb-4">
                Communities by Theme
                <div className="w-4 h-4 rounded-full border border-border flex items-center justify-center text-muted text-[10px] cursor-help">i</div>
              </h3>

              <div className="flex-1 w-full flex flex-col justify-center gap-1">
                {/* Heatmap header */}
                <div className="flex text-xs font-semibold text-muted mb-2">
                  <div className="w-24 shrink-0 pt-6">Top Communities</div>
                  <div className="flex-1 flex flex-col items-center">
                    <span className="mb-2">Themes</span>
                    <div className="flex w-full justify-between">
                      <div className="flex items-center gap-1 w-12 flex-col text-center"><span className="w-2 h-2 rounded-full bg-[#bb9af7]"></span><span className="text-[10px] truncate w-full">Personal Support</span></div>
                      <div className="flex items-center gap-1 w-12 flex-col text-center"><span className="w-2 h-2 rounded-full bg-[#7aa2f7]"></span><span className="text-[10px] truncate w-full">Current Events</span></div>
                      <div className="flex items-center gap-1 w-12 flex-col text-center"><span className="w-2 h-2 rounded-full bg-[#9ece6a]"></span><span className="text-[10px] truncate w-full">Civic Discourse</span></div>
                      <div className="flex items-center gap-1 w-12 flex-col text-center"><span className="w-2 h-2 rounded-full bg-[#e0af68]"></span><span className="text-[10px] truncate w-full">Education</span></div>
                      <div className="flex items-center gap-1 w-12 flex-col text-center"><span className="w-2 h-2 rounded-full bg-[#f7768e]"></span><span className="text-[10px] truncate w-full">Emotional Topics</span></div>
                      <div className="flex items-center gap-1 w-12 flex-col text-center"><span className="w-2 h-2 rounded-full bg-[#2ac3de]"></span><span className="text-[10px] truncate w-full">News Discussion</span></div>
                      <div className="flex items-center gap-1 w-12 flex-col text-center"><span className="w-2 h-2 rounded-full bg-[#a9b1d6]"></span><span className="text-[10px] truncate w-full">Other</span></div>
                    </div>
                  </div>
                </div>

                {/* Heatmap rows */}
                {[
                  { name: 'Telegram', icon: '✈', color: 'text-blue-400', vals: [28, 17, 14, 12, 9, 8, 12] },
                  { name: 'Twitter/X', icon: '𝕏', color: 'text-text-heading font-bold', vals: [22, 24, 15, 10, 8, 9, 12] },
                  { name: 'Reddit', icon: '⚇', color: 'text-orange-500', vals: [20, 16, 18, 14, 10, 7, 15] },
                  { name: 'Facebook', icon: 'f', color: 'text-blue-600 font-bold', vals: [18, 14, 13, 16, 11, 6, 22] },
                  { name: 'Discord', icon: '👾', color: 'text-indigo-500', vals: [24, 12, 11, 10, 8, 7, 28] }
                ].map((row, i) => (
                  <div key={i} className="flex text-xs h-8 items-center border-b border-border/30 last:border-0">
                    <div className="w-24 shrink-0 flex items-center gap-1.5 text-text-heading font-medium">
                      <span className={row.color}>{row.icon}</span> {row.name}
                    </div>
                    <div className="flex-1 flex justify-between gap-1 h-full">
                      {row.vals.map((v, j) => (
                        <div key={j} className="flex-1 h-full flex items-center justify-center font-medium" style={{ backgroundColor: `rgba(99, 102, 241, ${v/100})`, color: v > 15 ? 'white' : 'inherit' }}>
                          {v}%
                        </div>
                      ))}
                    </div>
                  </div>
                ))}

                {/* Heatmap legend */}
                <div className="flex items-center gap-4 mt-6">
                  <span className="text-xs text-muted w-24">% of Conversations</span>
                  <div className="flex-1 h-2 rounded-full bg-gradient-to-r from-panel-soft to-primary"></div>
                  <div className="flex justify-between w-full absolute mt-6 text-[10px] text-muted">
                     <span className="ml-32">0%</span>
                     <span>30%+</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="flex flex-col gap-6">
          <div className="bg-panel border border-border rounded-xl p-6">
            <h3 className="text-lg font-bold text-text-heading mb-4 flex items-center gap-2">
              <span className="text-primary">💡</span> Theme Insights
            </h3>

            <div className="flex flex-col gap-6">
              <div className="flex gap-4">
                <div className="w-8 h-8 rounded-full bg-blue-500/20 text-blue-500 flex items-center justify-center shrink-0">📈</div>
                <div>
                  <p className="text-sm font-bold text-text-heading mb-1">Personal Support Leads</p>
                  <p className="text-xs text-muted leading-relaxed">Personal Support remains the top theme, with a 2.3pp increase in share compared to last month.</p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="w-8 h-8 rounded-full bg-purple-500/20 text-purple-500 flex items-center justify-center shrink-0">📊</div>
                <div>
                  <p className="text-sm font-bold text-text-heading mb-1">Current Events Spike</p>
                  <p className="text-xs text-muted leading-relaxed">Conversations around Current Events grew 18.7% month-over-month, driven by election discussions.</p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="w-8 h-8 rounded-full bg-green-500/20 text-green-500 flex items-center justify-center shrink-0">⭐</div>
                <div>
                  <p className="text-sm font-bold text-text-heading mb-1">Emerging Interest: Mental Health</p>
                  <p className="text-xs text-muted leading-relaxed">Topics like mental health and wellness are emerging across multiple communities.</p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="w-8 h-8 rounded-full bg-orange-500/20 text-orange-500 flex items-center justify-center shrink-0">👥</div>
                <div>
                  <p className="text-sm font-bold text-text-heading mb-1">Diversified Engagement</p>
                  <p className="text-xs text-muted leading-relaxed">Communities show broad engagement across themes, with no single-theme dominance.</p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-panel border border-border rounded-xl p-6">
            <h3 className="text-lg font-bold text-text-heading mb-4 flex items-center gap-2">
              <span className="text-muted">⚙</span> Methodology
            </h3>

            <div className="flex flex-col gap-4 text-sm">
              <div>
                <p className="font-semibold text-text-heading mb-1">Theme Detection</p>
                <p className="text-xs text-muted leading-relaxed">NLP-powered topic modeling (LDA) with dynamic clustering.</p>
              </div>
              <div>
                <p className="font-semibold text-text-heading mb-1">Topic Granularity</p>
                <p className="text-xs text-muted leading-relaxed">Topic-level analysis for detailed insights into conversation themes.</p>
              </div>
              <div>
                <p className="font-semibold text-text-heading mb-1">Update Frequency</p>
                <p className="text-xs text-muted leading-relaxed">Themes and topics are updated daily based on new conversations.</p>
              </div>
            </div>

            <button className="mt-6 text-sm text-primary font-medium hover:text-primary/80 transition-colors flex items-center gap-1">
              View full methodology →
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
