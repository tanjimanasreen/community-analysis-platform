import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function PlatformComparison({ data }) {
  // Use mock data matching the mockup
  const chartData = [
    { name: 'Message Volume\n(in millions)', twitter: 4.91, telegram: 3.76 },
    { name: 'Persistence Score\n(WIF)', twitter: 0.55, telegram: 0.76 },
    { name: 'Thematic Diversity\n(Topics per Community)', twitter: 6.2, telegram: 4.1 },
  ];

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-panel border border-border p-3 rounded-lg shadow-xl text-sm">
          <p className="font-bold mb-2 text-text-heading">{label.split('\n')[0]}</p>
          {payload.map((entry, index) => (
            <p key={`item-${index}`} style={{ color: entry.color }} className="flex justify-between gap-4 font-medium">
              <span>{entry.name}:</span>
              <span>{entry.value}</span>
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const CustomTick = ({ x, y, payload }) => {
    const lines = payload.value.split('\n');
    return (
      <g transform={`translate(${x},${y})`}>
        <text x={0} y={0} dy={16} textAnchor="middle" fill="var(--color-muted)" fontSize={11}>
          <tspan x="0" dy="0">{lines[0]}</tspan>
          {lines[1] && <tspan x="0" dy="14">{lines[1]}</tspan>}
        </text>
      </g>
    );
  };

  return (
    <div className="bg-panel border border-border rounded-xl p-5 flex flex-col h-full">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-sm font-bold text-text-heading flex items-center gap-2">
          Platform Comparison
          <div className="w-4 h-4 rounded-full border border-border flex items-center justify-center text-muted text-[10px] cursor-help">
            i
          </div>
        </h3>
      </div>
      
      <div className="flex-grow w-full min-h-[200px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ top: 20, right: 10, left: -20, bottom: 20 }}
            barGap={8}
            barSize={24}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
            <XAxis dataKey="name" stroke="var(--color-muted)" tickLine={false} axisLine={false} tick={<CustomTick />} height={50} />
            <YAxis stroke="var(--color-muted)" fontSize={11} tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'var(--color-panel-soft)' }} />
            <Legend iconType="square" wrapperStyle={{ top: -10, left: 0, fontSize: '12px', color: 'var(--color-muted)' }} verticalAlign="top" align="left" />
            <Bar dataKey="twitter" name="Twitter/X" fill="var(--color-primary)" radius={[4, 4, 0, 0]} />
            <Bar dataKey="telegram" name="Telegram" fill="var(--color-secondary)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
