import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Banknote, ChevronDown, ChevronUp, Loader2 } from 'lucide-react'
import { apiClient } from '@/api/client'
import type { LoanScenario } from '@/api/types'

interface LoanScenariosCardProps {
  profile: {
    cgpa: number
    internships_count: number
    backlogs: number
    field_of_study: string
    college_placement_rate: number
    loan_amount_inr: number
    annual_family_income_inr?: number
    has_consent?: boolean
    cgpa_verified?: boolean
    institution_verified?: boolean
  }
}

const TIER_COLORS: Record<string, string> = {
  GREEN: '#22c55e',
  AMBER: '#f59e0b',
  RED:   '#ef4444',
}

const AMOUNT_LABELS = ['50% of ask', '75% of ask', 'Full amount']

export default function LoanScenariosCard({ profile }: LoanScenariosCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [scenarios, setScenarios] = useState<LoanScenario[] | null>(null)
  const [note, setNote] = useState('')

  const { mutate: fetch, isPending } = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/student/loan-scenarios', {
        ...profile,
        user_hash: sessionStorage.getItem('ep_student_hash') || 'anonymous',
      })
      return res.data
    },
    onSuccess: (data) => {
      setScenarios(data.scenarios)
      setNote(data.note)
      setExpanded(true)
    },
  })

  const handleToggle = () => {
    if (!scenarios) {
      fetch()
    } else {
      setExpanded(e => !e)
    }
  }

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
      <button
        onClick={handleToggle}
        className="w-full px-5 py-4 flex items-center justify-between hover:bg-slate-800/40 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Banknote size={16} className="text-slate-400" />
          <span className="text-sm font-semibold text-white">Loan Scenario Comparison</span>
          {isPending && <Loader2 size={12} className="animate-spin text-slate-500 ml-1" />}
        </div>
        {scenarios
          ? expanded
            ? <ChevronUp size={16} className="text-slate-400" />
            : <ChevronDown size={16} className="text-slate-400" />
          : <span className="text-xs text-blue-400">Compare 3 amounts →</span>
        }
      </button>

      <AnimatePresence initial={false}>
        {expanded && scenarios && (
          <motion.div
            key="body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {scenarios.map((s, i) => {
                  const tc = TIER_COLORS[s.affordability_tier] ?? '#94a3b8'
                  return (
                    <div
                      key={i}
                      className="rounded-xl p-4 border"
                      style={{
                        backgroundColor: tc + '14',
                        borderColor: tc + '40',
                      }}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] text-slate-400 font-medium">
                          {AMOUNT_LABELS[i]}
                        </span>
                        <span
                          className="text-[9px] font-bold uppercase px-2 py-0.5 rounded-full"
                          style={{ color: tc, backgroundColor: tc + '22' }}
                        >
                          {s.affordability_tier}
                        </span>
                      </div>

                      <p className="text-xl font-bold text-white">
                        ₹{(s.loan_amount_inr / 100_000).toFixed(1)}L
                      </p>
                      <p className="text-sm text-slate-300 mt-0.5">
                        ₹{Math.round(s.emi_monthly).toLocaleString('en-IN')}/mo
                      </p>
                      {s.dti_ratio !== null && (
                        <p className="text-[11px] text-slate-400 mt-1">
                          DTI {(s.dti_ratio * 100).toFixed(1)}%
                        </p>
                      )}
                      <p className="text-[10px] text-slate-500 mt-2 leading-relaxed">{s.verdict}</p>
                    </div>
                  )
                })}
              </div>
              {note && (
                <p className="text-[10px] text-slate-600 mt-3 leading-relaxed">{note}</p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
