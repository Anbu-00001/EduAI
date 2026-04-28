import { useState } from 'react'
import { motion } from 'framer-motion'
import { ChevronLeft, AlertTriangle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import RiskGauge from '@/components/RiskGauge'
import ConformalInterval from '@/components/ConformalInterval'
import SkillRoadmap from '@/components/SkillRoadmap'
import VerifiedBadge from '@/components/VerifiedBadge'
import { formatINR } from '@/lib/utils'

// Demo profile pre-loaded when no JanParichay session
const DEMO_PROFILE = {
  cgpa: 8.4,
  internships_count: 2,
  backlogs: 0,
  field_of_study: 'Computer Science / IT',
  college: 'Anna University',
  degree: 'B.E. Computer Science',
  cgpa_verified: true,
  institution_verified: true,
}

const DEMO_RESULT = {
  calibrated_probability: 0.87,
  risk_tier: 'GREEN' as const,
  confidence_interval_90pct: { lower: 0.81, upper: 0.93 },
  recommendation: 'Strong repayment likelihood. Applicant profile is well above industry median. Loan viable at standard interest rates.',
}

// Build loan ROI chart data
function buildLoanData(loanAmount: number, interestRate: number, tenureYears: number, annualSalary: number) {
  const monthlyRate = interestRate / 12
  const months = tenureYears * 12
  const emi = (loanAmount * monthlyRate * Math.pow(1 + monthlyRate, months)) / (Math.pow(1 + monthlyRate, months) - 1)

  return Array.from({ length: tenureYears + 1 }, (_, year) => {
    const salary = annualSalary * Math.pow(1.08, year) // 8% salary growth
    const yearlyEmi = emi * 12
    return {
      year: `Year ${year}`,
      salary: Math.round(salary / 1000),
      emi: Math.round(yearlyEmi / 1000),
      surplus: Math.round((salary - yearlyEmi) / 1000),
    }
  })
}

export default function StudentPortal() {
  const navigate = useNavigate()
  const [loanAmount, setLoanAmount] = useState(500000)
  const [interestRate, setInterestRate] = useState(0.105)
  const [tenure, setTenure] = useState(7)
  const annualSalary = 700000 // Estimated starting salary for CS grad

  const loanData = buildLoanData(loanAmount, interestRate, tenure, annualSalary)
  const breakEvenYear = loanData.findIndex(d => d.surplus > 0)

  return (
    <div className="min-h-screen bg-bg">
      {/* Header */}
      <header className="border-b border-border sticky top-0 z-20 bg-bg/80 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/')} className="p-1.5 rounded-lg hover:bg-card-2 transition-colors" aria-label="Back">
              <ChevronLeft className="w-4 h-4 text-slate-400" />
            </button>
            <div>
              <p className="text-sm font-bold text-slate-200">Your Loan Intelligence</p>
              <p className="text-[10px] text-slate-500 uppercase tracking-widest">Student Portal</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-slate-500">
            <span className="w-2 h-2 rounded-full bg-green" />
            Consent active
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        {/* Demo banner */}
        <div className="flex items-center gap-2 bg-amber-dim border border-amber/20 rounded-2xl px-4 py-3">
          <AlertTriangle className="w-4 h-4 text-amber-text shrink-0" />
          <p className="text-xs text-amber-text">
            Demo mode — DigiLocker integration pending NIC partner approval. Profile below is pre-loaded sample data.
          </p>
        </div>

        {/* Profile + Gauge row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Verified profile */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-card border border-border rounded-3xl p-6"
          >
            <h2 className="text-sm font-bold text-slate-200 mb-5">📋 Verified Profile</h2>
            <div className="space-y-3">
              {[
                { label: 'CGPA', value: `${DEMO_PROFILE.cgpa}/10`, verified: DEMO_PROFILE.cgpa_verified, source: 'NAD' },
                { label: 'Degree', value: DEMO_PROFILE.degree, verified: DEMO_PROFILE.institution_verified, source: 'AICTE' },
                { label: 'College', value: DEMO_PROFILE.college, verified: DEMO_PROFILE.institution_verified, source: 'NIRF' },
                { label: 'Internships', value: `${DEMO_PROFILE.internships_count}`, verified: false },
              ].map(row => (
                <div key={row.label} className="flex items-center justify-between py-2 border-b border-border/60 last:border-0">
                  <span className="text-[11px] text-slate-500 uppercase font-bold">{row.label}</span>
                  <div className="flex flex-col items-end gap-0.5">
                    <span className="text-sm font-medium text-slate-200">{row.value}</span>
                    <VerifiedBadge verified={row.verified} source={row.source} />
                  </div>
                </div>
              ))}
            </div>
            <button className="mt-4 w-full py-2 rounded-xl text-xs text-slate-400 border border-border-2 hover:border-blue/40 hover:text-blue-text transition-colors">
              Edit Profile
            </button>
          </motion.div>

          {/* Risk gauge */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-card border border-border rounded-3xl p-6 flex flex-col gap-4"
          >
            <h2 className="text-sm font-bold text-slate-200">📊 Your Risk Profile</h2>
            <RiskGauge
              probability={DEMO_RESULT.calibrated_probability}
              tier={DEMO_RESULT.risk_tier}
              ciLow={DEMO_RESULT.confidence_interval_90pct.lower}
              ciHigh={DEMO_RESULT.confidence_interval_90pct.upper}
              isLoading={false}
            />
            <div className="p-4 bg-green-dim border border-green/20 rounded-xl">
              <p className="text-xs text-slate-300 leading-relaxed">{DEMO_RESULT.recommendation}</p>
            </div>
            <ConformalInterval
              probability={DEMO_RESULT.calibrated_probability}
              ciLow={DEMO_RESULT.confidence_interval_90pct.lower}
              ciHigh={DEMO_RESULT.confidence_interval_90pct.upper}
              tier={DEMO_RESULT.risk_tier}
            />
          </motion.div>
        </div>

        {/* Skill Roadmap */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-card border border-border rounded-3xl p-6"
        >
          <h2 className="text-sm font-bold text-slate-200 mb-5">🎯 3 Actions to Strengthen Your Profile</h2>
          <SkillRoadmap
            actions={[
              { priority_i: 3, action: 'Complete 1 more internship', time_estimate: '~3 months', effort_score: 7, probability_lift: 0.08, resource_url: 'https://internshala.com', resource_label: 'Internshala' },
              { priority_i: 2, action: 'Build 2 portfolio projects on GitHub', time_estimate: '~2 months', effort_score: 5, probability_lift: 0.05, resource_url: 'https://kaggle.com', resource_label: 'Kaggle' },
              { priority_i: 1, action: 'Complete domain certification (NPTEL)', time_estimate: '~1 month', effort_score: 3, probability_lift: 0.03, resource_url: 'https://nptel.ac.in', resource_label: 'NPTEL' },
            ]}
            currentTier={DEMO_RESULT.risk_tier}
          />
        </motion.div>

        {/* Loan ROI Calculator */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-card border border-border rounded-3xl p-6"
        >
          <h2 className="text-sm font-bold text-slate-200 mb-5">💰 Loan ROI Calculator</h2>

          {/* Controls */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            <div>
              <label htmlFor="student-loan-amount" className="block text-[10px] text-slate-500 uppercase font-bold mb-1">
                Loan Amount — {formatINR(loanAmount)}
              </label>
              <input
                id="student-loan-amount"
                type="range" min={100000} max={5000000} step={50000}
                value={loanAmount}
                onChange={e => setLoanAmount(Number(e.target.value))}
                className="w-full accent-blue"
              />
            </div>
            <div>
              <label htmlFor="interest-rate" className="block text-[10px] text-slate-500 uppercase font-bold mb-1">
                Interest Rate — {(interestRate * 100).toFixed(1)}%
              </label>
              <input
                id="interest-rate"
                type="range" min={0.07} max={0.18} step={0.005}
                value={interestRate}
                onChange={e => setInterestRate(Number(e.target.value))}
                className="w-full accent-blue"
              />
            </div>
            <div>
              <label htmlFor="tenure-years" className="block text-[10px] text-slate-500 uppercase font-bold mb-1">
                Tenure — {tenure} years
              </label>
              <input
                id="tenure-years"
                type="range" min={3} max={12} step={1}
                value={tenure}
                onChange={e => setTenure(Number(e.target.value))}
                className="w-full accent-blue"
              />
            </div>
          </div>

          {/* Key callouts */}
          <div className="flex flex-wrap gap-4 mb-4">
            <div className="bg-card-2 rounded-xl px-4 py-2 border border-border">
              <p className="text-[10px] text-slate-500">Break-even</p>
              <p className="text-lg font-bold font-mono text-green-text">
                {breakEvenYear > 0 ? `Year ${breakEvenYear}` : 'Day 1'}
              </p>
            </div>
            <div className="bg-card-2 rounded-xl px-4 py-2 border border-border">
              <p className="text-[10px] text-slate-500">Total Loan Cost</p>
              <p className="text-lg font-bold font-mono text-amber-text">
                {formatINR(loanAmount * (1 + interestRate * tenure / 2))}
              </p>
            </div>
          </div>

          {/* Area chart */}
          <div aria-label="Salary vs EMI trajectory chart over loan tenure" role="img">
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={loanData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="salGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="emiGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="year" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis tickFormatter={v => `₹${v}K`} tick={{ fontSize: 10, fill: '#64748b' }} />
                <Tooltip
                  formatter={(v: number, name: string) => [`₹${v}K`, name === 'salary' ? 'Annual Salary' : 'EMI (annual)']}
                  contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8 }}
                  labelStyle={{ color: '#94a3b8', fontSize: 11 }}
                />
                <ReferenceLine y={0} stroke="#475569" />
                <Area type="monotone" dataKey="salary" stroke="#10b981" fill="url(#salGrad)" strokeWidth={2} name="salary" isAnimationActive={false} />
                <Area type="monotone" dataKey="emi" stroke="#f43f5e" fill="url(#emiGrad)" strokeWidth={2} name="emi" isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <p className="text-[10px] text-slate-600 mt-2 text-center">
            Assumes 8% annual salary growth · For informational purposes only
          </p>
        </motion.div>
      </main>
    </div>
  )
}
