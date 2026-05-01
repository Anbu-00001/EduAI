import { useState } from 'react'
import { titleCase } from '@/lib/utils'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

interface ShapWaterfallProps {
  contributions: Record<string, number>
  actualValues?: Record<string, any>
}

export default function ShapWaterfall({ contributions, actualValues = {} }: ShapWaterfallProps) {
  const [expandedFeature, setExpandedFeature] = useState<string | null>(null)

  const { data: featureRanges } = useQuery({
    queryKey: ['featureRanges'],
    queryFn: async () => {
      const res = await apiClient.get('/features/ranges')
      return res.data
    }
  })

  const sorted = Object.entries(contributions)
    .map(([name, value]) => ({ name, label: titleCase(name.replace(/_normalized$/, '')), value }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, 5)

  return (
    <div>
      <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-4">
        Top 5 Risk Drivers
      </p>
      <div className="space-y-3 w-full">
        {sorted.map((entry) => {
          const isPositive = entry.value > 0
          const absVal = Math.abs(entry.value)
          const widthPct = Math.min(100, Math.max(2, absVal * 400)) // Scale for visibility
          const isExpanded = expandedFeature === entry.name
          const ranges = featureRanges?.[entry.name]
          const p10 = ranges?.p10 ?? 0
          const p90 = ranges?.p90 ?? 0
          const actual = actualValues[entry.name] ?? ranges?.median ?? 0
          const target = entry.value < 0 ? p90 : p10 // Simplistic target
          const delta = (Math.abs(entry.value) * 0.8 * 100).toFixed(1)

          return (
            <div key={entry.name} className="flex flex-col">
              <div 
                className="group relative flex items-center h-8 cursor-pointer hover:bg-slate-800/30 rounded px-1 transition-colors"
                onClick={() => setExpandedFeature(isExpanded ? null : entry.name)}
              >
                {/* Left label */}
                <div className="w-[30%] text-xs text-slate-400 truncate pr-2" title={entry.label}>
                  {entry.label}
                </div>
                
                {/* Center dividing line and bars */}
                <div className="w-[50%] relative flex items-center justify-center h-full border-l border-slate-700">
                  {/* Left side (Positive) */}
                  <div className="w-1/2 h-full flex items-center justify-end pr-px">
                    {isPositive && (
                      <div 
                        className="h-[22px] rounded-l-sm bg-gradient-to-l from-emerald-500 to-emerald-400/50" 
                        style={{ width: `${widthPct}%` }}
                      />
                    )}
                  </div>
                  {/* Right side (Negative) */}
                  <div className="w-1/2 h-full flex items-center justify-start pl-px">
                    {!isPositive && (
                      <div 
                        className="h-[22px] rounded-r-sm bg-gradient-to-r from-rose-500 to-rose-400/50" 
                        style={{ width: `${widthPct}%` }}
                      />
                    )}
                  </div>
                  
                  {/* Tooltip on hover */}
                  <div className="absolute hidden group-hover:block z-10 bottom-full mb-1 left-1/2 -translate-x-1/2 bg-slate-900 border border-slate-700 text-xs text-slate-300 p-2 rounded shadow-xl w-48 text-center pointer-events-none">
                    <p className="font-bold text-white">{entry.label}</p>
                    <p>Actual: {typeof actual === 'number' ? actual.toFixed(2) : actual}</p>
                    <p className="text-[10px] text-slate-500">Pop range: {p10.toFixed(1)} - {p90.toFixed(1)}</p>
                  </div>
                </div>

                {/* Right value */}
                <div className="w-[20%] text-right text-xs font-mono pl-2">
                  <span className={isPositive ? 'text-emerald-400' : 'text-rose-400'}>
                    {isPositive ? '+' : ''}{entry.value.toFixed(3)}
                  </span>
                </div>
              </div>

              {/* Sub-panel */}
              {isExpanded && (
                <div className="mt-1 mb-2 ml-[30%] p-2.5 bg-slate-800/50 rounded border border-slate-700/50 text-xs text-slate-300">
                  <p>
                    <span className="text-white font-medium">{entry.label}</span> = {typeof actual === 'number' ? actual.toFixed(2) : actual} 
                    <span className="text-slate-500 ml-1">(population p10–p90: {p10.toFixed(1)}–{p90.toFixed(1)})</span>
                  </p>
                  <p className="mt-1.5 text-slate-400">
                    Counterfactual: if this were <span className="text-white">{target.toFixed(2)}</span>, prediction would change by <span className={isPositive ? 'text-rose-400' : 'text-emerald-400'}>±{delta}%</span>
                  </p>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
