export default function TransitionsSankey() {
  // Mock data for the transitions to look like the mockup
  const themes = [
    { name: 'Current Events', color: '#7aa2f7' },
    { name: 'Personal Support', color: '#bb9af7' },
    { name: 'Civic Discourse', color: '#9ece6a' },
    { name: 'Education', color: '#e0af68' },
    { name: 'Emotional Topics', color: '#f7768e' },
    { name: 'News Discussion', color: '#ff9e64' },
    { name: 'Other', color: '#a9b1d6' },
  ];

  const months = ['Feb \'24', 'Mar \'24', 'Apr \'24', 'May \'24'];

  return (
    <div className="bg-panel border border-border rounded-xl p-5 flex flex-col h-full overflow-hidden">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-sm font-bold text-text-heading flex items-center gap-2">
          Community Transitions (Member Overlap)
          <div className="w-4 h-4 rounded-full border border-border flex items-center justify-center text-muted text-[10px] cursor-help">
            i
          </div>
        </h3>
      </div>

      <div className="flex-grow w-full relative min-h-[220px] flex">
        {/* Y Axis Labels */}
        <div className="flex flex-col justify-between py-8 pr-2 w-32 shrink-0">
          {themes.map((theme, i) => (
            <div key={i} className="text-xs font-medium" style={{ color: theme.color }}>
              {theme.name}
            </div>
          ))}
        </div>

        {/* Chart Area */}
        <div className="flex-grow relative border-l border-border/30">
          {/* X Axis Labels */}
          <div className="absolute top-0 left-0 w-full flex justify-between px-8 text-xs font-medium text-text-heading">
            {months.map(m => <span key={m}>{m}</span>)}
          </div>

          {/* SVG Ribbons Mockup */}
          <svg className="absolute top-8 left-0 w-full h-[calc(100%-2rem)]" preserveAspectRatio="none" viewBox="0 0 1000 300">
            {/* Ribbons */}
            <path d="M 100 20 C 300 20, 300 100, 500 100 C 700 100, 700 20, 900 20" fill="none" stroke="#7aa2f7" strokeWidth="15" strokeOpacity="0.4" />
            <path d="M 100 60 C 300 60, 300 20, 500 20 C 700 20, 700 140, 900 140" fill="none" stroke="#bb9af7" strokeWidth="12" strokeOpacity="0.4" />
            <path d="M 100 100 C 300 100, 300 60, 500 60 C 700 60, 700 60, 900 60" fill="none" stroke="#9ece6a" strokeWidth="10" strokeOpacity="0.4" />
            <path d="M 100 140 C 300 140, 300 220, 500 220 C 700 220, 700 100, 900 100" fill="none" stroke="#e0af68" strokeWidth="18" strokeOpacity="0.4" />
            <path d="M 100 180 C 300 180, 300 180, 500 180 C 700 180, 700 180, 900 180" fill="none" stroke="#f7768e" strokeWidth="14" strokeOpacity="0.4" />
            <path d="M 100 220 C 300 220, 300 140, 500 140 C 700 140, 700 260, 900 260" fill="none" stroke="#ff9e64" strokeWidth="8" strokeOpacity="0.4" />
            <path d="M 100 260 C 300 260, 300 260, 500 260 C 700 260, 700 220, 900 220" fill="none" stroke="#a9b1d6" strokeWidth="12" strokeOpacity="0.4" />

            {/* Bars at columns */}
            {[100, 500, 900].map(x => (
              <g key={x}>
                <rect x={x-6} y={12} width={12} height={15} fill="#7aa2f7" />
                <rect x={x-6} y={54} width={12} height={12} fill="#bb9af7" />
                <rect x={x-6} y={95} width={12} height={10} fill="#9ece6a" />
                <rect x={x-6} y={131} width={12} height={18} fill="#e0af68" />
                <rect x={x-6} y={173} width={12} height={14} fill="#f7768e" />
                <rect x={x-6} y={216} width={12} height={8} fill="#ff9e64" />
                <rect x={x-6} y={254} width={12} height={12} fill="#a9b1d6" />
              </g>
            ))}
          </svg>

          {/* X Axis Line */}
          <div className="absolute bottom-0 left-8 right-8 border-t border-border flex items-center mt-2 pt-2 text-xs text-muted">
            <span className="mx-auto">% of Members Retained</span>
            <span className="text-right">→</span >
          </div>
        </div>

        {/* Right Percentages */}
        <div className="flex flex-col justify-between py-8 pl-4 w-12 shrink-0 border-l border-border/30">
          <div className="text-xs font-medium text-muted">22%</div>
          <div className="text-xs font-medium text-muted">18%</div>
          <div className="text-xs font-medium text-muted">16%</div>
          <div className="text-xs font-medium text-muted">13%</div>
          <div className="text-xs font-medium text-muted">11%</div>
          <div className="text-xs font-medium text-muted">9%</div>
          <div className="text-xs font-medium text-muted">11%</div>
        </div>
      </div>
    </div>
  );
}
