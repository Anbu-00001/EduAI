import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronLeft, AlertTriangle, Loader2, ShieldCheck, XCircle, Banknote, Users, BarChart3, TrendingUp, CheckCircle2, ExternalLink } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { StudentProfileSchema, type StudentProfile, FIELDS } from '@/api/types'
import { useStudentSession } from '@/hooks/useStudentSession'
import { useStudentAssess } from '@/hooks/useStudentAssess'

import SkillRoadmap from '@/components/SkillRoadmap'
import ErrorBoundary from '@/components/ErrorBoundary'
import TemporalWarningBanner from '@/components/TemporalWarningBanner'

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

  const { register, handleSubmit, formState: { errors }, getValues } = useForm<StudentProfile>({
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
            <ResultPanel result={result} reset={reset} profile={getValues()} />
          )}
        </AnimatePresence>
      </main>
    </div>
  )
}

function ResultPanel({ result, reset, profile }: { result: any, reset: () => void, profile: any }) {
  const prob_pct = Math.round(result.calibrated_probability * 100);
  const confidence_lower = result.confidence_interval_90pct.lower;
  const confidence_upper = result.confidence_interval_90pct.upper;
  const emi_monthly = profile.loan_amount_inr * 0.00926;
  const dti = profile.annual_family_income_inr ? (emi_monthly * 12) / profile.annual_family_income_inr : null;
  const peer_pct = Math.round((result.potential_score || 0) * 100);
  const field_demand_pct = Math.round((profile.college_placement_rate || 0) * 100); // proxy if missing from API
  const demand_proxy = profile.college_placement_rate ? profile.college_placement_rate / 100 : 0.5; // proxy

  const tier = result.risk_tier;
  const tierColor = tier === 'GREEN' ? '#22c55e' : tier === 'AMBER' ? '#f59e0b' : '#ef4444';
  const tierFilter = tier === 'GREEN' ? 'drop-shadow(0 0 8px #22c55e80)' : tier === 'AMBER' ? 'drop-shadow(0 0 8px #f59e0b80)' : 'drop-shadow(0 0 8px #ef444480)';
  const badgeLabel = tier === 'GREEN' ? 'LOW RISK' : tier === 'AMBER' ? 'MODERATE' : 'HIGH RISK';

  const r = 100;
  const cx = 110;
  const cy = 120;
  const circumference = Math.PI * r;
  const [dashoffset, setDashoffset] = useState(circumference);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDashoffset(circumference * (1 - result.calibrated_probability));
    }, 100);
    return () => clearTimeout(timer);
  }, [result.calibrated_probability, circumference]);

  const factors = [
    { label: "Academic Score", value: profile.cgpa / 10 },
    { label: "Practical Exp.", value: Math.min(profile.internships_count / 3, 1) },
    { label: "Field Placement", value: (profile.college_placement_rate || 0) / 100 },
    { label: "Market Demand", value: demand_proxy },
  ];

  const Icon = tier === 'GREEN' ? ShieldCheck : tier === 'AMBER' ? AlertTriangle : XCircle;

  return (
    <div className="flex flex-col gap-4">
      {/* ROW 1: Hero score strip */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut", delay: 0 }}
        className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col md:flex-row items-center w-full gap-6"
      >
        {/* Left Column (40%) */}
        <div className="w-full md:w-[40%] flex flex-col items-center justify-center relative">
          <svg width="220" height="130" viewBox="0 0 220 130" style={{ filter: tierFilter }}>
            <defs>
              <linearGradient id="gauge-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                {tier === 'GREEN' && <><stop offset="0%" stopColor="#16a34a" /><stop offset="100%" stopColor="#4ade80" /></>}
                {tier === 'AMBER' && <><stop offset="0%" stopColor="#d97706" /><stop offset="100%" stopColor="#fbbf24" /></>}
                {tier === 'RED' && <><stop offset="0%" stopColor="#dc2626" /><stop offset="100%" stopColor="#f87171" /></>}
              </linearGradient>
            </defs>
            <path
              d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
              fill="none"
              stroke="#1e293b"
              strokeWidth="18"
              strokeLinecap="round"
            />
            <path
              d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
              fill="none"
              stroke="url(#gauge-gradient)"
              strokeWidth="18"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={dashoffset}
              style={{ transition: 'stroke-dashoffset 1.2s ease-out 0.3s' }}
            />
          </svg>
          <div className="absolute top-[50px] flex flex-col items-center">
            <span style={{ fontSize: '44px', fontWeight: 700, color: tierColor, lineHeight: 1 }}>{prob_pct}%</span>
            <span className="text-slate-400" style={{ fontSize: '11px' }}>repayment likelihood</span>
            <span className="mt-2 text-white px-2 py-0.5 rounded-full" style={{ fontSize: '10px', backgroundColor: tierColor, textTransform: 'uppercase' }}>
              {badgeLabel}
            </span>
          </div>
        </div>

        {/* Centre Column (30%) */}
        <div className="w-full md:w-[30%] flex flex-col justify-center">
          <span className="text-slate-400 uppercase mb-2" style={{ fontSize: '11px' }}>90% Confidence Band</span>
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
              <span className="text-white text-xs font-medium">{(confidence_lower * 100).toFixed(1)}%</span>
              <span className="text-white text-xs font-medium">{(confidence_upper * 100).toFixed(1)}%</span>
            </div>
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-white group cursor-help z-10"
              style={{ left: `${result.calibrated_probability * 100}%` }}
              title={`Point estimate: ${prob_pct}%`}
            />
          </div>
          <span className="text-slate-500 mt-2" style={{ fontSize: '10px' }}>Distribution-free conformal guarantee · α = 0.10</span>
        </div>

        {/* Right Column (30%) */}
        <div className="w-full md:w-[30%] flex flex-col justify-center gap-2">
          <div className="flex items-center gap-2">
            <Icon size={20} color={tierColor} />
            <span className="font-semibold text-white" style={{ fontSize: '14px' }}>
              {tier === 'GREEN' ? "Strong repayment profile" : tier === 'AMBER' ? "Moderate repayment profile" : "Elevated repayment risk"}
            </span>
          </div>
          <p className="text-slate-300 line-clamp-3" style={{ fontSize: '12px' }}>
            {result.recommendation}
          </p>
          <div className="flex items-center gap-1 mt-1 text-slate-500" style={{ fontSize: '10px' }}>
            {result.fairness_applied ? <CheckCircle2 size={10} /> : null}
            <span>{result.fairness_applied ? "Fairness calibration: applied" : "Baseline threshold"}</span>
          </div>
        </div>
      </motion.div>

      {/* ROW 2: Three metric cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: "easeOut", delay: 0.10 }}
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
            <div className="text-slate-400" style={{ fontSize: '11px' }}>Est. monthly EMI (10.5% p.a. · 10yr)</div>
          </div>
          {dti !== null ? (
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-slate-400" style={{ fontSize: '11px' }}>Debt-to-income ratio</span>
                <span className="font-medium" style={{ fontSize: '11px', color: dti < 0.30 ? '#22c55e' : dti < 0.50 ? '#f59e0b' : '#ef4444' }}>
                  {(dti * 100).toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${Math.min(dti * 100, 100)}%`,
                    backgroundColor: dti < 0.30 ? '#22c55e' : dti < 0.50 ? '#f59e0b' : '#ef4444'
                  }}
                />
              </div>
            </div>
          ) : (
            <div className="text-slate-500 italic" style={{ fontSize: '11px' }}>Add family income for DTI analysis</div>
          )}
          <div className="pt-2 border-t border-slate-800 text-xs text-slate-300">
            {tier === 'GREEN' ? "✓ Loan appears serviceable" : tier === 'AMBER' ? "⚠ Manageable with income growth" : "✗ High debt burden risk"}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: "easeOut", delay: 0.18 }}
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
            <div className="text-slate-400" style={{ fontSize: '11px' }}>vs students in {FIELD_LABELS[profile.field_of_study] || profile.field_of_study}</div>
          </div>
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-slate-400" style={{ fontSize: '11px' }}>Field job demand</span>
              <span className="font-medium" style={{ fontSize: '11px', color: field_demand_pct > 60 ? '#22c55e' : field_demand_pct > 40 ? '#f59e0b' : '#ef4444' }}>
                {field_demand_pct}%
              </span>
            </div>
            <div className="w-full bg-slate-800 h-[6px] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${field_demand_pct}%`,
                  backgroundColor: field_demand_pct > 60 ? '#22c55e' : field_demand_pct > 40 ? '#f59e0b' : '#ef4444'
                }}
              />
            </div>
          </div>
          <div className="pt-2 border-t border-slate-800" style={{ fontSize: '11px', color: profile.internships_count === 0 ? '#ef4444' : profile.internships_count === 1 ? '#f59e0b' : '#22c55e' }}>
            {profile.internships_count === 0 ? "⚠ No internships detected — high impact gap" : profile.internships_count === 1 ? "1 internship — consider a second" : `${profile.internships_count} internships — above average`}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: "easeOut", delay: 0.26 }}
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
                    transition={{ duration: 0.8, delay: 0.4 + (i * 0.1) }}
                    className="h-full rounded-full"
                    style={{ backgroundColor: f.value > 0.65 ? '#22c55e' : f.value > 0.40 ? '#f59e0b' : '#ef4444' }}
                  />
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* ROW 3: Skill Roadmap */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut", delay: 0.34 }}
        className="w-full relative"
      >
        <div className="mb-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <TrendingUp size={16} className="text-slate-400" />
            Skill Roadmap
          </div>
          <div className="text-slate-400" style={{ fontSize: '11px' }}>Actions ranked by impact on your repayment profile</div>
        </div>
        
        <div className="flex flex-nowrap overflow-x-auto gap-4 pb-4 w-full relative" style={{ scrollbarWidth: 'none' }}>
          {(result.skill_roadmap || [
            { priority_i: 1, action: 'Complete domain certification (NPTEL)', time_estimate: '~1 month', effort_score: 3, probability_lift: 0.03, resource_url: 'https://nptel.ac.in', resource_label: 'NPTEL' },
            { priority_i: 2, action: 'Build 2 portfolio projects on GitHub', time_estimate: '~2 months', effort_score: 5, probability_lift: 0.05, resource_url: 'https://kaggle.com', resource_label: 'Kaggle' },
            { priority_i: 3, action: 'Complete 1 more internship', time_estimate: '~3 months', effort_score: 7, probability_lift: 0.08, resource_url: 'https://internshala.com', resource_label: 'Internshala' }
          ]).map((action: any, idx: number) => (
            <div key={idx} className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shrink-0 min-w-[240px] flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-slate-900" style={{ backgroundColor: tierColor }}>
                    {action.priority_i}
                  </div>
                  <div className="flex items-center gap-1 text-[10px] text-emerald-400 font-medium">
                    <TrendingUp size={12} />
                    +{(action.probability_lift * 100).toFixed(1)}%
                  </div>
                </div>
                <h3 className="text-[13px] font-medium text-slate-200 leading-snug mb-1">{action.action}</h3>
                <span className="text-[10px] text-slate-500 bg-slate-800 px-2 py-0.5 rounded-md">{action.time_estimate}</span>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between">
                <span className="text-[10px] text-slate-500">Effort: {action.effort_score}/10</span>
                {action.resource_url && (
                  <a href={action.resource_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-[10px] text-blue-400 hover:underline">
                    {action.resource_label || 'Link'} <ExternalLink size={10} />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
        <div className="absolute right-0 top-0 bottom-0 w-16 bg-gradient-to-l from-[#0a0f1e] to-transparent pointer-events-none" />
      </motion.div>

      {/* ROW 4: Reassess strip */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut", delay: 0.42 }}
        className="w-full pt-4 border-t border-slate-800 flex flex-col md:flex-row items-center justify-between gap-4"
      >
        <div className="font-mono text-slate-500" style={{ fontSize: '11px' }}>
          Assessment ID: {result.assessment_id.slice(0, 16)}...
        </div>
        <div className="text-slate-500 italic" style={{ fontSize: '11px' }}>
          Results are indicative. Not a credit decision.
        </div>
        <button
          onClick={reset}
          className="border border-slate-600 text-slate-300 hover:border-blue-500 hover:text-blue-400 transition-colors rounded-lg px-4 py-2"
          style={{ fontSize: '12px' }}
        >
          Reassess
        </button>
      </motion.div>
    </div>
  )
}

