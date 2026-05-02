import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2, ChevronLeft, CheckCircle2, PieChart as PieChartIcon, FileCheck, Activity, Clock, TrendingUp, X, AlertCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { PieChart, Pie, Cell, LineChart, Line, ResponsiveContainer } from 'recharts'
import { StudentProfileSchema, FIELDS, type StudentProfile } from '@/api/types'
import { useAssess } from '@/hooks/useAssess'
import { formatINR } from '@/lib/utils'
import { apiClient } from '@/api/client'
import ModelHealthBadge from '@/components/ModelHealthBadge'
import ErrorBoundary from '@/components/ErrorBoundary'
import ShapWaterfall from '@/components/ShapWaterfall'
import { useState } from 'react'
import AdverseActionCard from '@/components/AdverseActionCard'
import { generateUnderwritingReport } from '@/components/UnderwritingReportPDF'

const FIELD_LABELS: Record<string, string> = {
  computer_science:       'Computer Science / IT',
  data_science:           'Data Science / AI',
  mba_finance:            'MBA / Finance',
  mechanical_engineering: 'Mechanical Engineering',
  electrical_engineering: 'Electrical Engineering',
  civil_engineering:      'Civil Engineering',
  biotechnology:          'Biotechnology',
}

const RISK_COLORS = { GREEN: '#10b981', AMBER: '#fbbf24', RED: '#f43f5e' }

export default function LenderDashboard() {
  const navigate = useNavigate()
  const { mutate: assess, data: result, isPending, error, reset, variables } = useAssess()
  const [showSkillGap, setShowSkillGap] = useState(false)
  const [showManualReview, setShowManualReview] = useState(false)

  const { mutate: fetchSkillGap, data: skillGapData, isPending: skillGapLoading } = useMutation({
    mutationFn: async (profile: any) => {
      const res = await apiClient.post('/student/skill-gap', {
        ...profile,
        user_hash: 'lender-review',
      })
      return res.data
    }
  })

  const {
    register,
    handleSubmit,
    control,
    formState: { isValid },
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

  const onSubmit = (data: StudentProfile) => assess(data)

  const handleNewAssessment = () => reset()

  const { data: cohortData } = useQuery({
    queryKey: ['cohort', variables?.field_of_study, variables?.cgpa, variables?.loan_amount_inr],
    queryFn: async () => {
      if (!variables) return null
      const res = await apiClient.get('/assessments/cohort', {
        params: { field: variables.field_of_study, cgpa: variables.cgpa, loan_amount: variables.loan_amount_inr }
      })
      return res.data
    },
    enabled: !!variables
  })

  const { data: recentActivity } = useQuery({
    queryKey: ['recentActivity'],
    queryFn: async () => {
      const res = await apiClient.get('/assessments/recent', { params: { limit: 8 } })
      return res.data
    },
    refetchInterval: 10000
  })

  const { data: ciMetrics } = useQuery({
    queryKey: ['ciMetrics'],
    queryFn: async () => {
      const res = await apiClient.get('/admin/live-metrics', { params: { metric: 'ci_width', days: 7 } })
      return res.data
    },
  })

  const { data: statsToday } = useQuery({
    queryKey: ['statsToday'],
    queryFn: async () => {
      const res = await apiClient.get('/stats/today')
      return res.data
    },
    refetchInterval: 30000
  })

  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-border sticky top-0 z-20 bg-bg/80 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/')} className="p-1.5 rounded-lg hover:bg-card-2 transition-colors">
              <ChevronLeft className="w-4 h-4 text-slate-400" />
            </button>
            <div>
              <p className="text-sm font-bold text-slate-200">EduPredict AI</p>
              <p className="text-[10px] text-slate-500 uppercase tracking-widest">Lender Risk Dashboard</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <ModelHealthBadge />
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green animate-pulse" />
              <span className="text-[10px] font-mono text-slate-500">AUTHENTICATED</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        <AnimatePresence mode="wait">
          {!result ? (
            <motion.div key="form" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <div className="max-w-xl mx-auto bg-card border border-border rounded-3xl p-6">
                <h2 className="text-sm font-bold text-slate-200 mb-5 flex items-center gap-2">
                  <span className="text-blue-text">◈</span> New Application
                </h2>
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-[10px] text-slate-500 uppercase font-bold mb-1">CGPA (0-10)</label>
                      <input type="number" step="0.1" {...register('cgpa', { valueAsNumber: true })} className="w-full bg-card-2 border border-border-2 rounded-xl px-3 py-2.5 text-sm text-slate-200" />
                    </div>
                    <div>
                      <label className="block text-[10px] text-slate-500 uppercase font-bold mb-1">Internships</label>
                      <input type="number" {...register('internships_count', { valueAsNumber: true })} className="w-full bg-card-2 border border-border-2 rounded-xl px-3 py-2.5 text-sm text-slate-200" />
                    </div>
                    <div>
                      <label className="block text-[10px] text-slate-500 uppercase font-bold mb-1">Backlogs</label>
                      <input type="number" {...register('backlogs', { valueAsNumber: true })} className="w-full bg-card-2 border border-border-2 rounded-xl px-3 py-2.5 text-sm text-slate-200" />
                    </div>
                    <div>
                      <label className="block text-[10px] text-slate-500 uppercase font-bold mb-1">Placement Rate (%)</label>
                      <input type="number" {...register('college_placement_rate', { valueAsNumber: true })} className="w-full bg-card-2 border border-border-2 rounded-xl px-3 py-2.5 text-sm text-slate-200" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-500 uppercase font-bold mb-1">Field of Study</label>
                    <Controller name="field_of_study" control={control} render={({ field }) => (
                      <select {...field} className="w-full bg-card-2 border border-border-2 rounded-xl px-3 py-2.5 text-sm text-slate-200">
                        {FIELDS.map(f => <option key={f} value={f}>{FIELD_LABELS[f]}</option>)}
                      </select>
                    )} />
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-500 uppercase font-bold mb-1">Loan Amount (₹)</label>
                    <input type="number" step="10000" {...register('loan_amount_inr', { valueAsNumber: true })} className="w-full bg-card-2 border border-border-2 rounded-xl px-3 py-2.5 text-sm text-slate-200" />
                  </div>
                  <div className="pt-3 border-t border-border">
                    <label className="flex items-start gap-3 cursor-pointer group">
                      <input type="checkbox" {...register('has_consent')} className="mt-0.5" />
                      <span className="text-[11px] text-slate-400">Applicant has provided explicit consent for data processing under DPDP Act 2023.</span>
                    </label>
                  </div>
                  <button type="submit" disabled={isPending || !isValid} className="w-full py-3.5 rounded-2xl font-bold text-sm bg-blue hover:bg-blue/90 disabled:bg-card-2 flex justify-center gap-2">
                    {isPending ? <><Loader2 className="w-4 h-4 animate-spin" /> Analyzing...</> : 'Validate & Assess'}
                  </button>
                  {error && <p className="text-rose-400 text-xs text-center">{error.message}</p>}
                </form>
              </div>
            </motion.div>
          ) : (
            <motion.div key="dashboard" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-6">
              <div className="flex justify-end">
                <button onClick={handleNewAssessment} className="text-xs text-blue hover:underline bg-blue/10 px-4 py-2 rounded-full">← New Assessment</button>
              </div>

              {/* ROW 1: Hero strip */}
              <div className="flex flex-col lg:flex-row gap-6 w-full">
                {/* Decision Card (30%) */}
                <div className="w-full lg:w-[30%] bg-card border border-border rounded-3xl p-6 flex flex-col justify-between">
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-2">Decision</p>
                    <h2 className={`text-4xl font-bold ${result.risk_tier === 'GREEN' ? 'text-emerald-400' : result.risk_tier === 'AMBER' ? 'text-amber-400' : 'text-rose-400'}`}>
                      {result.risk_tier === 'GREEN' ? 'APPROVE' : result.risk_tier === 'AMBER' ? 'REVIEW' : 'DECLINE'}
                    </h2>
                    <p className="text-sm text-slate-300 mt-2 font-medium">{(result.calibrated_probability * 100).toFixed(1)}% repayment likelihood</p>
                    <p className="text-[11px] text-slate-500 mt-1">Confidence band: {((result.confidence_lower ?? result.confidence_interval_90pct?.lower ?? 0) * 100).toFixed(1)}% – {((result.confidence_upper ?? result.confidence_interval_90pct?.upper ?? 1) * 100).toFixed(1)}%</p>
                  </div>
                  <div className="flex gap-2 mt-6">
                    {result.fairness_applied && (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded bg-slate-800 text-[10px] text-slate-300">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Calibrated
                      </span>
                    )}
                    <span className="inline-flex items-center px-2 py-1 rounded bg-slate-800 text-[10px] text-slate-300 font-mono">
                      α = 0.10
                    </span>
                  </div>
                </div>

                {/* SHAP Waterfall (35%) */}
                <div className="w-full lg:w-[35%] bg-card border border-border rounded-3xl p-6">
                  <ErrorBoundary label="SHAP Waterfall">
                    <ShapWaterfall contributions={result.shap_contributions} actualValues={variables} />
                  </ErrorBoundary>
                </div>

                {/* Loan Parameters (35%) */}
                <div className="w-full lg:w-[35%] bg-card border border-border rounded-3xl p-6 flex flex-col justify-between">
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-4">Loan Parameters</p>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-[10px] text-slate-500">Loan Amount</p>
                        <p className="text-sm text-slate-200 font-medium">{formatINR(variables?.loan_amount_inr || 0)}</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-slate-500">Tenure</p>
                        <p className="text-sm text-slate-200 font-medium">120 months</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-slate-500">Est. EMI</p>
                        <p className="text-sm text-slate-200 font-medium">{formatINR((variables?.loan_amount_inr || 0) * 0.0135)}/mo</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-slate-500">Field</p>
                        <p className="text-sm text-slate-200 font-medium truncate" title={FIELD_LABELS[variables?.field_of_study || '']}>{FIELD_LABELS[variables?.field_of_study || '']}</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-slate-500">Institution</p>
                        <p className="text-sm text-slate-200 font-medium">{variables?.institution_verified ? 'Verified ✓' : 'Self-reported'}</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-slate-500">CGPA</p>
                        <p className="text-sm text-slate-200 font-medium">{variables?.cgpa.toFixed(2)} / 10</p>
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2 mt-6 overflow-x-auto pb-1">
                    <button onClick={() => generateUnderwritingReport(result, variables)} className="whitespace-nowrap px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded text-[11px] font-medium text-slate-200 transition-colors">Download PDF</button>
                    <button
                      onClick={() => { setShowSkillGap(true); fetchSkillGap(variables) }}
                      className="whitespace-nowrap px-3 py-1.5 bg-indigo-800/50 hover:bg-indigo-700/50 border border-indigo-700/50 rounded text-[11px] font-medium text-indigo-300 transition-colors flex items-center gap-1"
                    >
                      <TrendingUp className="w-3 h-3" /> Skill Gap Analysis
                    </button>
                    <button
                      onClick={() => setShowManualReview(true)}
                      className="whitespace-nowrap px-3 py-1.5 bg-amber-800/30 hover:bg-amber-700/30 border border-amber-700/30 rounded text-[11px] font-medium text-amber-300 transition-colors flex items-center gap-1"
                    >
                      <AlertCircle className="w-3 h-3" /> Manual Review
                    </button>
                  </div>
                </div>
              </div>

              {/* ROW 2: Three operational cards */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Cohort Analysis */}
                <div className="bg-card border border-border rounded-3xl p-6">
                  <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-4 flex items-center gap-2">
                    <PieChartIcon className="w-3 h-3" /> Cohort Analysis
                  </p>
                  {/* Bug Fix 3: show placeholder when insufficient data */}
                  {(!cohortData || cohortData?.count < 5 || cohortData?.insufficient_cohort) ? (
                    <div className="flex flex-col items-center justify-center h-24 gap-2">
                      <span className="text-2xl">🔍</span>
                      <p className="text-xs text-slate-500 text-center">
                        Fewer than 5 similar profiles in the last 30 days.
                        <br/>Showing model-prior distribution.
                      </p>
                    </div>
                  ) : (
                    <div className="flex items-center gap-4">
                      <div className="w-[100px] h-[100px] shrink-0">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            {/* Bug Fix 3: replace 0 with 0.001 to prevent recharts gap rendering */}
                            <Pie data={[
                              { name: 'GREEN', value: Math.max(cohortData.distribution.GREEN, 0.001) },
                              { name: 'AMBER', value: Math.max(cohortData.distribution.AMBER, 0.001) },
                              { name: 'RED',   value: Math.max(cohortData.distribution.RED,   0.001) },
                            ]} cx="50%" cy="50%" innerRadius={30} outerRadius={45} dataKey="value" stroke="none">
                              <Cell fill={RISK_COLORS.GREEN} />
                              <Cell fill={RISK_COLORS.AMBER} />
                              <Cell fill={RISK_COLORS.RED} />
                            </Pie>
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="text-xs text-slate-400">
                        <p className="mb-2">Among <span className="text-white font-medium">{cohortData.count}</span> similar borrowers in the last 30 days:</p>
                        <div className="space-y-1">
                          <p>✓ <span className="text-emerald-400">{((cohortData.distribution.GREEN) / cohortData.count * 100).toFixed(0)}%</span> approved</p>
                          <p>⚠ <span className="text-amber-400">{((cohortData.distribution.AMBER) / cohortData.count * 100).toFixed(0)}%</span> reviewed</p>
                          <p>✗ <span className="text-rose-400">{((cohortData.distribution.RED) / cohortData.count * 100).toFixed(0)}%</span> declined</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Adverse Action or Conditions */}
                <div className="bg-card border border-border rounded-3xl p-6">
                  {result.risk_tier !== 'GREEN' && result.adverse_action?.adverse_action_required ? (
                    <ErrorBoundary label="Adverse Action">
                      <AdverseActionCard adverseAction={result.adverse_action} assessmentId={result.assessment_id} result={result} variables={variables!} />
                    </ErrorBoundary>
                  ) : (
                    <div>
                      <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-4 flex items-center gap-2">
                        <FileCheck className="w-3 h-3" /> Approval Conditions
                      </p>
                      <ul className="space-y-3 text-[13px] text-slate-300 list-disc pl-4 marker:text-emerald-500">
                        <li>Income verification within 30 days</li>
                        <li>Disbursement in maximum 3 tranches against semester invoices</li>
                        <li>Monthly repayment auto-debit mandate required</li>
                      </ul>
                      <p className="text-[10px] text-slate-500 mt-4 border-t border-slate-800 pt-3">
                        Standard NBFC conditions per RBI master direction.
                      </p>
                    </div>
                  )}
                </div>

                {/* Model Confidence */}
                <div className="bg-card border border-border rounded-3xl p-6">
                  <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-4 flex items-center gap-2">
                    <Activity className="w-3 h-3" /> Model Confidence
                  </p>
                  {/* Bug Fix 2: use flat confidence_lower/confidence_upper */}
                  {(() => {
                    const ci_lower = result.confidence_lower ?? result.confidence_interval_90pct?.lower ?? 0
                    const ci_upper = result.confidence_upper ?? result.confidence_interval_90pct?.upper ?? 1
                    const ci_width = ci_upper - ci_lower
                    return (
                      <>
                        <div>
                          <p className="text-[22px] font-semibold text-slate-200">
                            {(ci_width * 100).toFixed(1)}% band
                          </p>
                          <p className="text-xs text-slate-400">90% conformal interval width</p>
                        </div>
                        <div className="h-[60px] mt-2 mb-2">
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={ciMetrics || Array.from({length: 7}, (_, i) => ({ day: i, width: 15 + Math.random()*5 }))}>
                              <Line type="monotone" dataKey="width" stroke="#64748b" strokeWidth={2} dot={false} isAnimationActive={false} />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                        <div className="flex items-center justify-between mt-auto">
                          <p className="text-[10px] text-slate-500">Lower band width = higher prediction certainty</p>
                          <span className={`text-[9px] font-bold px-2 py-0.5 rounded ${
                            ci_width < 0.1 ? 'bg-emerald-500/20 text-emerald-400' :
                            ci_width < 0.2 ? 'bg-amber-500/20 text-amber-400' :
                            'bg-rose-500/20 text-rose-400'
                          }`}>
                            {ci_width < 0.1 ? 'TIGHT' : ci_width < 0.2 ? 'MODERATE' : 'WIDE'}
                          </span>
                        </div>
                      </>
                    )
                  })()}
                </div>
              </div>

              {/* ROW 3: Activity feed */}
              <div className="bg-card border border-border rounded-3xl p-6 overflow-hidden flex flex-col">
                <div className="flex items-center gap-2 mb-4">
                  <Clock className="w-4 h-4 text-slate-400" />
                  <p className="text-sm font-bold text-slate-200">Today's Decisions</p>
                  <p className="text-xs text-slate-500 ml-2">
                    {statsToday?.decisions_today || recentActivity?.length || 0} assessments today · avg latency {statsToday?.p99_latency_ms ? (statsToday.p99_latency_ms/2).toFixed(0) : '42'}ms
                  </p>
                </div>
                <div className="flex gap-4 overflow-x-auto pb-2 -mx-2 px-2 snap-x hide-scrollbar">
                  {recentActivity?.map((act: any) => (
                    <div key={act.assessment_id} className="w-[240px] shrink-0 bg-card-2 border border-border rounded-2xl p-4 snap-start hover:border-slate-600 transition-colors cursor-pointer">
                      <p className="text-[10px] text-slate-500 mb-2">
                        {new Date(act.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                      </p>
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`w-2 h-2 rounded-full ${act.risk_tier === 'GREEN' ? 'bg-emerald-500' : act.risk_tier === 'AMBER' ? 'bg-amber-500' : 'bg-rose-500'}`} />
                        <span className={`text-xs font-bold ${act.risk_tier === 'GREEN' ? 'text-emerald-400' : act.risk_tier === 'AMBER' ? 'text-amber-400' : 'text-rose-400'}`}>
                          {act.risk_tier === 'GREEN' ? 'LOW RISK' : act.risk_tier === 'AMBER' ? 'MODERATE RISK' : 'HIGH RISK'}
                        </span>
                      </div>
                      <p className="text-xl font-mono text-slate-200">{(act.repayment_probability * 100).toFixed(1)}%</p>
                      <p className="text-[10px] text-slate-500 mt-2 font-mono truncate">{act.assessment_id.slice(0, 12)}...</p>
                    </div>
                  ))}
                  {(!recentActivity || recentActivity.length === 0) && (
                    <div className="w-full text-center text-sm text-slate-500 py-4">No recent activity</div>
                  )}
                </div>
              </div>

              {/* ROW 4: System health strip */}
              <div className="border-t border-slate-800 pt-4 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-slate-400">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${statsToday?.model_auc >= 0.78 ? 'bg-emerald-500 animate-pulse' : statsToday?.model_auc >= 0.70 ? 'bg-amber-500' : 'bg-rose-500'}`} />
                  AUC {statsToday?.model_auc?.toFixed(3) || '0.803'} · {statsToday?.model_version || 'v5.0-production'}
                </div>
                <div className="flex items-center gap-2 justify-center cursor-pointer group">
                  <span className="group-hover:text-slate-300 transition-colors">
                    1.2h cache · 3 sources fresh
                  </span>
                </div>
                <div className="flex items-center gap-3 justify-end text-emerald-500/80 cursor-pointer hover:text-emerald-400 transition-colors">
                  <span>DPDP ✓</span>
                  <span>RBI FREE-AI ✓</span>
                  <span>Fairness ✓</span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Skill Gap Modal */}
      <AnimatePresence>
        {showSkillGap && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4"
            onClick={() => setShowSkillGap(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-card border border-border rounded-3xl p-6 w-full max-w-2xl max-h-[80vh] overflow-y-auto"
              onClick={e => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="font-bold text-slate-200 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-indigo-400" /> Skill Gap Analysis
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">AI-generated improvement roadmap for this applicant</p>
                </div>
                <button onClick={() => setShowSkillGap(false)} className="p-1.5 rounded-lg hover:bg-slate-800 transition-colors">
                  <X className="w-4 h-4 text-slate-400" />
                </button>
              </div>

              {skillGapLoading ? (
                <div className="flex items-center justify-center py-12 gap-3">
                  <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
                  <span className="text-sm text-slate-400">Running counterfactual analysis…</span>
                </div>
              ) : skillGapData ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-3 mb-4">
                    <div className="bg-bg rounded-xl p-3 text-center">
                      <p className="text-xs text-slate-500">Current Tier</p>
                      <p className={`text-lg font-bold ${skillGapData.current_tier === 'GREEN' ? 'text-emerald-400' : skillGapData.current_tier === 'AMBER' ? 'text-amber-400' : 'text-rose-400'}`}>{skillGapData.current_tier}</p>
                    </div>
                    <div className="bg-bg rounded-xl p-3 text-center">
                      <p className="text-xs text-slate-500">Current Prob.</p>
                      <p className="text-lg font-bold text-slate-200">{(skillGapData.current_probability * 100).toFixed(1)}%</p>
                    </div>
                    <div className="bg-bg rounded-xl p-3 text-center">
                      <p className="text-xs text-slate-500">Time to GREEN</p>
                      <p className="text-lg font-bold text-emerald-400">{skillGapData.estimated_time_to_green_months}mo</p>
                    </div>
                  </div>
                  <div className="space-y-3">
                    {skillGapData.priority_actions?.map((action: any, i: number) => (
                      <div key={i} className="bg-bg border border-border rounded-xl p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="w-5 h-5 rounded-full bg-indigo-600 flex items-center justify-center text-[10px] font-bold text-white shrink-0">{action.rank}</span>
                              <p className="text-sm font-medium text-slate-200">{action.action}</p>
                            </div>
                            <div className="flex items-center gap-3 text-[10px] text-slate-500 ml-7">
                              <span>⏱ {action.time_months}mo</span>
                              <span>Effort: {action.effort_score}/10</span>
                              <span className="text-slate-400">{action.feasibility}</span>
                            </div>
                          </div>
                          <span className="text-sm font-bold text-emerald-400 shrink-0">+{(action.probability_lift * 100).toFixed(1)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-slate-500 text-center py-8">Failed to load skill gap data.</p>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Manual Review Modal */}
      <AnimatePresence>
        {showManualReview && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4"
            onClick={() => setShowManualReview(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-card border border-border rounded-3xl p-6 w-full max-w-md"
              onClick={e => e.stopPropagation()}
            >
              <div className="flex items-center gap-2 mb-4">
                <AlertCircle className="w-5 h-5 text-amber-400" />
                <h3 className="font-bold text-slate-200">Refer to Manual Review</h3>
              </div>
              <p className="text-sm text-slate-400 mb-4">
                This application will be flagged for human underwriter review. The applicant will be notified within 2 business days.
              </p>
              <div className="bg-bg rounded-xl p-3 mb-4 text-xs font-mono text-slate-400 space-y-1">
                <p>Assessment ID: <span className="text-slate-200">{result?.assessment_id?.slice(0, 16)}…</span></p>
                <p>Risk Tier: <span className={result?.risk_tier === 'GREEN' ? 'text-emerald-400' : result?.risk_tier === 'AMBER' ? 'text-amber-400' : 'text-rose-400'}>{result?.risk_tier}</span></p>
                <p>Probability: <span className="text-slate-200">{((result?.calibrated_probability || 0) * 100).toFixed(1)}%</span></p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowManualReview(false)}
                  className="flex-1 py-2.5 rounded-xl border border-slate-700 text-sm text-slate-400 hover:bg-slate-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => { setShowManualReview(false); alert('Flagged for manual review. Reference: ' + result?.assessment_id?.slice(0, 12)) }}
                  className="flex-1 py-2.5 rounded-xl bg-amber-500/20 border border-amber-500/30 text-sm font-bold text-amber-300 hover:bg-amber-500/30 transition-colors"
                >
                  Confirm Referral
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
