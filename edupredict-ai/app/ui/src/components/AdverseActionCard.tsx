import { AlertTriangle, Download } from 'lucide-react'
import type { AdverseAction } from '@/api/types'

interface AdverseActionCardProps {
  adverseAction: AdverseAction
  assessmentId: string
}

export default function AdverseActionCard({ adverseAction, assessmentId }: AdverseActionCardProps) {
  const handlePrint = () => {
    window.print()
  }

  if (!adverseAction.adverse_action_required) return null

  return (
    <div
      className="border-l-4 border-rose bg-rose-dim rounded-2xl p-6 mt-6"
      role="alert"
      aria-live="assertive"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-rose-text shrink-0" />
          <div>
            <p className="text-xs font-black uppercase tracking-widest text-rose-text">
              Adverse Action Notice
            </p>
            <p className="text-[10px] text-slate-500 mt-0.5">RBI FREE-AI Framework Compliant</p>
          </div>
        </div>
        <button
          onClick={handlePrint}
          className="flex items-center gap-1.5 text-[11px] text-slate-400 hover:text-slate-200 transition-colors px-3 py-1.5 rounded-lg bg-rose/10 hover:bg-rose/20 border border-rose/20"
        >
          <Download className="w-3.5 h-3.5" />
          Download PDF
        </button>
      </div>

      {/* Reasons */}
      <div className="space-y-2 mb-4">
        <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Top Risk Factors</p>
        {adverseAction.reasons.slice(0, 3).map((reason) => (
          <div key={reason.code} className="flex items-start gap-3 p-3 bg-black/20 rounded-xl border border-rose/10">
            <span className="text-[9px] font-black uppercase text-rose-text bg-rose/20 px-2 py-0.5 rounded-md font-mono shrink-0">
              {reason.code}
            </span>
            <p className="text-xs text-slate-300">{reason.reason}</p>
          </div>
        ))}
      </div>

      {/* Notice */}
      <div className="border-t border-rose/20 pt-4">
        <p className="text-xs text-slate-400 leading-relaxed">{adverseAction.notice}</p>
        <div className="flex items-center justify-between mt-3">
          <p className="text-[10px] text-slate-600 font-mono">
            Ref: {adverseAction.rbi_reference}
          </p>
          <p className="text-[10px] text-slate-600 font-mono">
            Assessment: {assessmentId.slice(0, 12)}…
          </p>
        </div>
        <p className="text-[10px] text-rose-text mt-2">
          ⓘ You have the right to dispute this assessment. Contact your lender within 60 days.
        </p>
      </div>
    </div>
  )
}
