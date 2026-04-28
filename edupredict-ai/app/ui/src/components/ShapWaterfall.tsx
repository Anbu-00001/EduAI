import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, ReferenceLine,
  Cell, LabelList, ResponsiveContainer, Tooltip,
} from 'recharts'
import { titleCase } from '@/lib/utils'

interface ShapWaterfallProps {
  contributions: Record<string, number>
}

export default function ShapWaterfall({ contributions }: ShapWaterfallProps) {
  const sorted = Object.entries(contributions)
    .map(([name, value]) => ({ name: titleCase(name.replace(/_normalized$/, '')), value }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, 10)

  return (
    <div>
      <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-4">
        Why This Score? (SHAP Explainability)
      </p>
      <div
        className="w-full"
        aria-label="SHAP feature contribution chart showing the top 10 factors impacting repayment probability"
        role="img"
      >
        <ResponsiveContainer width="100%" height={300}>
          <BarChart
            data={sorted}
            layout="vertical"
            margin={{ top: 4, right: 64, left: 8, bottom: 4 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
            <XAxis
              type="number"
              tickFormatter={v => `${(v * 100).toFixed(0)}%`}
              tick={{ fontSize: 10, fill: '#64748b' }}
              label={{ value: 'SHAP value (impact on repayment probability)', position: 'insideBottom', offset: -4, fontSize: 9, fill: '#475569' }}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={130}
              tick={{ fontSize: 10, fill: '#94a3b8' }}
            />
            <Tooltip
              formatter={(v: number) => [`${(v * 100).toFixed(2)}%`, 'Impact']}
              contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8 }}
              labelStyle={{ color: '#94a3b8', fontSize: 11 }}
            />
            <ReferenceLine x={0} stroke="#475569" strokeWidth={1} />
            <Bar dataKey="value" radius={[0, 4, 4, 0]} isAnimationActive>
              {sorted.map((entry, i) => (
                <Cell key={i} fill={entry.value > 0 ? '#10b981' : '#f43f5e'} />
              ))}
              <LabelList
                dataKey="value"
                position="right"
                formatter={(v: number) => `${v > 0 ? '+' : ''}${(v * 100).toFixed(1)}%`}
                style={{ fontSize: 9, fill: '#94a3b8' }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
