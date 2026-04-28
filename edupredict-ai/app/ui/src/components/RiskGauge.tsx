import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'

interface RiskGaugeProps {
  probability: number
  tier: 'GREEN' | 'AMBER' | 'RED'
  ciLow: number
  ciHigh: number
  isLoading: boolean
}

const TIER_COLOR = {
  GREEN: '#10b981',
  AMBER: '#f59e0b',
  RED:   '#f43f5e',
}

const CIRCUMFERENCE = Math.PI * 90  // half circle arc: r=90, C=π*r for half

export default function RiskGauge({ probability, tier, ciLow, ciHigh, isLoading }: RiskGaugeProps) {
  const arcRef = useRef<SVGPathElement>(null)
  const totalArc = Math.PI * 90 // 283 ≈ π×90

  useEffect(() => {
    if (isLoading || !arcRef.current) return
    const target = totalArc * (1 - probability)
    arcRef.current.style.strokeDashoffset = String(totalArc)
    arcRef.current.getBoundingClientRect()

    arcRef.current.style.transition = 'stroke-dashoffset 1.2s ease-out'
    arcRef.current.style.strokeDashoffset = String(target)
  }, [probability, isLoading, totalArc])

  const needleAngle = -90 + probability * 180

  const tierLabel: Record<string, string> = {
    GREEN: 'LOW RISK',
    AMBER: 'MODERATE RISK',
    RED:   'HIGH RISK',
  }

  const tierBg: Record<string, string> = {
    GREEN: 'bg-green-dim text-green-text',
    AMBER: 'bg-amber-dim text-amber-text',
    RED:   'bg-rose-dim text-rose-text',
  }

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-full max-w-[260px]">
        <svg
          viewBox="0 0 200 110"
          role="img"
          aria-label={`Repayment probability gauge showing ${(probability * 100).toFixed(1)}%`}
          className="w-full"
        >
          {/* Background arc */}
          <path
            d="M 10 100 A 90 90 0 0 1 190 100"
            fill="none"
            stroke="#1e293b"
            strokeWidth={12}
            strokeLinecap="round"
          />

          {/* Animated fill arc */}
          {isLoading ? (
            <path
              d="M 10 100 A 90 90 0 0 1 190 100"
              fill="none"
              stroke="#334155"
              strokeWidth={12}
              strokeLinecap="round"
              className="animate-pulse"
            />
          ) : (
            <path
              ref={arcRef}
              d="M 10 100 A 90 90 0 0 1 190 100"
              fill="none"
              stroke={TIER_COLOR[tier]}
              strokeWidth={12}
              strokeLinecap="round"
              strokeDasharray={String(totalArc)}
              strokeDashoffset={String(totalArc)}
            />
          )}

          {/* Needle */}
          {!isLoading && (
            <motion.line
              x1="100"
              y1="100"
              x2="100"
              y2="20"
              stroke="white"
              strokeWidth={2}
              strokeLinecap="round"
              initial={{ rotate: -90 }}
              animate={{ rotate: needleAngle }}
              transition={{ duration: 1.2, ease: 'easeOut' }}
              style={{ originX: '100px', originY: '100px' }}
            />
          )}

          {/* Center dot */}
          <circle cx="100" cy="100" r="5" fill="#1e293b" stroke="white" strokeWidth={2} />

          {/* Probability text */}
          {isLoading ? (
            <rect x="60" y="55" width="80" height="28" rx="6" fill="#1e293b" className="animate-pulse" />
          ) : (
            <text x="100" y="78" textAnchor="middle" fontSize="26" fontWeight="700" fill="white">
              {(probability * 100).toFixed(1)}%
            </text>
          )}
        </svg>
      </div>

      {/* Tier badge */}
      {!isLoading && (
        <div className={`mt-2 px-4 py-1 rounded-full text-xs font-black tracking-widest uppercase ${tierBg[tier]}`}>
          {tierLabel[tier]}
        </div>
      )}

      {/* CI band */}
      {!isLoading && (
        <p className="mt-2 text-xs text-slate-500 font-mono">
          90% CI: {(ciLow * 100).toFixed(1)}% – {(ciHigh * 100).toFixed(1)}%
        </p>
      )}

      {/* CIRCUMFERENCE ref suppression */}
      {CIRCUMFERENCE && null}
    </div>
  )
}
