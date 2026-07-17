import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export default function EvolutionChart({ data, title }) {
  // Use mock data matching the mockup if real data isn't structured appropriately yet
  const chartData = [
    { name: 'May 1', total: 500, twitter: 300, telegram: 200 },
    { name: 'May 6', total: 1100, twitter: 700, telegram: 400 },
    { name: 'May 11', total: 1000, twitter: 600, telegram: 400 },
    { name: 'May 16', total: 1500, twitter: 900, telegram: 600 },
    { name: 'May 21', total: 1400, twitter: 800, telegram: 600 },
    { name: 'May 26', total: 1200, twitter: 700, telegram: 500 },
    { name: 'May 31', total: 1248, twitter: 742, telegram: 506 },
  ];

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-panel border border-border p-3 rounded-lg shadow-xl text-sm z-50">
          <p className="font-bold mb-2 text-text-heading">{label}</p>
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

  return (
    <div className="bg-panel border border-border rounded-xl p-5 flex flex-col h-full">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-sm font-bold text-text-heading flex items-center gap-2">
          {title || "Evolution Over Time"}
          <div className="w-4 h-4 rounded-full border border-border flex items-center justify-center text-muted text-[10px] cursor-help">
            i
          </div>
        </h3>
        <select className="bg-transparent border border-border rounded-lg text-xs text-text-heading font-medium focus:outline-none cursor-pointer py-1 px-2">
          <option>Day</option>
          <option>Week</option>
          <option>Month</option>
        </select>
      </div>

      <div className="flex-grow w-full min-h-[250px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{ top: 5, right: 10, left: -20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
            <XAxis dataKey="name" stroke="var(--color-muted)" fontSize={11} tickLine={false} axisLine={false} />
            <YAxis stroke="var(--color-muted)" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(val) => val >= 1000000 ? `${(val/1000000).toFixed(1)}M` : val >= 1000 ? `${(val/1000).toFixed(1)}K` : val} />
            <Tooltip content={<CustomTooltip />} />
            <Legend iconType="circle" wrapperStyle={{ fontSize: '11px', color: 'var(--color-muted)', top: -10 }} verticalAlign="top" align="left" />
            <Line type="monotone" dataKey="total" name="Total (Both)" stroke="var(--color-primary)" strokeWidth={2} dot={false} activeDot={{ r: 5 }} />
            <Line type="monotone" dataKey="twitter" name="Twitter/X" stroke="#38bdf8" strokeWidth={2} dot={false} activeDot={{ r: 5 }} />
            <Line type="monotone" dataKey="telegram" name="Telegram" stroke="var(--color-secondary)" strokeWidth={2} dot={false} activeDot={{ r: 5 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
