import { TrendingUp, TrendingDown, AlertTriangle, Activity } from 'lucide-react'
import type { AdminMetrics } from '@/hooks/useAdminMetrics'

interface MetricsStripProps {
  data: AdminMetrics | undefined
  isLoading: boolean
}

function MetricCard({
  label, value, subtitle, delta, icon: Icon, valueColor
}: {
  label: string
  value: string
  subtitle?: string
  delta?: string
  icon: React.ComponentType<{ className?: string }>
  valueColor?: string
}) {
  return (
    <div className="bg-card border border-border rounded-2xl p-4 flex flex-col gap-1 hover:border-border-2 transition-colors">
      <div className="flex items-center gap-2 mb-1">
        <Icon className="w-3.5 h-3.5 text-slate-500" />
        <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">{label}</p>
      </div>
      <p className={`text-2xl font-bold font-mono ${valueColor ?? 'text-white'}`}>{value}</p>
      {delta && (
        <p className="text-[11px] text-green-text flex items-center gap-1">
          <TrendingUp className="w-3 h-3" /> {delta}
        </p>
      )}
      {subtitle && (
        <p className="text-[10px] text-slate-500">{subtitle}</p>
      )}
    </div>
  )
}

function Skeleton() {
  return <div className="bg-card border border-border rounded-2xl p-4 h-[100px] animate-pulse" />
}

export default function MetricsStrip({ data, isLoading }: MetricsStripProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <Skeleton key={i} />)}
      </div>
    )
  }

  const auc = data?.live.auc ?? data?.static.auc
  const ece = data?.live.ece ?? data?.static.ece
  const dpi = data?.live.dpi
  const preds = data?.live.predictions_1h

  const aucDelta = auc != null ? `+${(auc - 0.62).toFixed(3)} vs CIBIL` : undefined
  const aucColor = auc != null && auc >= 0.78 ? 'text-green-text' : 'text-amber-text'
  const eceColor = ece != null && ece < 0.03 ? 'text-green-text' : 'text-rose-text'
  const eceSubtitle = ece != null ? (ece < 0.03 ? '<0.03 target ✓' : 'Above 0.03 target ⚠') : '—'
  const dpiFair = dpi != null && dpi >= 0.8

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricCard
        label="AUC"
        value={auc != null ? auc.toFixed(4) : '—'}
        delta={aucDelta}
        icon={TrendingUp}
        valueColor={aucColor}
      />
      <MetricCard
        label="ECE"
        value={ece != null ? ece.toFixed(4) : '—'}
        subtitle={eceSubtitle}
        icon={Activity}
        valueColor={eceColor}
      />
      <MetricCard
        label="Fairness DPI"
        value={dpi != null ? dpi.toFixed(3) : '—'}
        subtitle={dpiFair ? '✓ Fair (≥0.80)' : '⚠ Review Required'}
        icon={AlertTriangle}
        valueColor={dpiFair ? 'text-green-text' : 'text-rose-text'}
      />
      <MetricCard
        label="Predictions / hr"
        value={preds != null ? preds.toFixed(0) : '—'}
        subtitle="/hr"
        icon={TrendingDown}
        valueColor="text-blue-text"
      />
    </div>
  )
}
