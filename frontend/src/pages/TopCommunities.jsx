import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { Network, Target, Users, Shield, Star, MoreHorizontal, X, ArrowRight, TrendingUp, TrendingDown, Send } from 'lucide-react';

export default function TopCommunitiesPage() {
  const { summary } = useOutletContext() || {};
  const [selectedCommunity, setSelectedCommunity] = useState('C-1124');

  const communities = [
    { rank: 1, id: 'C-1124', platform: 'Telegram', theme: 'Personal Support', color: 'bg-purple-500', size: '5,432', messages: '320,154', persistence: '0.82', trend: 15.3, diversity: '4.3' },
    { rank: 2, id: 'C-0789', platform: 'Twitter/X', theme: 'Current Events', color: 'bg-blue-500', size: '4,987', messages: '410,982', persistence: '0.63', trend: 8.7, diversity: '7.1' },
    { rank: 3, id: 'C-0561', platform: 'Telegram', theme: 'Civic Discourse', color: 'bg-green-500', size: '3,876', messages: '210,443', persistence: '0.74', trend: 12.1, diversity: '5.2' },
    { rank: 4, id: 'C-0312', platform: 'Twitter/X', theme: 'News Discussion', color: 'bg-orange-500', size: '3,112', messages: '198,765', persistence: '0.58', trend: -3.6, diversity: '6.8' },
    { rank: 5, id: 'C-0098', platform: 'Telegram', theme: 'Education', color: 'bg-teal-500', size: '2,945', messages: '156,332', persistence: '0.69', trend: 5.4, diversity: '4.6' },
    { rank: 6, id: 'C-0771', platform: 'Telegram', theme: 'Investment', color: 'bg-yellow-500', size: '2,781', messages: '142,876', persistence: '0.61', trend: 9.2, diversity: '6.1' },
    { rank: 7, id: 'C-0450', platform: 'Twitter/X', theme: 'Health & Wellness', color: 'bg-pink-500', size: '2,658', messages: '138,221', persistence: '0.66', trend: 3.1, diversity: '5.0' },
    { rank: 8, id: 'C-0622', platform: 'Telegram', theme: 'Technology', color: 'bg-blue-600', size: '2,431', messages: '123,887', persistence: '0.57', trend: 4.8, diversity: '6.3' },
    { rank: 9, id: 'C-0183', platform: 'Twitter/X', theme: 'Entertainment', color: 'bg-purple-600', size: '2,215', messages: '112,993', persistence: '0.53', trend: -1.7, diversity: '4.9' },
    { rank: 10, id: 'C-0867', platform: 'Telegram', theme: 'Religion & Spirituality', color: 'bg-amber-600', size: '2,102', messages: '108,614', persistence: '0.60', trend: 2.9, diversity: '5.6' },
    { rank: 11, id: 'C-0091', platform: 'Twitter/X', theme: 'Environmental', color: 'bg-green-600', size: '1,987', messages: '95,431', persistence: '0.64', trend: 6.2, diversity: '5.4' },
    { rank: 12, id: 'C-0333', platform: 'Telegram', theme: 'Gaming', color: 'bg-indigo-500', size: '1,865', messages: '89,776', persistence: '0.49', trend: -0.8, diversity: '4.2' },
    { rank: 13, id: 'C-0714', platform: 'Telegram', theme: 'Science', color: 'bg-blue-400', size: '1,742', messages: '78,992', persistence: '0.56', trend: 1.3, diversity: '4.8' },
    { rank: 14, id: 'C-0412', platform: 'Twitter/X', theme: 'Politics', color: 'bg-red-600', size: '1,598', messages: '74,511', persistence: '0.48', trend: -2.5, diversity: '6.7' },
    { rank: 15, id: 'C-0221', platform: 'Telegram', theme: 'Local Communities', color: 'bg-green-400', size: '1,476', messages: '63,245', persistence: '0.55', trend: 0.6, diversity: '4.1' }
  ];

  return (
    <div className="flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center shadow-sm">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-500">
              <Network size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted flex items-center gap-1">
                Tracked Communities
                <span className="w-3.5 h-3.5 rounded-full border border-muted flex items-center justify-center text-[8px] cursor-help">i</span>
              </p>
              <h3 className="text-2xl font-bold text-text-heading">1,248</h3>
            </div>
          </div>
          <p className="text-xs text-success font-medium flex items-center gap-1">↑ 12.4% <span className="text-muted font-normal">vs Apr 1 - Apr 30</span></p>
        </div>

        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center shadow-sm">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-500">
              <Target size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted flex items-center gap-1">
                Fastest Growing
                <span className="w-3.5 h-3.5 rounded-full border border-muted flex items-center justify-center text-[8px] cursor-help">i</span>
              </p>
              <h3 className="text-2xl font-bold text-text-heading">15.3%</h3>
            </div>
          </div>
          <p className="text-xs text-success font-medium flex items-center gap-1">↑ Growth <span className="text-muted font-normal">(vs Apr 1 - Apr 30)</span></p>
        </div>

        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center shadow-sm">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center text-green-500">
              <Users size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted flex items-center gap-1">
                Highest Persistence
                <span className="w-3.5 h-3.5 rounded-full border border-muted flex items-center justify-center text-[8px] cursor-help">i</span>
              </p>
              <h3 className="text-2xl font-bold text-text-heading">0.82</h3>
            </div>
          </div>
          <p className="text-xs text-success font-medium flex items-center gap-1">↑ 6.1% <span className="text-muted font-normal">vs Apr 1 - Apr 30</span></p>
        </div>

        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center shadow-sm">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-orange-500/10 flex items-center justify-center text-orange-500">
              <Shield size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted flex items-center gap-1">
                Highest Message Volume
                <span className="w-3.5 h-3.5 rounded-full border border-muted flex items-center justify-center text-[8px] cursor-help">i</span>
              </p>
              <h3 className="text-2xl font-bold text-text-heading">6.87M</h3>
            </div>
          </div>
          <p className="text-xs text-success font-medium flex items-center gap-1">↑ 18.7% <span className="text-muted font-normal">vs Apr 1 - Apr 30</span></p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">

        {/* Main Data Table */}
        <div className="xl:col-span-3 bg-panel border border-border rounded-xl flex flex-col overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs whitespace-nowrap">
              <thead>
                <tr className="border-b border-border text-muted font-bold">
                  <th className="py-4 px-4 font-semibold text-center w-12">Rank ↕</th>
                  <th className="py-4 px-4 font-semibold">Community ID ↕</th>
                  <th className="py-4 px-4 font-semibold">Platform</th>
                  <th className="py-4 px-4 font-semibold">Dominant Theme</th>
                  <th className="py-4 px-4 font-semibold">Size ↕</th>
                  <th className="py-4 px-4 font-semibold">Messages (May) ↕</th>
                  <th className="py-4 px-4 font-semibold">Persistence (WIF) ↕</th>
                  <th className="py-4 px-4 font-semibold">Trend (vs Apr) ↕</th>
                  <th className="py-4 px-4 font-semibold">Thematic Diversity</th>
                  <th className="py-4 px-4"></th>
                </tr>
              </thead>
              <tbody className="text-text font-medium">
                {communities.map((community, index) => (
                  <tr
                    key={community.id}
                    className={`border-b border-border/30 hover:bg-panel-soft transition-colors cursor-pointer ${selectedCommunity === community.id ? 'bg-primary/5' : ''}`}
                    onClick={() => setSelectedCommunity(community.id)}
                  >
                    <td className="py-3 px-4 flex items-center justify-center gap-1 text-muted">
                      {community.rank}
                      {index === 0 && <Star size={14} className="text-orange-400 fill-orange-400" />}
                      {index > 0 && index < 3 && <Star size={14} className="text-muted" />}
                    </td>
                    <td className="py-3 px-4 text-text-heading">{community.id}</td>
                    <td className="py-3 px-4 text-muted flex items-center gap-1.5">
                      {community.platform === 'Telegram' ? <Send size={12} className="text-blue-500" /> : <span className="font-serif italic font-bold">𝕏</span>}
                      {community.platform}
                    </td>
                    <td className="py-3 px-4 text-text-heading flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${community.color}`}></div>
                      {community.theme}
                    </td>
                    <td className="py-3 px-4 text-muted">{community.size}</td>
                    <td className="py-3 px-4 text-muted">{community.messages}</td>
                    <td className="py-3 px-4 text-muted">{community.persistence}</td>
                    <td className="py-3 px-4 flex items-center gap-2">
                      <span className={community.trend > 0 ? 'text-success' : 'text-danger'}>
                        {community.trend > 0 ? '↑' : '↓'} {Math.abs(community.trend)}%
                      </span>
                      {/* Micro Sparkline */}
                      <svg width="40" height="15" viewBox="0 0 40 15" className="overflow-visible ml-1">
                        {community.trend > 0 ? (
                          <path d="M 0 10 L 10 12 L 20 8 L 30 11 L 40 2" stroke="#10b981" strokeWidth="1.5" fill="none" />
                        ) : (
                          <path d="M 0 2 L 10 5 L 20 4 L 30 10 L 40 12" stroke="#ef4444" strokeWidth="1.5" fill="none" />
                        )}
                      </svg>
                    </td>
                    <td className="py-3 px-4 text-muted">{community.diversity}</td>
                    <td className="py-3 px-4 text-muted text-right">
                      <button className="p-1 hover:bg-bg rounded transition-colors"><MoreHorizontal size={16} /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="p-4 border-t border-border flex items-center justify-between text-xs text-muted font-medium bg-panel/50">
            <span>Showing 1 to 15 of 1,248 communities</span>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1">
                <button className="w-6 h-6 flex items-center justify-center hover:bg-panel-soft rounded text-muted">←</button>
                <button className="w-6 h-6 flex items-center justify-center bg-primary/10 text-primary font-bold rounded">1</button>
                <button className="w-6 h-6 flex items-center justify-center hover:bg-panel-soft rounded">2</button>
                <button className="w-6 h-6 flex items-center justify-center hover:bg-panel-soft rounded">3</button>
                <button className="w-6 h-6 flex items-center justify-center hover:bg-panel-soft rounded">4</button>
                <button className="w-6 h-6 flex items-center justify-center hover:bg-panel-soft rounded">5</button>
                <span className="px-1">...</span>
                <button className="w-6 h-6 flex items-center justify-center hover:bg-panel-soft rounded">84</button>
                <button className="w-6 h-6 flex items-center justify-center hover:bg-panel-soft rounded text-text-heading">→</button>
              </div>
              <div className="flex items-center gap-2">
                Rows per page:
                <select className="bg-transparent border-none font-bold text-text-heading outline-none cursor-pointer">
                  <option>15</option>
                  <option>30</option>
                  <option>50</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Selected Community Side Panel */}
        <div className="xl:col-span-1 flex flex-col h-full">
          {selectedCommunity && (
            <div className="bg-panel border border-border rounded-xl flex flex-col shadow-sm sticky top-[100px]">

              {/* Header */}
              <div className="p-5 border-b border-border flex justify-between items-start">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-2.5 h-2.5 rounded-full bg-purple-500"></div>
                    <h2 className="text-xl font-bold text-text-heading">{selectedCommunity}</h2>
                    <span className="text-[10px] bg-bg border border-border px-1.5 py-0.5 rounded font-bold text-muted ml-2">Rank #1</span>
                  </div>
                  <div className="flex flex-col gap-1 mt-3 text-xs text-muted font-medium">
                    <div className="flex items-center gap-1.5">
                      <Send size={12} className="text-blue-500" /> Telegram
                    </div>
                    <div className="flex items-center gap-1.5 mt-1">
                      <div className="w-1.5 h-1.5 rounded-full bg-purple-500 ml-0.5"></div> Personal Support
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedCommunity(null)}
                  className="p-1 hover:bg-panel-soft rounded-lg text-muted transition-colors"
                >
                  <X size={16} />
                </button>
              </div>

              <div className="p-5 flex flex-col gap-6">
                {/* Overview Stats */}
                <div>
                  <h3 className="text-xs font-bold text-text-heading mb-3">Overview</h3>
                  <div className="grid grid-cols-2 gap-y-4 gap-x-2">
                    <div>
                      <p className="text-[10px] text-muted font-medium mb-1">Size</p>
                      <p className="text-sm font-bold text-text-heading">5,432</p>
                      <p className="text-[10px] text-success font-medium">↑ 8.6% <span className="text-muted font-normal">vs Apr 1 - Apr 30</span></p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted font-medium mb-1">Messages (May)</p>
                      <p className="text-sm font-bold text-text-heading">320,154</p>
                      <p className="text-[10px] text-success font-medium">↑ 15.3% <span className="text-muted font-normal">vs Apr 1 - Apr 30</span></p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted font-medium mb-1">Persistence (WIF)</p>
                      <p className="text-sm font-bold text-text-heading">0.82</p>
                      <p className="text-[10px] text-success font-medium">↑ 6.1% <span className="text-muted font-normal">vs Apr 1 - Apr 30</span></p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted font-medium mb-1">Thematic Diversity</p>
                      <p className="text-sm font-bold text-text-heading">4.3</p>
                      <p className="text-[10px] text-success font-medium">↑ 4.2% <span className="text-muted font-normal">vs Apr 1 - Apr 30</span></p>
                    </div>
                  </div>
                </div>

                {/* Trend Chart Mock */}
                <div>
                  <h3 className="text-xs font-bold text-text-heading mb-1">Trend (vs Apr)</h3>
                  <p className="text-[10px] text-success font-medium mb-2">↑ 15.3%</p>
                  <div className="h-20 w-full relative">
                    <svg viewBox="0 0 200 60" className="w-full h-full overflow-visible" preserveAspectRatio="none">
                      <path d="M 0 50 L 40 40 L 80 45 L 120 30 L 160 35 L 200 10" stroke="#3b82f6" strokeWidth="2" fill="none" />
                      <path d="M 0 50 L 40 40 L 80 45 L 120 30 L 160 35 L 200 10 L 200 60 L 0 60 Z" fill="rgba(59, 130, 246, 0.1)" stroke="none" />
                    </svg>
                    <div className="absolute bottom-[-15px] left-0 text-[9px] text-muted font-medium">Apr 1</div>
                    <div className="absolute bottom-[-15px] right-0 text-[9px] text-muted font-medium">May 31</div>
                  </div>
                </div>

                {/* Top Themes Progress Bars */}
                <div className="pt-4">
                  <h3 className="text-xs font-bold text-text-heading mb-3">Top Themes</h3>
                  <div className="flex flex-col gap-2.5">
                    <div className="flex items-center text-[10px]">
                      <div className="w-24 text-muted flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-purple-500"></div> Personal Support
                      </div>
                      <div className="flex-1 mx-2 h-1.5 bg-bg rounded-full overflow-hidden">
                        <div className="h-full bg-purple-500" style={{ width: '42%' }}></div>
                      </div>
                      <div className="w-8 text-right font-medium text-text-heading">42%</div>
                    </div>
                    <div className="flex items-center text-[10px]">
                      <div className="w-24 text-muted flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-blue-500"></div> Mental Health
                      </div>
                      <div className="flex-1 mx-2 h-1.5 bg-bg rounded-full overflow-hidden">
                        <div className="h-full bg-blue-500" style={{ width: '18%' }}></div>
                      </div>
                      <div className="w-8 text-right font-medium text-text-heading">18%</div>
                    </div>
                    <div className="flex items-center text-[10px]">
                      <div className="w-24 text-muted flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-500"></div> Relationships
                      </div>
                      <div className="flex-1 mx-2 h-1.5 bg-bg rounded-full overflow-hidden">
                        <div className="h-full bg-green-500" style={{ width: '14%' }}></div>
                      </div>
                      <div className="w-8 text-right font-medium text-text-heading">14%</div>
                    </div>
                    <div className="flex items-center text-[10px]">
                      <div className="w-24 text-muted flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-orange-400"></div> Wellness
                      </div>
                      <div className="flex-1 mx-2 h-1.5 bg-bg rounded-full overflow-hidden">
                        <div className="h-full bg-orange-400" style={{ width: '11%' }}></div>
                      </div>
                      <div className="w-8 text-right font-medium text-text-heading">11%</div>
                    </div>
                    <div className="flex items-center text-[10px]">
                      <div className="w-24 text-muted flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-blue-300"></div> Other
                      </div>
                      <div className="flex-1 mx-2 h-1.5 bg-bg rounded-full overflow-hidden">
                        <div className="h-full bg-blue-300" style={{ width: '15%' }}></div>
                      </div>
                      <div className="w-8 text-right font-medium text-text-heading">15%</div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="p-4 border-t border-border mt-auto">
                <button className="w-full flex items-center justify-center gap-2 bg-primary/5 hover:bg-primary/10 text-primary py-2 rounded-lg text-xs font-semibold transition-colors">
                  View Community Insights <ArrowRight size={14} />
                </button>
              </div>

            </div>
          )}
        </div>
      </div>
    </div>
  );
}
