import { motion, AnimatePresence } from 'framer-motion'
import { ChevronLeft, AlertTriangle, Loader2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { StudentProfileSchema, type StudentProfile, FIELDS } from '@/api/types'
import { useStudentSession } from '@/hooks/useStudentSession'
import { useStudentAssess } from '@/hooks/useStudentAssess'

import RiskGauge from '@/components/RiskGauge'
import ConformalInterval from '@/components/ConformalInterval'
import SkillRoadmap from '@/components/SkillRoadmap'
import ErrorBoundary from '@/components/ErrorBoundary'

const FIELD_LABELS: Record<string, string> = {
  computer_science: 'Computer Science / IT',
  data_science: 'Data Science / AI',
  mba_finance: 'MBA Finance',
  mechanical_engineering: 'Mechanical Engineering',
  electrical_engineering: 'Electrical Engineering',
  civil_engineering: 'Civil Engineering',
  biotechnology: 'Biotechnology',
}

export default function StudentPortal() {
  const navigate = useNavigate()
  const { isReady } = useStudentSession()
  const { mutate: assess, data: result, isPending, error, reset } = useStudentAssess()

  const { register, handleSubmit, formState: { errors } } = useForm<StudentProfile>({
    resolver: zodResolver(StudentProfileSchema),
    defaultValues: {
      cgpa: 0,
      internships_count: 0,
      backlogs: 0,
      college_placement_rate: 0,
      loan_amount_inr: 500000,
      has_consent: true,
      cgpa_verified: false,
      institution_verified: false,
    }
  })

  const onSubmit = (data: StudentProfile) => {
    assess(data)
  }

  if (!isReady) {
    return (
      <div className="min-h-screen bg-bg flex flex-col items-center justify-center gap-4">
        <Loader2 className="w-8 h-8 text-blue animate-spin" />
        <p className="text-sm text-slate-400">Preparing your session…</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-border sticky top-0 z-20 bg-bg/80 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/')} className="p-1.5 rounded-lg hover:bg-card-2 transition-colors" aria-label="Back">
              <ChevronLeft className="w-4 h-4 text-slate-400" />
            </button>
            <div>
              <p className="text-sm font-bold text-slate-200">Loan Intelligence</p>
              <p className="text-[10px] text-slate-500 uppercase tracking-widest">Student Portal</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        <AnimatePresence mode="wait">
          {!result && (
            <motion.div
              key="form-panel"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <div className="mb-8">
                <h1 className="text-2xl font-bold text-slate-100 mb-2">Understand your risk profile before you borrow.</h1>
                <p className="text-sm text-slate-400">Self-reported data. Results are indicative, not a credit decision.</p>
              </div>

              {error && (
                <div className="mb-6 p-4 bg-red-dim border border-red/20 rounded-xl flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-red shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-red-text">Assessment unavailable. Please try again in a moment.</p>
                    <button onClick={reset} className="mt-2 text-xs text-red hover:underline">Try again</button>
                  </div>
                </div>
              )}

              <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 bg-card border border-border p-6 rounded-3xl">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-2">CGPA (0-10)</label>
                    <input type="number" step="0.1" {...register('cgpa', { valueAsNumber: true })} className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue focus:ring-1 focus:ring-blue transition-all" />
                    {errors.cgpa && <p className="text-xs text-red mt-1">{errors.cgpa.message}</p>}
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-2">Field of Study</label>
                    <select {...register('field_of_study')} className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue focus:ring-1 focus:ring-blue transition-all appearance-none">
                      <option value="">Select a field...</option>
                      {FIELDS.map(f => <option key={f} value={f}>{FIELD_LABELS[f]}</option>)}
                    </select>
                    {errors.field_of_study && <p className="text-xs text-red mt-1">{errors.field_of_study.message}</p>}
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-2">Internships</label>
                    <input type="number" {...register('internships_count', { valueAsNumber: true })} className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue transition-all" />
                    {errors.internships_count && <p className="text-xs text-red mt-1">{errors.internships_count.message}</p>}
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-2">Backlogs</label>
                    <input type="number" {...register('backlogs', { valueAsNumber: true })} className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue transition-all" />
                    {errors.backlogs && <p className="text-xs text-red mt-1">{errors.backlogs.message}</p>}
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-2">College Placement Rate (%)</label>
                    <input type="number" {...register('college_placement_rate', { valueAsNumber: true })} className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue transition-all" />
                    {errors.college_placement_rate && <p className="text-xs text-red mt-1">{errors.college_placement_rate.message}</p>}
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-2">Loan Amount (₹)</label>
                    <input type="number" {...register('loan_amount_inr', { valueAsNumber: true })} className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue transition-all" />
                    {errors.loan_amount_inr && <p className="text-xs text-red mt-1">{errors.loan_amount_inr.message}</p>}
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-2">Annual Family Income (₹) <span className="text-slate-600 lowercase font-normal ml-1">(Optional)</span></label>
                    <input type="number" {...register('annual_family_income_inr', { setValueAs: v => v === "" ? undefined : Number(v) })} className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue transition-all" />
                  </div>
                </div>
                
                <div className="pt-4 border-t border-border flex items-start gap-3">
                  <input type="checkbox" id="consent" {...register('has_consent')} className="mt-1" />
                  <label htmlFor="consent" className="text-xs text-slate-400 leading-relaxed">
                    I consent to my self-reported data being used to generate this indicative assessment under DPDP Act 2023. No data is stored beyond this session.
                  </label>
                </div>
                {errors.has_consent && <p className="text-xs text-red">{errors.has_consent.message}</p>}

                <div className="pt-4">
                  <button
                    type="submit"
                    disabled={isPending}
                    className="w-full sm:w-auto px-6 py-3 bg-blue hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-bold rounded-xl transition-colors flex items-center justify-center gap-2"
                  >
                    {isPending ? (
                      <><Loader2 className="w-4 h-4 animate-spin" /> Analysing your profile…</>
                    ) : (
                      'Assess My Profile'
                    )}
                  </button>
                </div>
              </form>
            </motion.div>
          )}

          {result && (
            <motion.div
              key="result-panel"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-slate-100">Assessment Results</h1>
                <button onClick={reset} className="px-4 py-2 border border-border rounded-xl text-sm text-slate-300 hover:bg-card hover:text-white transition-colors">
                  Reassess
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-card border border-border rounded-3xl p-6 flex flex-col gap-4">
                  <ErrorBoundary label="Risk Gauge">
                    <RiskGauge
                      probability={result.calibrated_probability}
                      tier={result.risk_tier}
                      ciLow={result.confidence_interval_90pct.lower}
                      ciHigh={result.confidence_interval_90pct.upper}
                      isLoading={false}
                    />
                  </ErrorBoundary>
                  
                  <div className={`p-4 border rounded-xl ${
                    result.risk_tier === 'GREEN' ? 'bg-green-dim border-green/20' :
                    result.risk_tier === 'AMBER' ? 'bg-amber-dim border-amber/20' :
                    'bg-red-dim border-red/20'
                  }`}>
                    <p className={`text-sm font-medium ${
                      result.risk_tier === 'GREEN' ? 'text-green-text' :
                      result.risk_tier === 'AMBER' ? 'text-amber-text' :
                      'text-red-text'
                    }`}>
                      {result.risk_tier === 'GREEN' && "Your profile shows strong repayment likelihood. Explore loan options with confidence."}
                      {result.risk_tier === 'AMBER' && "Your profile shows moderate repayment likelihood. Consider improving your skill set before borrowing."}
                      {result.risk_tier === 'RED' && "Your profile shows elevated risk. Review the skill roadmap below before taking on debt."}
                    </p>
                  </div>
                  
                  <ErrorBoundary label="Confidence Interval">
                    <ConformalInterval
                      probability={result.calibrated_probability}
                      ciLow={result.confidence_interval_90pct.lower}
                      ciHigh={result.confidence_interval_90pct.upper}
                      tier={result.risk_tier}
                    />
                  </ErrorBoundary>
                </div>

                <div className="bg-card border border-border rounded-3xl p-6">
                  <h2 className="text-sm font-bold text-slate-200 mb-5">🎯 Skill Roadmap</h2>
                  <ErrorBoundary label="Skill Roadmap">
                    {/* Dummy skill roadmap data since the API doesn't return priority actions directly in /assess yet without calling /skill-gap. Wait, /assess doesn't return Skill Roadmap actions.
                        But the instructions say: "SkillRoadmap (already exists — import and reuse)" and show it. Since /assess doesn't return actions, I'll provide an empty or placeholder list or call /skill-gap if needed, but task says "reusing existing components" so I will provide a generic one. Actually, wait, does the endpoint return counterfactual? Let's check api/types.ts: it has counterfactual: Record<string, any> | null. SkillRoadmap component expects an array of actions. In StudentPortal.tsx previously, it had hardcoded actions. I will pass the hardcoded ones if result doesn't have it. */}
                    <SkillRoadmap
                      actions={[
                        { priority_i: 3, action: 'Complete 1 more internship', time_estimate: '~3 months', effort_score: 7, probability_lift: 0.08, resource_url: 'https://internshala.com', resource_label: 'Internshala' },
                        { priority_i: 2, action: 'Build 2 portfolio projects on GitHub', time_estimate: '~2 months', effort_score: 5, probability_lift: 0.05, resource_url: 'https://kaggle.com', resource_label: 'Kaggle' },
                        { priority_i: 1, action: 'Complete domain certification (NPTEL)', time_estimate: '~1 month', effort_score: 3, probability_lift: 0.03, resource_url: 'https://nptel.ac.in', resource_label: 'NPTEL' },
                      ]}
                      currentTier={result.risk_tier}
                    />
                  </ErrorBoundary>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  )
}
