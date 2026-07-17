import { MoreHorizontal } from 'lucide-react';

export default function DataTable({ communities }) {
  const records = communities?.records || [];

  // Use mock data if records are empty to match the mockup
  const data = records.length > 0 ? records.slice(0, 5) : [
    { id: 'C-1124', platform: 'Telegram', theme: 'Personal Support', themeColor: '#bb9af7', size: 5432, messages: 320154, persistence: 0.82, trend: 15.3, diversity: 4.3, starred: true },
    { id: 'C-0789', platform: 'Twitter/X', theme: 'Current Events', themeColor: '#7aa2f7', size: 4987, messages: 410982, persistence: 0.63, trend: 8.7, diversity: 7.1, starred: false },
    { id: 'C-0561', platform: 'Telegram', theme: 'Civic Discourse', themeColor: '#9ece6a', size: 3876, messages: 210443, persistence: 0.74, trend: 12.1, diversity: 5.2, starred: false },
    { id: 'C-0312', platform: 'Twitter/X', theme: 'News Discussion', themeColor: '#e0af68', size: 3112, messages: 198765, persistence: 0.58, trend: -3.6, diversity: 6.8, starred: false },
    { id: 'C-0098', platform: 'Telegram', theme: 'Education', themeColor: '#2ac3de', size: 2945, messages: 156332, persistence: 0.69, trend: 5.4, diversity: 4.6, starred: false },
  ];

  return (
    <div className="bg-panel border border-border rounded-xl flex flex-col overflow-hidden">
      <div className="flex items-center justify-between p-5 border-b border-border">
        <h2 className="text-lg font-bold text-text-heading flex items-center gap-2">
          Top Communities
          <div className="w-4 h-4 rounded-full border border-border flex items-center justify-center text-muted text-[10px] cursor-help">
            i
          </div>
        </h2>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-border bg-panel-soft/50 text-xs text-muted uppercase tracking-wider font-semibold">
              <th className="px-5 py-3 font-medium">Community ID</th>
              <th className="px-5 py-3 font-medium">Platform</th>
              <th className="px-5 py-3 font-medium">Dominant Theme</th>
              <th className="px-5 py-3 font-medium">Size</th>
              <th className="px-5 py-3 font-medium">Messages (May)</th>
              <th className="px-5 py-3 font-medium">Persistence (WIF)</th>
              <th className="px-5 py-3 font-medium">Trend (vs Apr)</th>
              <th className="px-5 py-3 font-medium">Thematic Diversity</th>
              <th className="px-5 py-3"></th>
            </tr>
          </thead>
          <tbody className="text-sm">
            {data.map((row, i) => {
              const isPositive = row.trend > 0;
              return (
                <tr key={i} className="border-b border-border/50 hover:bg-panel-soft/30 transition-colors">
                  <td className="px-5 py-3 font-medium flex items-center gap-2">
                    <span className={row.starred ? "text-warning" : "text-muted"}>
                      {row.starred ? "★" : "☆"}
                    </span>
                    {row.id || `C-${Math.floor(Math.random()*10000)}`}
                  </td>
                  <td className="px-5 py-3 text-muted">
                    <div className="flex items-center gap-1.5">
                      {row.platform === 'Twitter/X' ? (
                        <span className="font-bold">𝕏</span>
                      ) : (
                        <span className="text-primary text-base">✈</span>
                      )}
                      {row.platform || 'Telegram'}
                    </div>
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: row.themeColor || '#bb9af7' }}></span>
                      {row.theme || 'Unknown'}
                    </div>
                  </td>
                  <td className="px-5 py-3">{row.size?.toLocaleString() || '-'}</td>
                  <td className="px-5 py-3">{row.messages?.toLocaleString() || '-'}</td>
                  <td className="px-5 py-3">{row.persistence || '-'}</td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3">
                      <span className={`flex items-center gap-1 font-medium ${isPositive ? 'text-success' : 'text-danger'} w-16`}>
                        {isPositive ? '↑' : '↓'} {Math.abs(row.trend)}%
                      </span>
                      {/* Fake Sparkline */}
                      <svg width="40" height="15" viewBox="0 0 40 15" className="opacity-80">
                        {isPositive ? (
                          <path d="M0 12 Q 5 12, 10 8 T 20 8 T 30 2 T 40 0" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-success" />
                        ) : (
                          <path d="M0 2 Q 5 2, 10 6 T 20 6 T 30 12 T 40 15" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-danger" />
                        )}
                      </svg>
                    </div>
                  </td>
                  <td className="px-5 py-3">{row.diversity || '-'}</td>
                  <td className="px-5 py-3 text-muted text-right">
                    <button className="p-1 hover:bg-panel-soft rounded"><MoreHorizontal size={16} /></button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <div className="p-3 border-t border-border flex justify-end">
        <button className="text-sm text-primary font-medium hover:text-primary/80 transition-colors">
          View all communities →
        </button>
      </div>
    </div>
  );
}
