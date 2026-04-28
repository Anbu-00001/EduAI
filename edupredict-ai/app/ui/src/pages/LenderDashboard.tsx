import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2, ChevronLeft, Info } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { StudentProfileSchema, FIELDS, type StudentProfile } from '@/api/types'
import { useAssess } from '@/hooks/useAssess'
import { useAdminMetrics } from '@/hooks/useAdminMetrics'
import { formatINR } from '@/lib/utils'
import MetricsStrip from '@/components/MetricsStrip'
import RiskGauge from '@/components/RiskGauge'
import ShapWaterfall from '@/components/ShapWaterfall'
import ConformalInterval from '@/components/ConformalInterval'
import FreshnessPanel from '@/components/FreshnessPanel'
import AdverseActionCard from '@/components/AdverseActionCard'

const FIELD_LABELS: Record<string, string> = {
  computer_science:       'Computer Science / IT',
  data_science:           'Data Science / AI',
  mba_finance:            'MBA / Finance',
  mechanical_engineering: 'Mechanical Engineering',
  electrical_engineering: 'Electrical Engineering',
  civil_engineering:      'Civil Engineering',
  biotechnology:          'Biotechnology',
}

const RISK_BORDER: Record<string, string> = {
  GREEN: 'border-l-green',
  AMBER: 'border-l-amber',
  RED:   'border-l-rose',
}

export default function LenderDashboard() {
  const navigate = useNavigate()
  const { data: metricsData, isLoading: metricsLoading } = useAdminMetrics()
  const { mutate: assess, data: result, isPending, error, reset } = useAssess()

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isValid },
  } = useForm<StudentProfile>({
    resolver: zodResolver(StudentProfileSchema),
    defaultValues: {
      cgpa: 8.0,
      internships_count: 2,
      backlogs: 0,
      field_of_study: 'computer_science',
      college_placement_rate: 80,
      loan_amount_inr: 500000,
      has_consent: true,
      cgpa_verified: false,
      institution_verified: false,
    },
    mode: 'onChange',
  })

  const onSubmit = (data: StudentProfile) => {
    reset()
    assess(data)
  }

  return (
    <div className="min-h-screen bg-bg">
      {/* Nav */}
      <header className="border-b border-border sticky top-0 z-20 bg-bg/80 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/')}
              className="p-1.5 rounded-lg hover:bg-card-2 transition-colors"
              aria-label="Back to home"
            >
              <ChevronLeft className="w-4 h-4 text-slate-400" />
            </button>
            <div>
              <p className="text-sm font-bold text-slate-200">EduPredict AI</p>
              <p className="text-[10px] text-slate-500 uppercase tracking-widest">Lender Risk Dashboard</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green animate-pulse" />
            <span className="text-[10px] font-mono text-slate-500">AUTHENTICATED</span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Live Metrics Strip */}
        <MetricsStrip data={metricsData} isLoading={metricsLoading} />

        {/* Main grid: form + results */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* ── INPUT FORM ── */}
          <aside className="lg:col-span-4">
            <div className="bg-card border border-border rounded-3xl p-6 sticky top-20">
              <h2 className="text-sm font-bold text-slate-200 mb-5 flex items-center gap-2">
                <span className="text-blue-text">◈</span> Applicant Profile
              </h2>

              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
                {/* CGPA */}
                <div>
                  <label htmlFor="cgpa" className="block text-[10px] text-slate-500 uppercase font-bold mb-1">
                    CGPA (0 – 10)
                  </label>
                  <input
                    id="cgpa"
                    type="number"
                    step="0.1"
                    min="0"
                    max="10"
                    {...register('cgpa', { valueAsNumber: true })}
                    className="w-full bg-card-2 border border-border-2 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue/60 focus:ring-1 focus:ring-blue/30 transition-colors"
                  />
                  {errors.cgpa && <p className="text-xs text-rose-text mt-1">{errors.cgpa.message}</p>}
                </div>

                {/* Internships */}
                <div>
                  <label htmlFor="internships" className="block text-[10px] text-slate-500 uppercase font-bold mb-1">
                    Internships Count
                  </label>
                  <input
                    id="internships"
                    type="number"
                    min="0"
                    max="10"
                    {...register('internships_count', { valueAsNumber: true })}
                    className="w-full bg-card-2 border border-border-2 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue/60 focus:ring-1 focus:ring-blue/30 transition-colors"
                  />
                  {errors.internships_count && <p className="text-xs text-rose-text mt-1">{errors.internships_count.message}</p>}
                </div>

                {/* Backlogs */}
                <div>
                  <label htmlFor="backlogs" className="block text-[10px] text-slate-500 uppercase font-bold mb-1">
                    Academic Backlogs
                  </label>
                  <input
                    id="backlogs"
                    type="number"
                    min="0"
                    max="20"
                    {...register('backlogs', { valueAsNumber: true })}
                    className="w-full bg-card-2 border border-border-2 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue/60 focus:ring-1 focus:ring-blue/30 transition-colors"
                  />
                  {errors.backlogs && <p className="text-xs text-rose-text mt-1">{errors.backlogs.message}</p>}
                </div>

                {/* Field of study */}
                <div>
                  <label htmlFor="field-of-study" className="block text-[10px] text-slate-500 uppercase font-bold mb-1">
                    Field of Study
                  </label>
                  <Controller
                    name="field_of_study"
                    control={control}
                    render={({ field }) => (
                      <select
                        id="field-of-study"
                        {...field}
                        className="w-full bg-card-2 border border-border-2 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue/60 focus:ring-1 focus:ring-blue/30 transition-colors"
                      >
                        {FIELDS.map(f => (
                          <option key={f} value={f} className="bg-card-2">{FIELD_LABELS[f]}</option>
                        ))}
                      </select>
                    )}
                  />
                </div>

                {/* College placement rate */}
                <div>
                  <label htmlFor="placement-rate" className="block text-[10px] text-slate-500 uppercase font-bold mb-1">
                    College Placement Rate (%)
                  </label>
                  <input
                    id="placement-rate"
                    type="number"
                    min="0"
                    max="100"
                    {...register('college_placement_rate', { valueAsNumber: true })}
                    className="w-full bg-card-2 border border-border-2 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue/60 focus:ring-1 focus:ring-blue/30 transition-colors"
                  />
                  {errors.college_placement_rate && <p className="text-xs text-rose-text mt-1">{errors.college_placement_rate.message}</p>}
                </div>

                {/* Loan amount */}
                <div>
                  <label htmlFor="loan-amount" className="block text-[10px] text-slate-500 uppercase font-bold mb-1">
                    Loan Amount (₹10K – ₹50L)
                  </label>
                  <input
                    id="loan-amount"
                    type="number"
                    min="10000"
                    max="5000000"
                    step="10000"
                    {...register('loan_amount_inr', { valueAsNumber: true })}
                    className="w-full bg-card-2 border border-border-2 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue/60 focus:ring-1 focus:ring-blue/30 transition-colors"
                  />
                  {errors.loan_amount_inr && <p className="text-xs text-rose-text mt-1">{errors.loan_amount_inr.message}</p>}
                </div>

                {/* DPDP Consent */}
                <div className="pt-3 border-t border-border">
                  <label className="flex items-start gap-3 cursor-pointer group">
                    <input
                      id="consent-checkbox"
                      type="checkbox"
                      {...register('has_consent')}
                      className="mt-0.5 w-4 h-4 rounded border-slate-700 bg-card-2 text-blue accent-blue focus:ring-blue/30"
                    />
                    <span className="text-[11px] text-slate-400 group-hover:text-slate-300 transition-colors leading-relaxed">
                      Applicant has provided explicit consent for data processing under DPDP Act 2023 guidelines.
                    </span>
                  </label>
                  {errors.has_consent && <p className="text-xs text-rose-text mt-1">{errors.has_consent.message}</p>}
                </div>

                {/* Submit */}
                <button
                  type="submit"
                  disabled={isPending || !isValid}
                  className="w-full py-3.5 rounded-2xl font-bold text-sm transition-all flex items-center justify-center gap-2
                    bg-blue hover:bg-blue/90 disabled:bg-card-2 disabled:text-slate-600 active:scale-[0.98]"
                >
                  {isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Analyzing…
                    </>
                  ) : 'Validate & Assess'}
                </button>
              </form>

              {/* Error state */}
              {error && (
                <div className="mt-4 p-4 bg-rose-dim border border-rose/20 rounded-2xl">
                  <div className="flex items-start gap-2">
                    <Info className="w-4 h-4 text-rose-text shrink-0 mt-0.5" />
                    <p className="text-xs text-rose-text">{error.message}</p>
                  </div>
                  <button
                    onClick={() => assess({ cgpa: 8, internships_count: 2, backlogs: 0, field_of_study: 'computer_science', college_placement_rate: 80, loan_amount_inr: 500000, has_consent: true, cgpa_verified: false, institution_verified: false })}
                    className="mt-2 text-xs text-blue-text underline"
                  >
                    Retry
                  </button>
                </div>
              )}
            </div>
          </aside>

          {/* ── RESULTS PANEL ── */}
          <section className="lg:col-span-8 space-y-6">
            <AnimatePresence mode="wait">
              {result ? (
                <motion.div
                  key="result"
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.4, ease: 'easeOut' }}
                  className="space-y-6"
                >
                  {/* Hero result card */}
                  <div className={`bg-card border-l-4 ${RISK_BORDER[result.risk_tier]} border border-border rounded-3xl p-6`}>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
                      {/* Left: Gauge */}
                      <div>
                        <RiskGauge
                          probability={result.calibrated_probability}
                          tier={result.risk_tier}
                          ciLow={result.confidence_interval_90pct.lower}
                          ciHigh={result.confidence_interval_90pct.upper}
                          isLoading={false}
                        />
                      </div>

                      {/* Right: Details */}
                      <div className="space-y-4">
                        <div className="p-4 bg-card-2 rounded-2xl border border-border">
                          <p className="text-xs text-slate-500 mb-2">Blended Estimate</p>
                          <div className="grid grid-cols-3 gap-2 text-center">
                            {[
                              { label: 'Model', value: result.p_model },
                              { label: 'Cohort', value: result.p_cohort },
                              { label: 'Blend', value: result.p_blended },
                            ].map(m => (
                              <div key={m.label}>
                                <p className="text-[10px] text-slate-500 uppercase">{m.label}</p>
                                <p className="text-lg font-bold font-mono text-slate-200">{(m.value * 100).toFixed(1)}%</p>
                              </div>
                            ))}
                          </div>
                        </div>

                        <ConformalInterval
                          probability={result.calibrated_probability}
                          ciLow={result.confidence_interval_90pct.lower}
                          ciHigh={result.confidence_interval_90pct.upper}
                          tier={result.risk_tier}
                        />

                        <div className="p-4 bg-card-2 rounded-2xl border border-border">
                          <p className="text-sm text-slate-300 leading-relaxed">{result.recommendation}</p>
                        </div>
                      </div>
                    </div>

                    {/* Metadata bar */}
                    <div className="mt-4 pt-4 border-t border-border flex flex-wrap gap-4 text-[10px] text-slate-600 font-mono">
                      <span>ID: {result.assessment_id?.slice(0, 12)}…</span>
                      <span>Model: {result.model_version}</span>
                      <span>Potential: {result.potential_score?.toFixed(2)}</span>
                    </div>
                  </div>

                  {/* SHAP chart */}
                  <div className="bg-card border border-border rounded-3xl p-6">
                    <ShapWaterfall contributions={result.shap_contributions} />
                  </div>

                  {/* Freshness Panel */}
                  <FreshnessPanel />

                  {/* Adverse Action */}
                  {result.adverse_action?.adverse_action_required && (
                    <AdverseActionCard
                      adverseAction={result.adverse_action}
                      assessmentId={result.assessment_id}
                    />
                  )}
                </motion.div>
              ) : (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="bg-card border border-dashed border-border-2 rounded-3xl flex flex-col items-center justify-center min-h-[500px] text-slate-600"
                >
                  {isPending ? (
                    <div className="flex flex-col items-center gap-4">
                      <div className="relative">
                        <div className="w-16 h-16 rounded-full border border-border-2 flex items-center justify-center">
                          <Loader2 className="w-8 h-8 text-blue animate-spin" />
                        </div>
                        <div className="absolute inset-0 rounded-full border border-blue/20 animate-ping" />
                      </div>
                      <div className="text-center">
                        <p className="text-sm font-medium text-slate-400">Running 14-feature ML inference…</p>
                        <p className="text-xs text-slate-600 mt-1">SHAP explainability · Conformal calibration · Fairness audit</p>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="w-16 h-16 bg-card-2 rounded-full flex items-center justify-center mb-4 text-3xl">⚙</div>
                      <p className="text-sm font-medium text-slate-500">Enter student profile to run assessment</p>
                      <p className="text-xs text-slate-600 mt-1">Results include SHAP explainability and conformal intervals</p>
                    </>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </section>
        </div>
      </main>
    </div>
  )
}

// Needed for formatINR import without unused-vars error
void formatINR
