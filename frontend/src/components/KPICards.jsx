import { Users, MessageSquare, Maximize, Shield } from 'lucide-react';

function MetricCard({ title, value, trend, trendValue, icon: Icon, colorClass, bgClass }) {
  const isPositive = trend === 'up';

  return (
    <div className="bg-panel border border-border rounded-xl p-5 shadow-sm relative overflow-hidden group hover:border-border/80 transition-colors">
      <div className={`absolute top-0 right-0 w-24 h-24 ${bgClass} rounded-full blur-2xl opacity-20 -mr-8 -mt-8 group-hover:opacity-30 transition-opacity`}></div>

      <div className="flex justify-between items-start mb-4 relative z-10">
        <div className={`w-10 h-10 rounded-lg ${bgClass} bg-opacity-20 flex items-center justify-center`}>
          <Icon size={20} className={colorClass} />
        </div>
        <div className="w-5 h-5 rounded-full border border-border flex items-center justify-center text-muted text-xs cursor-help">
          i
        </div>
      </div>

      <div className="relative z-10">
        <h3 className="text-muted text-sm font-medium mb-1">{title}</h3>
        <div className="text-2xl font-bold text-text-heading mb-2">{value}</div>

        <div className="flex items-center gap-1.5 text-xs font-medium">
          {isPositive ? (
            <span className="text-success flex items-center gap-0.5">
              <svg width="10" height="10" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 10V2M6 2L2 6M6 2L10 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              {trendValue}
            </span>
          ) : (
            <span className="text-danger flex items-center gap-0.5">
              <svg width="10" height="10" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 2V10M6 10L10 6M6 10L2 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              {trendValue}
            </span>
          )}
          <span className="text-muted font-normal">vs Apr 1 - Apr 30</span>
        </div>
      </div>
    </div>
  );
}

export default function KPICards({ summary }) {
  const matchedSummary = summary?.matched_summary || {};
  const userMessageCounts = summary?.user_message_counts || {};
  const messages = userMessageCounts.messages || { absolute: 0 };
  const users = userMessageCounts.user || { absolute: 0 };

  // Format numbers nicely
  const formatNum = (num) => {
    if (!num) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(2) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toLocaleString();
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricCard
        title="Active Communities"
        value={(matchedSummary.total_absolute || 0).toLocaleString()}
        trend="up"
        trendValue="12.4%"
        icon={Users}
        colorClass="text-primary"
        bgClass="bg-primary"
      />
      <MetricCard
        title="Total Messages"
        value={formatNum(messages.absolute)}
        trend="up"
        trendValue="18.7%"
        icon={MessageSquare}
        colorClass="text-secondary"
        bgClass="bg-secondary"
      />
      <MetricCard
        title="Avg Community Size"
        value={Math.round((users.absolute || 0) / (matchedSummary.total_absolute || 1)).toLocaleString()}
        trend="up"
        trendValue="5.6%"
        icon={Users}
        colorClass="text-success"
        bgClass="bg-success"
      />
      <MetricCard
        title="Persistence Score (WIF)"
        value="0.68"
        trend="up"
        trendValue="6.1%"
        icon={Shield}
        colorClass="text-warning"
        bgClass="bg-warning"
      />
    </div>
  );
}
