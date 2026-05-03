import { useState } from 'react'
import * as Tooltip from '@radix-ui/react-tooltip'

interface ConformalIntervalProps {
  probability: number
  ciLow: number
  ciHigh: number
  tier: 'GREEN' | 'AMBER' | 'RED'
}

const TIER_COLOR = {
  GREEN: 'bg-green',
  AMBER: 'bg-amber',
  RED:   'bg-rose',
}

export default function ConformalInterval({ probability, ciLow, ciHigh, tier }: ConformalIntervalProps) {
  const [open, setOpen] = useState(false)

  // Clamp all to [0, 1]
  const lo = Math.max(0, Math.min(1, ciLow))
  const hi = Math.max(0, Math.min(1, ciHigh))
  const p  = Math.max(0, Math.min(1, probability))

  const leftPct  = lo * 100
  const widthPct = (hi - lo) * 100
  const markerPct = p * 100

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">
          Conformal Prediction Interval
        </p>
        <Tooltip.Provider>
          <Tooltip.Root open={open} onOpenChange={setOpen}>
            <Tooltip.Trigger asChild>
              <button
                className="text-[10px] text-blue-text underline underline-offset-2 cursor-pointer"
                aria-label="What is a conformal interval?"
              >
                What is this?
              </button>
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content
                className="max-w-[220px] p-3 text-[11px] text-slate-300 bg-card border border-border-2 rounded-xl shadow-xl leading-relaxed"
                sideOffset={6}
              >
                The q-hat threshold is computed on a held-out calibration set using the conformal
                prediction framework. This guarantees that the true repayment probability falls inside
                this interval at least 90% of the time, without distributional assumptions.
                <Tooltip.Arrow className="fill-card" />
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
        </Tooltip.Provider>
      </div>

      {/* Track */}
      <div className="relative h-2.5 rounded-full bg-card-2 overflow-visible">
        {/* CI band */}
        <div
          className={`absolute h-full rounded-full opacity-60 ${TIER_COLOR[tier]}`}
          style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
        />
        {/* Point estimate marker */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-white border-2 border-slate-900 shadow-lg z-10"
          style={{ left: `calc(${markerPct}% - 6px)` }}
          aria-hidden="true"
        />
      </div>

      {/* Labels */}
      <div className="flex justify-between mt-1.5">
        <span className="text-[10px] text-slate-500 font-mono">{(lo * 100).toFixed(1)}%</span>
        <span className="text-[10px] text-slate-500 font-mono">{(hi * 100).toFixed(1)}%</span>
      </div>

      <p className="mt-2 text-xs text-slate-400 leading-relaxed">
        90% confident repayment probability is between{' '}
        <span className="font-semibold text-slate-200">{(lo * 100).toFixed(1)}%</span>
        {' '}and{' '}
        <span className="font-semibold text-slate-200">{(hi * 100).toFixed(1)}%</span>
      </p>
      <p className="mt-0.5 text-[10px] text-slate-600 italic">
        Distribution-free conformal guarantee
      </p>
    </div>
  )
}
