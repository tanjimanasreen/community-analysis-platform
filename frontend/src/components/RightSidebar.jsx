import { Target, Lightbulb, Activity, CheckCircle2 } from 'lucide-react';

function InsightItem({ title, description, icon: Icon, colorClass, bgClass }) {
  return (
    <div className="flex gap-4">
      <div className={`mt-1 flex-shrink-0 w-8 h-8 rounded-full ${bgClass} bg-opacity-20 flex items-center justify-center`}>
        <Icon size={16} className={colorClass} />
      </div>
      <div>
        <h4 className="text-sm font-bold text-text-heading mb-1">{title}</h4>
        <p className="text-xs text-muted leading-relaxed">{description}</p>
      </div>
    </div>
  );
}

export default function RightSidebar({ summary }) {
  return (
    <aside className="w-80 flex-shrink-0 flex flex-col gap-6">
      <div className="bg-panel border border-border rounded-xl p-5">
        <h3 className="text-sm font-bold text-text-heading flex items-center gap-2 mb-6 uppercase tracking-wider">
          <Lightbulb size={16} className="text-accent" />
          Key Insights
        </h3>

        <div className="flex flex-col gap-6">
          <InsightItem
            title="Higher Persistence on Telegram"
            description="Telegram communities show significantly higher persistence scores compared to Twitter/X."
            icon={Activity}
            colorClass="text-secondary"
            bgClass="bg-secondary"
          />
          <InsightItem
            title="Stronger Topic Consistency on Twitter/X"
            description="Twitter/X communities exhibit greater thematic consistency across time."
            icon={Target}
            colorClass="text-primary"
            bgClass="bg-primary"
          />
          <InsightItem
            title="WIF and IF are Comparable"
            description="Both affinity metrics produce comparable community structures with high overlap."
            icon={CheckCircle2}
            colorClass="text-success"
            bgClass="bg-success"
          />
          <InsightItem
            title="Growth in Support Communities"
            description="Personal Support and Emotional Topics communities have grown steadily over the past 3 months."
            icon={Users => <span className="text-lg">👥</span>} // Quick mockup icon
            colorClass="text-warning"
            bgClass="bg-warning"
          />
        </div>
      </div>

      <div className="bg-panel border border-border rounded-xl p-5 flex-grow">
        <h3 className="text-sm font-bold text-text-heading mb-4 uppercase tracking-wider">Data Summary</h3>

        <div className="flex flex-col gap-3 text-sm">
          <div className="flex justify-between py-2 border-b border-border/50">
            <span className="text-muted">Time Range</span>
            <span className="font-medium text-text-heading">May 1 – May 31, 2024</span>
          </div>
          <div className="flex justify-between py-2 border-b border-border/50">
            <span className="text-muted">Platforms</span>
            <span className="font-medium text-text-heading">Both (Twitter/X, Telegram)</span>
          </div>
          <div className="flex justify-between py-2 border-b border-border/50">
            <span className="text-muted">Affinity Metric</span>
            <span className="font-medium text-text-heading">WIF</span>
          </div>
          <div className="flex justify-between py-2 border-b border-border/50">
            <span className="text-muted">Min Community Size</span>
            <span className="font-medium text-text-heading">50</span>
          </div>
          <div className="flex justify-between py-2 border-b border-border/50">
            <span className="text-muted">Total Messages</span>
            <span className="font-medium text-text-heading">8.67M</span>
          </div>
          <div className="flex justify-between py-2 mt-2">
            <span className="text-muted">Data Source Status</span>
            <span className="font-medium text-success flex items-center gap-1.5">
              <CheckCircle2 size={14} />
              All Systems Operational
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
