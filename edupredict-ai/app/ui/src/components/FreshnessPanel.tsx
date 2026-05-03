import { useState } from 'react'
import { RefreshCw, Wifi, WifiOff, Clock } from 'lucide-react'
import { useFreshness } from '@/hooks/useFreshness'

const STATUS_STYLES = {
  fresh:    'bg-green-dim text-green-text border-green/30',
  stale:    'bg-amber-dim text-amber-text border-amber/30',
  critical: 'bg-rose-dim text-rose-text border-rose/30',
}

function ReliabilityBar({ score }: { score: number }) {
  const color = score > 0.7 ? 'bg-green' : score > 0.4 ? 'bg-amber' : 'bg-rose'
  return (
    <div className="h-1.5 rounded-full bg-card-2 overflow-hidden">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${score * 100}%` }} />
    </div>
  )
}

export default function FreshnessPanel() {
  const { data, isLoading, isError, refresh } = useFreshness()
  const [refreshDone, setRefreshDone] = useState(false)

  const handleRefresh = async () => {
    await refresh.mutateAsync()
    setRefreshDone(true)
    setTimeout(() => setRefreshDone(false), 10_000)
  }

  const status = data?.status ?? 'fresh'

  return (
    <div className="bg-card border border-border rounded-2xl p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {isError ? <WifiOff className="w-4 h-4 text-rose" /> : <Wifi className="w-4 h-4 text-green" />}
          <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Data Freshness</p>
        </div>
        <div className="flex items-center gap-2">
          {data && (
            <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded-full border ${STATUS_STYLES[status]}`}>
              {status}
            </span>
          )}
          <button
            onClick={handleRefresh}
            disabled={refresh.isPending}
            className="p-1.5 rounded-lg bg-card-2 hover:bg-border-2 transition-colors disabled:opacity-50"
            aria-label="Refresh data sources"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-400 ${refresh.isPending ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {refreshDone && (
        <p className="text-xs text-green-text mb-3 bg-green-dim px-3 py-2 rounded-lg">
          Refresh scheduled — data updates in ~5 minutes
        </p>
      )}

      {isLoading && (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-10 rounded-lg bg-card-2 animate-pulse" />
          ))}
        </div>
      )}

      {data && (
        <div className="space-y-3">
          {data.sources.map((src) => {
            const ageHours = data.cache_age_h
            return (
              <div key={src.name} className="flex items-center gap-3">
                <p className="font-mono text-[11px] text-slate-300 w-24 shrink-0">{src.name}</p>
                <div className="flex-1">
                  <ReliabilityBar score={src.reliability_score} />
                </div>
                <div className="flex items-center gap-1 text-slate-500">
                  <Clock className="w-3 h-3" />
                  <span className="text-[10px] font-mono">{ageHours.toFixed(1)}h</span>
                </div>
                <span className="text-[10px] text-slate-500 font-mono w-10 text-right">
                  {(src.reliability_score * 100).toFixed(0)}%
                </span>
              </div>
            )
          })}

          {/* Circuit Breakers Section */}
          <div className="pt-3 mt-3 border-t border-border">
            <p className="text-[9px] text-slate-500 uppercase font-bold tracking-widest mb-2">Circuit States (External APIs)</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(data.circuit_states || {}).map(([name, state]) => (
                <div key={name} className="flex items-center gap-2 px-2 py-1 bg-card-2 rounded-lg border border-border">
                  <span className="text-[10px] font-mono text-slate-400">{name}:</span>
                  <div className="flex items-center gap-1.5">
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      state === 'closed' ? 'bg-green' : 
                      state === 'open' ? 'bg-rose animate-pulse' : 
                      'bg-amber animate-bounce'
                    }`} />
                    <span className={`text-[9px] font-bold uppercase ${
                      state === 'closed' ? 'text-green-text' : 
                      state === 'open' ? 'text-rose-text' : 
                      'text-amber-text'
                    }`}>{state}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
