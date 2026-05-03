import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ChevronLeft, AlertTriangle, Loader2, ShieldCheck, XCircle,
  Banknote, Users, BarChart3, TrendingUp, CheckCircle2, ExternalLink,
  Sparkles, Clock, Share2, Download, Zap,
} from 'lucide-react'
import * as Tooltip from '@radix-ui/react-tooltip'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery } from '@tanstack/react-query'
import { StudentProfileSchema, type StudentProfile, FIELDS } from '@/api/types'
import { useStudentSession } from '@/hooks/useStudentSession'
import { useStudentAssess } from '@/hooks/useStudentAssess'
import { apiClient } from '@/api/client'
import WhatIfSimulator from '@/components/WhatIfSimulator'
import PsychometricQuiz from '@/components/PsychometricQuiz'
import LoanScenariosCard from '@/components/LoanScenariosCard'
import { downloadAssessmentCertificate } from '@/components/AssessmentCertificate'

// Frontend-side NPTEL lookup for DEFAULT_ACTIONS fallback
const NPTEL_TOP_BY_FIELD: Record<string, { name: string; url: string; institute: string }> = {
  computer_science:       { name: 'Programming in Python',                           url: 'https://nptel.ac.in/courses/106106145', institute: 'IIT Madras' },
  data_science:           { name: 'Machine Learning for Engineering & Science',       url: 'https://nptel.ac.in/courses/106106198', institute: 'IIT Madras' },
  mba_finance:            { name: 'Financial Management',                             url: 'https://nptel.ac.in/courses/110104073', institute: 'IIT Kharagpur' },
  mechanical_engineering: { name: 'Fluid Mechanics',                                  url: 'https://nptel.ac.in/courses/112105174', institute: 'IIT Madras' },
  electrical_engineering: { name: 'Embedded Systems',                                 url: 'https://nptel.ac.in/courses/108101091', institute: 'IIT Kharagpur' },
  civil_engineering:      { name: 'Structural Analysis',                              url: 'https://nptel.ac.in/courses/105106051', institute: 'IIT Madras' },
  biotechnology:          { name: 'Molecular Biology',                                url: 'https://nptel.ac.in/courses/102106067', institute: 'IIT Madras' },
}

const FIELD_LABELS: Record<string, string> = {
  computer_science:       'Computer Science / IT',
  data_science:           'Data Science / AI',
  mba_finance:            'MBA Finance',
  mechanical_engineering: 'Mechanical Engineering',
  electrical_engineering: 'Electrical Engineering',
  civil_engineering:      'Civil Engineering',
  biotechnology:          'Biotechnology',
}

// Profile Strength tiers
function getStrengthTier(prob: number) {
  if (prob >= 0.80) return { label: 'Platinum', color: '#e2e8f0', bg: 'rgba(226,232,240,0.08)', border: 'rgba(226,232,240,0.25)' }
  if (prob >= 0.65) return { label: 'Gold',     color: '#ffd700', bg: 'rgba(255,215,0,0.08)',   border: 'rgba(255,215,0,0.25)' }
  if (prob >= 0.50) return { label: 'Silver',   color: '#94a3b8', bg: 'rgba(148,163,184,0.08)', border: 'rgba(148,163,184,0.25)' }
  return               { label: 'Bronze',   color: '#cd7f32', bg: 'rgba(205,127,50,0.08)',  border: 'rgba(205,127,50,0.25)' }
}

export default function StudentPortal() {
  const navigate = useNavigate()
  const { isReady } = useStudentSession()
  const { mutate: assess, data: result, isPending, error, reset } = useStudentAssess()

  const { register, handleSubmit, formState: { errors }, getValues, setValue } = useForm<StudentProfile>({
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
    },
  })

  const onSubmit = (data: StudentProfile) => assess(data)

  // Used by WhatIfSimulator "Reassess with these values" button
  const handleReassess = (overrides: Partial<StudentProfile>) => {
    const merged: StudentProfile = { ...getValues(), ...overrides }
    // Update form fields so a subsequent manual submit also uses new values
    Object.entries(overrides).forEach(([k, v]) => setValue(k as keyof StudentProfile, v as any))
    assess(merged)
    // Scroll back to top of results
    window.scrollTo({ top: 0, behavior: 'smooth' })
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
            <button
              onClick={() => navigate('/')}
              className="p-1.5 rounded-lg hover:bg-card-2 transition-colors"
              aria-label="Back"
            >
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
                <h1 className="text-2xl font-bold text-slate-100 mb-2">
                  Understand your risk profile before you borrow.
                </h1>
                <p className="text-sm text-slate-400">
                  Self-reported data. Results are indicative, not a credit decision.
                </p>
              </div>

              {error && (
                <div className="mb-6 p-4 bg-red-dim border border-red/20 rounded-xl flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-red shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-red-text">
                      Assessment unavailable. Please try again in a moment.
                    </p>
                    <button onClick={reset} className="mt-2 text-xs text-red hover:underline">
                      Try again
                    </button>
                  </div>
                </div>
              )}

              <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 bg-card border border-border p-6 rounded-3xl">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-2">
                      CGPA (0–10)
                    </label>
                    <input
                      type="number" step="0.1"
                      {...register('cgpa', { valueAsNumber: true })}
                      className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue focus:ring-1 focus:ring-blue transition-all"
                    />
                    {errors.cgpa && <p className="text-xs text-red mt-1">{errors.cgpa.message}</p>}
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-2">
                      Field of Study
                    </label>
                    <select
                      {...register('field_of_study')}
                      className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue focus:ring-1 focus:ring-blue transition-all appearance-none"
                    >
                      <option value="">Select a field…</option>
                      {FIELDS.map(f => (
                        <option key={f} value={f}>{FIELD_LABELS[f]}</option>
                      ))}
                    </select>
                    {errors.field_of_study && (
                      <p className="text-xs text-red mt-1">{errors.field_of_study.message}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-2">
                      Internships
                    </label>
                    <input
                      type="number"
                      {...register('internships_count', { valueAsNumber: true })}
                      className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue transition-all"
                    />
                    {errors.internships_count && (
                      <p className="text-xs text-red mt-1">{errors.internships_count.message}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-2">
                      Backlogs
                    </label>
                    <input
                      type="number"
                      {...register('backlogs', { valueAsNumber: true })}
                      className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue transition-all"
                    />
                    {errors.backlogs && (
                      <p className="text-xs text-red mt-1">{errors.backlogs.message}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-2">
                      College Placement Rate (%)
                    </label>
                    <input
                      type="number"
                      {...register('college_placement_rate', { valueAsNumber: true })}
                      className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue transition-all"
                    />
                    {errors.college_placement_rate && (
                      <p className="text-xs text-red mt-1">{errors.college_placement_rate.message}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-2">
                      Loan Amount (INR)
                    </label>
                    <input
                      type="number"
                      {...register('loan_amount_inr', { valueAsNumber: true })}
                      className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue transition-all"
                    />
                    {errors.loan_amount_inr && (
                      <p className="text-xs text-red mt-1">{errors.loan_amount_inr.message}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-2">
                      Annual Family Income (INR){' '}
                      <span className="text-slate-600 lowercase font-normal ml-1">(Optional)</span>
                    </label>
                    <input
                      type="number"
                      {...register('annual_family_income_inr', {
                        setValueAs: v => v === '' ? undefined : Number(v),
                      })}
                      className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue transition-all"
                    />
                  </div>
                </div>

                <div className="pt-4 border-t border-border flex items-start gap-3">
                  <input type="checkbox" id="consent" {...register('has_consent')} className="mt-1" />
                  <label htmlFor="consent" className="text-xs text-slate-400 leading-relaxed">
                    I consent to my self-reported data being used to generate this indicative assessment
                    under DPDP Act 2023. No data is stored beyond this session.
                  </label>
                </div>
                {errors.has_consent && (
                  <p className="text-xs text-red">{errors.has_consent.message}</p>
                )}

                <div className="pt-4">
                  <button
                    type="submit"
                    disabled={isPending}
                    className="w-full sm:w-auto px-6 py-3 bg-blue hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-bold rounded-xl transition-colors flex items-center justify-center gap-2"
                  >
                    {isPending ? (
                      <><Loader2 className="w-4 h-4 animate-spin" /> Analysing your profile…</>
                    ) : 'Assess My Profile'}
                  </button>
                </div>
              </form>
            </motion.div>
          )}

          {result && (
            <ResultPanel
              result={result}
              reset={reset}
              profile={getValues()}
              reassess={handleReassess}
            />
          )}
        </AnimatePresence>
      </main>
    </div>
  )
}

// ─── Result Panel ─────────────────────────────────────────────────────────────

interface ResultPanelProps {
  result: any
  reset: () => void
  profile: any
  reassess: (overrides: any) => void
}

function ResultPanel({ result, reset, profile, reassess }: ResultPanelProps) {
  const prob = result.repayment_probability ?? result.calibrated_probability ?? 0.5
  const prob_pct = Math.round(prob * 100)
  const confidence_lower = result.confidence_lower ?? result.confidence_interval_90pct?.lower ?? 0
  const confidence_upper = result.confidence_upper ?? result.confidence_interval_90pct?.upper ?? 1

  const emi_monthly = profile.loan_amount_inr * 0.01349
  const dti = profile.annual_family_income_inr
    ? (emi_monthly * 12) / profile.annual_family_income_inr
    : null
  const peer_pct = Math.round((result.potential_score || 0) * 100)
  const field_demand_pct = Math.round((profile.college_placement_rate || 0) * 100)
  const demand_proxy = profile.college_placement_rate ? profile.college_placement_rate / 100 : 0.5

  const { data: skillGap, isLoading: skillGapLoading } = useQuery({
    queryKey: ['skillGap', profile],
    queryFn: async () => {
      const payload = {
        ...profile,
        user_hash: sessionStorage.getItem('ep_student_hash') || 'anonymous',
      }
      const res = await apiClient.post('/student/skill-gap', payload)
      return res.data
    },
    staleTime: 5 * 60 * 1000,
    retry: 1,
  })

  const fieldNptel = NPTEL_TOP_BY_FIELD[profile.field_of_study] ?? NPTEL_TOP_BY_FIELD['computer_science']

  const skillActions = skillGap?.priority_actions?.slice(0, 3).map((a: any) => ({
    priority_i: a.rank,
    action: a.action,
    time_estimate: `~${a.time_months} month${a.time_months !== 1 ? 's' : ''}`,
    effort_score: a.effort_score,
    probability_lift: a.probability_lift,
    resource_url: a.resources?.[0] ?? undefined,
    resource_label: a.resources?.[0]
      ? a.resources[0].replace(/^https?:\/\//, '').split('/')[0]
      : 'Resource',
  })) ?? null

  const tier = result.risk_tier
  const tierColor = tier === 'GREEN' ? '#22c55e' : tier === 'AMBER' ? '#f59e0b' : '#ef4444'
  const tierFilter =
    tier === 'GREEN' ? 'drop-shadow(0 0 8px #22c55e80)' :
    tier === 'AMBER' ? 'drop-shadow(0 0 8px #f59e0b80)' :
    'drop-shadow(0 0 8px #ef444480)'
  const badgeLabel = tier === 'GREEN' ? 'LOW RISK' : tier === 'AMBER' ? 'MODERATE' : 'HIGH RISK'

  const r = 100, cx = 110, cy = 120
  const circumference = Math.PI * r
  const [dashoffset, setDashoffset] = useState(circumference)

  useEffect(() => {
    const t = setTimeout(() => setDashoffset(circumference * (1 - prob)), 100)
    return () => clearTimeout(t)
  }, [prob, circumference])

  const factors = [
    { label: 'Academic Score',  value: profile.cgpa / 10 },
    { label: 'Practical Exp.',  value: Math.min(profile.internships_count / 3, 1) },
    { label: 'Field Placement', value: (profile.college_placement_rate || 0) / 100 },
    { label: 'Market Demand',   value: demand_proxy },
  ]

  const Icon = tier === 'GREEN' ? ShieldCheck : tier === 'AMBER' ? AlertTriangle : XCircle

  const timelineMonths =
    skillGap?.estimated_time_to_green_months ??
    (skillActions?.reduce((acc: number, a: any) => acc + (parseInt(a.time_estimate) || 1), 0) ?? 6)

  const milestones = (skillActions || []).slice(0, 3).map(
    (a: any, i: number) => ({
      label: a.action.split(' ').slice(0, 4).join(' ') + (a.action.split(' ').length > 4 ? '…' : ''),
      month: (i + 1) * Math.round(timelineMonths / 3),
    }),
  )

  const strength = getStrengthTier(prob)

  const handleShareWhatsApp = () => {
    const msg = encodeURIComponent(
      `I just checked my student loan profile on EduPredict AI.\n` +
      `Repayment likelihood: ${prob_pct}% (${badgeLabel})\n` +
      `Assessment ID: ${result.assessment_id.slice(0, 8)}\n` +
      `Note: Indicative only, not a credit decision.`,
    )
    window.open(`https://wa.me/?text=${msg}`, '_blank', 'noopener,noreferrer')
  }

  const handleDownloadCert = () => {
    downloadAssessmentCertificate({
      assessmentId: result.assessment_id,
      repaymentProbability: prob,
      riskTier: tier,
      confidenceLower: confidence_lower,
      confidenceUpper: confidence_upper,
      cgpa: profile.cgpa,
      fieldOfStudy: profile.field_of_study,
      loanAmountInr: profile.loan_amount_inr,
      timestamp: result.timestamp,
      modelVersion: result.model_version ?? 'v5.0',
    })
  }

  return (
    <div className="flex flex-col gap-4">

      {/* Backlog alert */}
      {profile.backlogs > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full bg-amber-500/10 border border-amber-500/30 rounded-2xl p-4 flex items-start gap-3"
        >
          <AlertTriangle size={18} className="text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-amber-300">
              {profile.backlogs === 1
                ? 'You have 1 unresolved backlog'
                : `You have ${profile.backlogs} unresolved backlogs`}
            </p>
            <p className="text-xs text-amber-400/80 mt-1">
              Most Indian banks and NBFCs treat backlogs as the primary academic risk signal.
              Clearing {profile.backlogs === 1 ? 'it' : 'them'} before applying improves your
              approval odds significantly.
              {profile.backlogs >= 5 &&
                ' With 5+ backlogs, most public sector banks will require written justification and a strong co-applicant.'}
            </p>
          </div>
        </motion.div>
      )}

      {/* ROW 1 — Hero score strip */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col md:flex-row items-center w-full gap-6"
      >
        {/* Gauge — 40% */}
        <div className="w-full md:w-[40%] flex flex-col items-center justify-center relative">
          <svg width="220" height="130" viewBox="0 0 220 130" style={{ filter: tierFilter }}>
            <defs>
              <linearGradient id="gauge-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                {tier === 'GREEN' && (
                  <><stop offset="0%" stopColor="#16a34a" /><stop offset="100%" stopColor="#4ade80" /></>
                )}
                {tier === 'AMBER' && (
                  <><stop offset="0%" stopColor="#d97706" /><stop offset="100%" stopColor="#fbbf24" /></>
                )}
                {tier === 'RED' && (
                  <><stop offset="0%" stopColor="#dc2626" /><stop offset="100%" stopColor="#f87171" /></>
                )}
              </linearGradient>
            </defs>
            <path
              d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
              fill="none" stroke="#1e293b" strokeWidth="18" strokeLinecap="round"
            />
            <path
              d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
              fill="none" stroke="url(#gauge-gradient)" strokeWidth="18" strokeLinecap="round"
              strokeDasharray={circumference} strokeDashoffset={dashoffset}
              style={{ transition: 'stroke-dashoffset 1.2s ease-out 0.3s' }}
            />
          </svg>
          <div className="absolute top-[50px] flex flex-col items-center">
            <span style={{ fontSize: '44px', fontWeight: 700, color: tierColor, lineHeight: 1 }}>
              {prob_pct}%
            </span>
            <span className="text-slate-400" style={{ fontSize: '11px' }}>repayment likelihood</span>
            <span
              className="mt-2 text-white px-2 py-0.5 rounded-full"
              style={{ fontSize: '10px', backgroundColor: tierColor, textTransform: 'uppercase' }}
            >
              {badgeLabel}
            </span>
          </div>
        </div>

        {/* Confidence band — 30% */}
        <div className="w-full md:w-[30%] flex flex-col justify-center">
          <span className="text-slate-400 uppercase mb-2" style={{ fontSize: '11px' }}>
            90% Confidence Band
          </span>
          <div className="w-full h-[56px] bg-slate-800/50 rounded-xl relative flex items-center">
            <div
              className="absolute h-full rounded-xl flex items-center justify-between px-2"
              style={{
                left: `${confidence_lower * 100}%`,
                width: `${(confidence_upper - confidence_lower) * 100}%`,
                backgroundColor: `${tierColor}4d`,
                border: `1px solid ${tierColor}b3`,
              }}
            >
              <span className="text-white text-xs font-medium">
                {(confidence_lower * 100).toFixed(1)}%
              </span>
              <span className="text-white text-xs font-medium">
                {(confidence_upper * 100).toFixed(1)}%
              </span>
            </div>
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-white z-10"
              style={{ left: `${prob * 100}%` }}
            />
          </div>
          <span className="text-slate-500 mt-2" style={{ fontSize: '10px' }}>
            Distribution-free conformal guarantee · α = 0.10
          </span>
        </div>

        {/* Right panel — 30% */}
        <div className="w-full md:w-[30%] flex flex-col justify-center gap-2">
          <div className="flex items-center gap-2">
            <Icon size={20} color={tierColor} />
            <span className="font-semibold text-white" style={{ fontSize: '14px' }}>
              {tier === 'GREEN'
                ? 'Strong repayment profile'
                : tier === 'AMBER'
                ? 'Moderate repayment profile'
                : 'Elevated repayment risk'}
            </span>
          </div>
          <p className="text-slate-300 line-clamp-3" style={{ fontSize: '12px' }}>
            {result.recommendation}
          </p>
          <div className="flex items-center gap-1 mt-1 text-slate-500" style={{ fontSize: '10px' }}>
            {result.fairness_applied ? <CheckCircle2 size={10} /> : null}
            <span>
              {result.fairness_applied ? 'Fairness calibration: applied' : 'Baseline threshold'}
            </span>
          </div>

          {/* Profile Strength Meter */}
          <Tooltip.Provider>
            <Tooltip.Root>
              <Tooltip.Trigger asChild>
                <div
                  className="mt-1 inline-flex items-center gap-1.5 px-3 py-1 rounded-full cursor-default self-start"
                  style={{
                    backgroundColor: strength.bg,
                    border: `1px solid ${strength.border}`,
                  }}
                >
                  <span style={{ color: strength.color, fontSize: '10px' }}>●</span>
                  <span style={{ color: strength.color, fontSize: '10px', fontWeight: 700 }}>
                    {strength.label}
                  </span>
                  <span className="text-[10px] text-slate-400">Profile</span>
                </div>
              </Tooltip.Trigger>
              <Tooltip.Portal>
                <Tooltip.Content
                  className="bg-slate-800 border border-slate-700 text-white text-xs p-3 rounded-xl max-w-xs z-50 shadow-xl"
                  sideOffset={6}
                >
                  <p className="font-semibold mb-2">Profile Strength Tiers</p>
                  <div className="space-y-1 text-[11px] text-slate-300">
                    <p><span style={{ color: '#e2e8f0' }}>● Platinum</span> — ≥80% repayment probability</p>
                    <p><span style={{ color: '#ffd700' }}>● Gold</span>     — 65–80% repayment probability</p>
                    <p><span style={{ color: '#94a3b8' }}>● Silver</span>   — 50–65% repayment probability</p>
                    <p><span style={{ color: '#cd7f32' }}>● Bronze</span>   — &lt;50% repayment probability</p>
                  </div>
                  <Tooltip.Arrow className="fill-slate-800" />
                </Tooltip.Content>
              </Tooltip.Portal>
            </Tooltip.Root>
          </Tooltip.Provider>
        </div>
      </motion.div>

      {/* Phase 5A — What-If Simulator */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut', delay: 0.08 }}
      >
        <WhatIfSimulator
          originalProb={prob}
          shapContributions={result.shap_contributions}
          profile={{
            cgpa: profile.cgpa,
            internships_count: profile.internships_count,
            backlogs: profile.backlogs,
            college_placement_rate: profile.college_placement_rate,
          }}
          onReassess={reassess}
        />
      </motion.div>

      {/* ROW 2 — Three metric cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: 'easeOut', delay: 0.10 }}
          className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3"
        >
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <Banknote size={16} className="text-slate-400" />
            Loan Feasibility
          </div>
          <div>
            <div style={{ fontSize: '24px', fontWeight: 600, color: 'white' }}>
              ₹{emi_monthly.toLocaleString('en-IN', { maximumFractionDigits: 0 })} /mo
            </div>
            <div className="text-slate-400" style={{ fontSize: '11px' }}>
              Est. monthly EMI (10.5% p.a. · 10yr)
            </div>
          </div>
          {dti !== null ? (
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-slate-400" style={{ fontSize: '11px' }}>
                  Debt-to-income ratio
                </span>
                <span
                  className="font-medium"
                  style={{
                    fontSize: '11px',
                    color: dti < 0.30 ? '#22c55e' : dti < 0.50 ? '#f59e0b' : '#ef4444',
                  }}
                >
                  {(dti * 100).toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${Math.min(dti * 100, 100)}%`,
                    backgroundColor: dti < 0.30 ? '#22c55e' : dti < 0.50 ? '#f59e0b' : '#ef4444',
                  }}
                />
              </div>
            </div>
          ) : (
            <div className="text-slate-500 italic" style={{ fontSize: '11px' }}>
              Add family income for DTI analysis
            </div>
          )}
          <div className="pt-2 border-t border-slate-800 text-xs text-slate-300">
            {tier === 'GREEN'
              ? 'Loan appears serviceable'
              : tier === 'AMBER'
              ? 'Manageable with income growth'
              : 'High debt burden risk'}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: 'easeOut', delay: 0.18 }}
          className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3"
        >
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <Users size={16} className="text-slate-400" />
            Your Standing
          </div>
          <div>
            <div style={{ fontSize: '28px', fontWeight: 700, color: tierColor }}>
              Top {100 - peer_pct}%
            </div>
            <div className="text-slate-400" style={{ fontSize: '11px' }}>
              vs students in {FIELD_LABELS[profile.field_of_study] ?? profile.field_of_study}
            </div>
          </div>
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-slate-400" style={{ fontSize: '11px' }}>Field job demand</span>
              <span
                className="font-medium"
                style={{
                  fontSize: '11px',
                  color: field_demand_pct > 60 ? '#22c55e' : field_demand_pct > 40 ? '#f59e0b' : '#ef4444',
                }}
              >
                {field_demand_pct}%
              </span>
            </div>
            <div className="w-full bg-slate-800 h-[6px] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${field_demand_pct}%`,
                  backgroundColor:
                    field_demand_pct > 60 ? '#22c55e' : field_demand_pct > 40 ? '#f59e0b' : '#ef4444',
                }}
              />
            </div>
          </div>
          <div
            className="pt-2 border-t border-slate-800"
            style={{
              fontSize: '11px',
              color:
                profile.internships_count === 0
                  ? '#ef4444'
                  : profile.internships_count === 1
                  ? '#f59e0b'
                  : '#22c55e',
            }}
          >
            {profile.internships_count === 0
              ? 'No internships detected — high impact gap'
              : profile.internships_count === 1
              ? '1 internship — consider a second'
              : `${profile.internships_count} internships — above average`}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: 'easeOut', delay: 0.26 }}
          className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3"
        >
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <BarChart3 size={16} className="text-slate-400" />
            Key Factors
          </div>
          <div className="space-y-2.5 flex-1">
            {factors.map((f, i) => (
              <div key={i}>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-slate-400" style={{ fontSize: '11px' }}>{f.label}</span>
                  <span className="font-medium" style={{ fontSize: '10px' }}>
                    {Math.round(f.value * 100)}%
                  </span>
                </div>
                <div className="w-full bg-slate-800 h-[5px] rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(f.value * 100, 100)}%` }}
                    transition={{ duration: 0.8, delay: 0.4 + i * 0.1 }}
                    className="h-full rounded-full"
                    style={{
                      backgroundColor:
                        f.value > 0.65 ? '#22c55e' : f.value > 0.40 ? '#f59e0b' : '#ef4444',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Phase 5C — Loan Scenario Comparison */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut', delay: 0.30 }}
      >
        <LoanScenariosCard profile={profile} />
      </motion.div>

      {/* ROW 3 — Skill Roadmap */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut', delay: 0.34 }}
        className="w-full relative"
      >
        <div className="mb-3 flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <TrendingUp size={16} className="text-slate-400" />
              Personalised Skill Roadmap
              {skillGapLoading && <Loader2 size={12} className="animate-spin text-slate-500" />}
              {skillGap && !skillGapLoading && (
                <span className="text-[10px] font-normal text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <Sparkles size={10} /> AI-generated
                </span>
              )}
            </div>
            <div className="text-slate-400" style={{ fontSize: '11px' }}>
              {skillGap
                ? `Estimated time to GREEN tier: ${skillGap.estimated_time_to_green_months} months · Actions ranked by probability lift`
                : 'Actions ranked by impact on your repayment profile'}
            </div>
          </div>
        </div>

        <div
          className="flex flex-nowrap overflow-x-auto gap-4 pb-4 w-full relative"
          style={{ scrollbarWidth: 'none' }}
        >
          {(skillActions || [
            {
              priority_i: 1,
              action: `Complete NPTEL: ${fieldNptel.name} (${fieldNptel.institute})`,
              time_estimate: '~3 months',
              effort_score: 4,
              probability_lift: 0.05,
              resource_url: fieldNptel.url,
              resource_label: 'NPTEL',
            },
            {
              priority_i: 2,
              action: 'Build 2 portfolio projects on GitHub',
              time_estimate: '~2 months',
              effort_score: 5,
              probability_lift: 0.05,
              resource_url: 'https://kaggle.com',
              resource_label: 'Kaggle',
            },
            {
              priority_i: 3,
              action: 'Complete 1 more internship',
              time_estimate: '~3 months',
              effort_score: 7,
              probability_lift: 0.08,
              resource_url: 'https://internshala.com',
              resource_label: 'Internshala',
            },
          ]).map((action: any, idx: number) => (
            <div
              key={idx}
              className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shrink-0 min-w-[240px] flex flex-col justify-between hover:border-slate-600 transition-colors"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div
                    className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-slate-900"
                    style={{ backgroundColor: tierColor }}
                  >
                    {action.priority_i}
                  </div>
                  <div className="flex items-center gap-1 text-[10px] text-emerald-400 font-medium">
                    <TrendingUp size={12} />
                    +{(action.probability_lift * 100).toFixed(1)}%
                  </div>
                </div>
                <h3 className="text-[13px] font-medium text-slate-200 leading-snug mb-1">
                  {action.action}
                </h3>
                <span className="text-[10px] text-slate-500 bg-slate-800 px-2 py-0.5 rounded-md">
                  {action.time_estimate}
                </span>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between">
                <span className="text-[10px] text-slate-500">Effort: {action.effort_score}/10</span>
                {action.resource_url && (
                  <a
                    href={action.resource_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-[10px] text-blue-400 hover:underline"
                  >
                    {action.resource_label || 'Link'} <ExternalLink size={10} />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
        <div className="absolute right-0 top-0 bottom-0 w-16 bg-gradient-to-l from-[#0a0f1e] to-transparent pointer-events-none" />
      </motion.div>

      {/* Feature 4 — Timeline to GREEN */}
      {tier !== 'GREEN' && skillActions && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: 'easeOut', delay: 0.40 }}
          className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-5"
        >
          <div className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <Clock size={14} className="text-slate-400" />
            Your path to GREEN
            <span className="text-xs font-normal text-emerald-400 ml-2">
              ~{timelineMonths} months
            </span>
          </div>
          <div className="relative flex items-center">
            <div className="absolute left-0 right-0 h-0.5 bg-slate-700 top-3" />
            <div className="relative flex flex-col items-center mr-8">
              <div className="w-3 h-3 rounded-full bg-slate-600 border-2 border-slate-500 z-10" />
              <span className="text-[10px] text-slate-500 mt-2">Now</span>
              <span className="text-[9px]" style={{ color: tierColor }}>{badgeLabel}</span>
            </div>
            {milestones.map((m: { label: string; month: number }, i: number) => (
              <div key={i} className="relative flex flex-col items-center mx-auto">
                <div
                  className="w-3 h-3 rounded-full z-10"
                  style={{ backgroundColor: tierColor, opacity: 0.6 + i * 0.2 }}
                />
                <span className="text-[9px] text-slate-500 mt-2 text-center max-w-[70px]">
                  {m.label}
                </span>
                <span className="text-[9px] text-slate-600">Mo. {m.month}</span>
              </div>
            ))}
            <div className="relative flex flex-col items-center ml-auto">
              <div className="w-4 h-4 rounded-full bg-emerald-500 z-10 flex items-center justify-center">
                <CheckCircle2 size={10} className="text-white" />
              </div>
              <span className="text-[10px] text-emerald-400 mt-2">GREEN</span>
              <span className="text-[9px] text-slate-500">Mo. {timelineMonths}</span>
            </div>
          </div>
        </motion.div>
      )}

      {/* Feature 3 — Gen Z Advantage */}
      {(tier === 'AMBER' || tier === 'RED') && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: 'easeOut', delay: 0.50 }}
          className="w-full bg-gradient-to-r from-indigo-500/10 to-blue-500/10 border border-indigo-500/20 rounded-2xl p-5"
        >
          <div className="flex items-start gap-3">
            <Zap size={20} className="text-indigo-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-semibold text-indigo-300 mb-1">Your Gen Z Advantage</p>
              <p className="text-xs text-slate-400 leading-relaxed mb-3">
                57% of Indian Gen Z are already choosing skills over salary. Lenders are beginning
                to recognise certifications, freelance work, and side projects as income signals —
                not just CGPA.
              </p>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: 'Upskilling weekly', value: '85%', note: 'of Gen Z in India' },
                  { label: 'Freelance + job',   value: '43%', note: 'prefer hybrid income' },
                  { label: 'Career optimism',   value: '77%', note: 'net positive outlook' },
                ].map((stat, i) => (
                  <div key={i} className="bg-indigo-500/10 rounded-xl p-3 text-center">
                    <p className="text-lg font-bold text-indigo-300">{stat.value}</p>
                    <p className="text-[10px] text-slate-400 mt-0.5">{stat.label}</p>
                    <p className="text-[9px] text-slate-500">{stat.note}</p>
                  </div>
                ))}
              </div>
              <p className="text-[10px] text-slate-500 mt-3 italic">
                Source: Deloitte Global Gen Z & Millennial Survey India 2025 · Naukri Skills Report 2025–26
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Phase 5B — Psychometric Assessment */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut', delay: 0.55 }}
      >
        <PsychometricQuiz baseProb={prob} />
      </motion.div>

      {/* ROW 4 — Action strip */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut', delay: 0.60 }}
        className="w-full pt-4 border-t border-slate-800 flex flex-col md:flex-row items-center justify-between gap-4"
      >
        <div className="font-mono text-slate-500" style={{ fontSize: '11px' }}>
          Assessment ID: {result.assessment_id.slice(0, 16)}…
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* WhatsApp share */}
          <button
            onClick={handleShareWhatsApp}
            className="flex items-center gap-1.5 px-3 py-2 bg-green-600/20 border border-green-600/30 hover:bg-green-600/30 text-green-400 text-xs font-medium rounded-xl transition-colors"
          >
            <Share2 size={12} />
            Share via WhatsApp
          </button>

          {/* Certificate download */}
          <button
            onClick={handleDownloadCert}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-700/50 border border-slate-700 hover:border-slate-500 text-slate-300 text-xs font-medium rounded-xl transition-colors"
          >
            <Download size={12} />
            Download Certificate
          </button>

          <button
            onClick={reset}
            className="border border-slate-600 text-slate-300 hover:border-blue-500 hover:text-blue-400 transition-colors rounded-lg px-4 py-2"
            style={{ fontSize: '12px' }}
          >
            Reassess
          </button>
        </div>

        <div className="text-slate-500 italic" style={{ fontSize: '11px' }}>
          Results are indicative. Not a credit decision.
        </div>
      </motion.div>
    </div>
  )
}
