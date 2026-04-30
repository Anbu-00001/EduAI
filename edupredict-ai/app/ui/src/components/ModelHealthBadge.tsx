import { useState, useEffect } from 'react'
import * as Tooltip from '@radix-ui/react-tooltip'
import { apiClient } from '@/api/client'

interface HealthResponse {
  status: string
  version: string
  model_auc?: number | null
  model_version?: string
}

export default function ModelHealthBadge() {
  const [data, setData] = useState<HealthResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function fetchHealth() {
      try {
        const res = await apiClient.get<HealthResponse>('/health')
        setData(res.data)
      } catch (err) {
        console.error("Health check failed", err)
      } finally {
        setIsLoading(false)
      }
    }
    fetchHealth()
  }, [])

  let statusText = 'Unknown'
  let colorClass = 'bg-slate-500'
  let textColorClass = 'text-slate-500'
  let tooltipText = 'Model health data unavailable.'
  let pulse = false

  if (!isLoading && data && data.model_auc !== undefined && data.model_auc !== null) {
    if (data.model_auc >= 0.78) {
      statusText = 'Operational'
      colorClass = 'bg-green'
      textColorClass = 'text-green-text'
      tooltipText = 'Model performing within normal parameters.'
      pulse = true
    } else if (data.model_auc >= 0.70) {
      statusText = 'Degraded'
      colorClass = 'bg-amber'
      textColorClass = 'text-amber-text'
      tooltipText = 'Model performance below optimal. Assessment results may be less reliable.'
    }
  }

  return (
    <Tooltip.Provider delayDuration={200}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-card-2 border border-border cursor-help">
            <span className={`w-2 h-2 rounded-full ${colorClass} ${pulse ? 'animate-pulse' : ''}`} />
            <span className={`text-[10px] font-mono ${textColorClass}`}>{statusText}</span>
          </div>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            className="z-50 max-w-[200px] px-3 py-2 text-xs text-slate-300 bg-card border border-border rounded-xl shadow-xl"
            sideOffset={5}
          >
            {tooltipText}
            <Tooltip.Arrow className="fill-border" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  )
}
