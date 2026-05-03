import { useState, useMemo } from 'react'
import * as Slider from '@radix-ui/react-slider'
import { Zap } from 'lucide-react'

interface WhatIfProfile {
  cgpa: number
  internships_count: number
  backlogs: number
  college_placement_rate: number
}

interface WhatIfSimulatorProps {
  originalProb: number
  shapContributions?: Record<string, number>
  profile: WhatIfProfile
  onReassess: (overrides: WhatIfProfile) => void
}

export default function WhatIfSimulator({
  originalProb,
  shapContributions,
  profile,
  onReassess,
}: WhatIfSimulatorProps) {
  const [simCgpa, setSimCgpa] = useState(profile.cgpa)
  const [simInterns, setSimInterns] = useState(profile.internships_count)
  const [simBacklogs, setSimBacklogs] = useState(profile.backlogs)
  const [simPlacement, setSimPlacement] = useState(profile.college_placement_rate)

  const shap = shapContributions ?? {}

  const estimatedProb = useMemo(() => {
    const eps = 0.05
    // Sensitivity = SHAP(feature) / max(original_norm, eps)  →  contribution per unit of normalized change
    const sCgpa =     (shap['cgpa_normalized']           ?? 0) / Math.max(profile.cgpa / 10,                  eps)
    const sInterns =  (shap['internships_count']         ?? 0) / Math.max(profile.internships_count,          eps)
    const sBacklogs = (shap['backlogs']                  ?? 0) / Math.max(profile.backlogs,                   eps)
    const sPlacement= (shap['placement_rate_for_field']  ?? 0) / Math.max(profile.college_placement_rate / 100, eps)

    const delta =
      sCgpa     * (simCgpa / 10 - profile.cgpa / 10) +
      sInterns  * (simInterns - profile.internships_count) +
      sBacklogs * (simBacklogs - profile.backlogs) +
      sPlacement* (simPlacement / 100 - profile.college_placement_rate / 100)

    return Math.max(0, Math.min(1, originalProb + delta))
  }, [simCgpa, simInterns, simBacklogs, simPlacement, shap, profile, originalProb])

  const deltaPct = Math.round((estimatedProb - originalProb) * 100)
  const estTierColor =
    estimatedProb >= 0.65 ? '#22c55e' : estimatedProb >= 0.50 ? '#f59e0b' : '#ef4444'

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-5">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <Zap size={16} className="text-yellow-400" />
          <span className="text-sm font-semibold text-white">What-If Simulator</span>
          <span className="text-[10px] text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full">
            linear estimate · no API call
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-bold text-xl" style={{ color: estTierColor }}>
            {Math.round(estimatedProb * 100)}%
          </span>
          {deltaPct !== 0 && (
            <span className={`text-xs font-medium ${deltaPct > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {deltaPct > 0 ? '+' : ''}{deltaPct}%
            </span>
          )}
        </div>
      </div>

      <div className="space-y-4 mb-5">
        <SimSlider
          label="CGPA"
          value={simCgpa}
          original={profile.cgpa}
          min={0} max={10} step={0.1}
          format={v => v.toFixed(1)}
          onChange={setSimCgpa}
          positive
        />
        <SimSlider
          label="Internships"
          value={simInterns}
          original={profile.internships_count}
          min={0} max={10} step={1}
          format={v => String(Math.round(v))}
          onChange={v => setSimInterns(Math.round(v))}
          positive
        />
        <SimSlider
          label="Backlogs"
          value={simBacklogs}
          original={profile.backlogs}
          min={0} max={20} step={1}
          format={v => String(Math.round(v))}
          onChange={v => setSimBacklogs(Math.round(v))}
          positive={false}
        />
        <SimSlider
          label="Placement Rate %"
          value={simPlacement}
          original={profile.college_placement_rate}
          min={0} max={100} step={1}
          format={v => `${Math.round(v)}%`}
          onChange={v => setSimPlacement(Math.round(v))}
          positive
        />
      </div>

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-3 border-t border-slate-800">
        <p className="text-[10px] text-slate-500">
          Uses SHAP sensitivity weights · actual results may vary
        </p>
        <button
          onClick={() =>
            onReassess({
              cgpa: simCgpa,
              internships_count: simInterns,
              backlogs: simBacklogs,
              college_placement_rate: simPlacement,
            })
          }
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-xl transition-colors shrink-0"
        >
          <Zap size={12} />
          Reassess with these values
        </button>
      </div>
    </div>
  )
}

interface SimSliderProps {
  label: string
  value: number
  original: number
  min: number
  max: number
  step: number
  format: (v: number) => string
  onChange: (v: number) => void
  positive: boolean
}

function SimSlider({ label, value, original, min, max, step, format, onChange, positive }: SimSliderProps) {
  const changed = Math.abs(value - original) > step * 0.5
  const improved = positive ? value > original : value < original

  return (
    <div className="flex items-center gap-3">
      <div className="w-32 shrink-0">
        <span className="text-[11px] text-slate-400">{label}</span>
        <div className="flex items-center gap-1 mt-0.5">
          {changed && (
            <span className="text-[10px] text-slate-600 line-through">{format(original)}</span>
          )}
          <span
            className={`text-[12px] font-semibold ${
              changed ? (improved ? 'text-emerald-400' : 'text-red-400') : 'text-slate-300'
            }`}
          >
            {format(value)}
          </span>
        </div>
      </div>

      <Slider.Root
        value={[value]}
        onValueChange={([v]) => onChange(v)}
        min={min}
        max={max}
        step={step}
        className="relative flex items-center select-none touch-none flex-1 h-5"
      >
        <Slider.Track className="bg-slate-700 relative grow rounded-full h-1.5 cursor-pointer">
          <Slider.Range
            className="absolute rounded-full h-full"
            style={{ backgroundColor: changed ? (improved ? '#22c55e' : '#ef4444') : '#3b82f6' }}
          />
        </Slider.Track>
        <Slider.Thumb className="block w-4 h-4 bg-white rounded-full shadow-md focus:outline-none focus:ring-2 focus:ring-blue-400 cursor-grab active:cursor-grabbing" />
      </Slider.Root>
    </div>
  )
}
