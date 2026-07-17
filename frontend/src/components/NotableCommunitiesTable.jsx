import { MoreHorizontal } from 'lucide-react';

export default function NotableCommunitiesTable() {
  const data = [
    { rank: 1, id: 'C-1124', theme: 'Personal Support', themeColor: '#bb9af7', platform: 'Telegram', size: 1892, messages: 320154, persistence: 0.82, trend: 15.3, avgDegree: 13.4, topLinked: 'Current Events (C-0789)', linkStrength: 0.74, starred: true },
    { rank: 2, id: 'C-0789', theme: 'Current Events', themeColor: '#7aa2f7', platform: 'Twitter/X', size: 2145, messages: 410982, persistence: 0.63, trend: 8.7, avgDegree: 14.1, topLinked: 'Personal Support (C-1124)', linkStrength: 0.74, starred: false },
    { rank: 3, id: 'C-0561', theme: 'Civic Discourse', themeColor: '#9ece6a', platform: 'Telegram', size: 1768, messages: 210443, persistence: 0.74, trend: 12.1, avgDegree: 11.8, topLinked: 'Education (C-0098)', linkStrength: 0.58, starred: false },
    { rank: 4, id: 'C-0312', theme: 'News Discussion', themeColor: '#e0af68', platform: 'Twitter/X', size: 1216, messages: 198765, persistence: 0.58, trend: -3.6, avgDegree: 10.6, topLinked: 'Current Events (C-0789)', linkStrength: 0.62, starred: false },
    { rank: 5, id: 'C-0098', theme: 'Education', themeColor: '#2ac3de', platform: 'Telegram', size: 1642, messages: 156332, persistence: 0.69, trend: 5.4, avgDegree: 11.2, topLinked: 'Civic Discourse (C-0561)', linkStrength: 0.58, starred: false },
    { rank: 6, id: 'C-1433', theme: 'Emotional Topics', themeColor: '#f7768e', platform: 'Twitter/X', size: 1431, messages: 142781, persistence: 0.61, trend: 2.8, avgDegree: 9.9, topLinked: 'Personal Support (C-1124)', linkStrength: 0.49, starred: false },
  ];

  return (
    <div className="bg-panel border border-border rounded-xl flex flex-col overflow-hidden">
      <div className="flex items-center justify-between p-5 border-b border-border">
        <h2 className="text-lg font-bold text-text-heading flex items-center gap-2">
          Notable Communities
          <div className="w-4 h-4 rounded-full border border-border flex items-center justify-center text-muted text-[10px] cursor-help">
            i
          </div>
        </h2>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[1200px]">
          <thead>
            <tr className="border-b border-border bg-panel-soft/50 text-xs text-muted font-semibold">
              <th className="px-5 py-3 font-medium">Rank</th>
              <th className="px-5 py-3 font-medium">Community ID</th>
              <th className="px-5 py-3 font-medium">Theme</th>
              <th className="px-5 py-3 font-medium">Primary Platform</th>
              <th className="px-5 py-3 font-medium">Size (Nodes)</th>
              <th className="px-5 py-3 font-medium">Messages (May)</th>
              <th className="px-5 py-3 font-medium">Persistence (WIF)</th>
              <th className="px-5 py-3 font-medium">Trend (vs Apr)</th>
              <th className="px-5 py-3 font-medium">Avg Degree</th>
              <th className="px-5 py-3 font-medium">Top Linked Community</th>
              <th className="px-5 py-3 font-medium">Link Strength</th>
            </tr>
          </thead>
          <tbody className="text-sm">
            {data.map((row, i) => {
              const isPositive = row.trend > 0;
              return (
                <tr key={i} className="border-b border-border/50 hover:bg-panel-soft/30 transition-colors">
                  <td className="px-5 py-3 font-medium flex items-center gap-2 text-muted">
                    {row.rank}
                    <span className={row.starred ? "text-warning" : "text-muted/30"}>
                      {row.starred ? "★" : "☆"}
                    </span>
                  </td>
                  <td className="px-5 py-3 font-medium text-text-heading">
                    {row.id}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2 text-muted">
                      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: row.themeColor }}></span>
                      <span className="text-text-heading">{row.theme}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3 text-muted">
                    <div className="flex items-center gap-1.5">
                      {row.platform === 'Twitter/X' ? (
                        <span className="font-bold text-text-heading">𝕏</span>
                      ) : (
                        <span className="text-primary text-base">✈</span>
                      )}
                      <span className="text-text-heading">{row.platform}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3 text-muted">{row.size.toLocaleString()}</td>
                  <td className="px-5 py-3 text-muted">{row.messages.toLocaleString()}</td>
                  <td className="px-5 py-3 text-muted">{row.persistence}</td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <span className={`flex items-center gap-1 font-medium ${isPositive ? 'text-success' : 'text-danger'} w-14`}>
                        {isPositive ? '↑' : '↓'} {Math.abs(row.trend)}%
                      </span>
                      <svg width="30" height="15" viewBox="0 0 40 15" className="opacity-80">
                        {isPositive ? (
                          <path d="M0 12 Q 5 12, 10 8 T 20 8 T 30 2 T 40 0" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-success" />
                        ) : (
                          <path d="M0 2 Q 5 2, 10 6 T 20 6 T 30 12 T 40 15" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-danger" />
                        )}
                      </svg>
                    </div>
                  </td>
                  <td className="px-5 py-3 text-muted">{row.avgDegree}</td>
                  <td className="px-5 py-3 text-muted">{row.topLinked}</td>
                  <td className="px-5 py-3 text-text-heading font-medium">{row.linkStrength}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <div className="p-3 flex justify-center mt-2 border-t border-border">
        <button className="text-sm text-primary font-medium hover:text-primary/80 transition-colors flex items-center gap-1">
          View all communities <span className="text-xs">↓</span>
        </button>
      </div>
    </div>
  );
}
