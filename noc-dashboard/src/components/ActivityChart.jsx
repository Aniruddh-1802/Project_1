import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

const SERIES = [
  {
    key: 'total_activity',
    label: 'Total Activity',
    color: '#4D9EFF'
  },
  {
    key: 'internet_activity',
    label: 'Internet Activity',
    color: '#41D65A'
  },
  {
    key: 'sms_activity',
    label: 'SMS Activity',
    color: '#EAB308'
  },
  {
    key: 'call_activity',
    label: 'Call Activity',
    color: '#F97316'
  }
];

function formatTick(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  return isNaN(d) ? ts : `${d.getHours().toString().padStart(2, '0')}:00`;
}

export default function ActivityChart({ data, selectedSeries }) {
  if (!data || data.length === 0) {
    return <p style={{ color: 'var(--text-muted)', padding: '16px 0' }}>No activity data.</p>;
  }

  const visible = selectedSeries && selectedSeries.length > 0
    ? SERIES.filter(s => selectedSeries.includes(s.key))
    : SERIES;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
        <XAxis
          dataKey="timestamp"
          tickFormatter={formatTick}
          tick={{ fill: '#8b949e', fontSize: 11 }}
          axisLine={{ stroke: '#30363d' }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: '#8b949e', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={50}
        />
        <Tooltip
          contentStyle={{
            background: '#161b22',
            border: '1px solid #30363d',
            borderRadius: 6,
            fontSize: 12,
          }}
          labelFormatter={v => formatTick(v)}
        />
        <Legend
          wrapperStyle={{ fontSize: 12, color: '#8b949e', paddingTop: 8 }}
        />
        {visible.map(s => (
          <Line
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.label}
            stroke={s.color}
            dot={false}
            strokeWidth={1.5}
            activeDot={{ r: 4 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

export { SERIES };
