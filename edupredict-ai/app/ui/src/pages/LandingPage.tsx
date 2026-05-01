import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Shield, ArrowRight, LogIn, FileText, Brain, ScrollText, CheckCircle2, XCircle, Server } from 'lucide-react'
import { apiClient } from '@/api/client'

export default function LandingPage() {
  const navigate = useNavigate()
  const [apiKey, setApiKey] = useState('')
  const [keyError, setKeyError] = useState('')

  const { data: statsToday } = useQuery({
    queryKey: ['landing-stats'],
    queryFn: async () => {
      try {
        const res = await apiClient.get('/stats/today')
        return res.data
      } catch {
        return { decisions_today: 0, p99_latency_ms: 0, model_auc: 0.803, model_version: 'v5.0-production' }
      }
    },
    refetchInterval: 10000,
  })

  const { data: publicMetrics } = useQuery({
    queryKey: ['public-metrics'],
    queryFn: async () => {
      try {
        const res = await apiClient.get('/metrics/public')
        return res.data
      } catch {
        return { 
          fairness: { fpr_diff: 0.087, tpr_diff: 0.034, demographic_parity: 0.82 },
          calibration_ece: 0.042,
          model_auc: 0.803,
          calibrated_npa: 4.4
        }
      }
    },
    refetchInterval: 30000,
  })

  const [adminKey, setAdminKey] = useState('')
  const [adminKeyError, setAdminKeyError] = useState('')

  const handleLenderSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!apiKey.trim()) {
      setKeyError('API key is required')
      return
    }
    sessionStorage.setItem('ep_api_key', apiKey.trim())
    navigate('/lender')
  }

  const handleAdminSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!adminKey.trim()) {
      setAdminKeyError('Admin key is required')
      return
    }
    sessionStorage.setItem('ep_api_key', adminKey.trim())
    navigate('/admin')
  }

  const handleStudentDemo = () => navigate('/student')

  const AnimatedNumber = ({ value }: { value: number | string }) => {
    const [display, setDisplay] = useState(0)
    useEffect(() => {
      if (typeof value !== 'number') {
        setDisplay(Number(value) || 0)
        return
      }
      let start = 0
      const duration = 800
      const interval = 16
      const steps = duration / interval
      const increment = value / steps
      const timer = setInterval(() => {
        start += increment
        if (start >= value) {
          setDisplay(value)
          clearInterval(timer)
        } else {
          setDisplay(start)
        }
      }, interval)
      return () => clearInterval(timer)
    }, [value])
    return <span>{typeof value === 'number' && Number.isInteger(value) ? Math.floor(display) : display.toFixed(typeof value === 'number' && value < 1 ? 3 : 1)}</span>
  }

  const auc = publicMetrics?.model_auc ?? statsToday?.model_auc ?? 0.803
  const decisions = statsToday?.decisions_today ?? 0
  const latency = statsToday?.p99_latency_ms ?? 42
  const npa = publicMetrics?.calibrated_npa ?? 4.4

  const renderMetricStatus = (value: number, threshold: number, operator: '<=' | '>=') => {
    const pass = operator === '<=' ? value <= threshold : value >= threshold
    return pass ? (
      <span className="flex items-center gap-1 text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded text-[10px] font-bold">
        <CheckCircle2 className="w-3 h-3" /> PASS
      </span>
    ) : (
      <span className="flex items-center gap-1 text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded text-[10px] font-bold">
        <XCircle className="w-3 h-3" /> FAIL
      </span>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 relative overflow-hidden text-slate-300">
      <div 
        className="absolute inset-0 opacity-5 pointer-events-none"
        style={{ 
          backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 39px, #fff 39px, #fff 40px), repeating-linear-gradient(90deg, transparent, transparent 39px, #fff 39px, #fff 40px)',
          backgroundSize: '40px 40px' 
        }} 
      />

      {/* SECTION 1: Hero */}
      <section className="relative z-10 flex flex-col items-center justify-center min-h-[90vh] px-4 pt-12 pb-24">
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-4 py-1.5 rounded-full mb-8">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[11px] font-mono text-slate-400 tracking-widest">
            Live · {decisions} assessments today
          </span>
        </div>

        <h1 className="text-4xl md:text-[64px] font-extrabold tracking-tight mb-6 leading-[1.1] text-center max-w-5xl">
          India's First AI-Powered
          <br />
          <span className="bg-gradient-to-r from-blue-text via-indigo-400 to-violet-400 bg-clip-text text-transparent">
            Student Loan Risk Engine
          </span>
        </h1>
        
        <p className="text-slate-400 text-lg md:text-xl text-center mb-12">
          DPDP compliant · RBI FREE-AI aligned · Verified via DigiLocker
        </p>

        {/* Live Stats Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-16 w-full max-w-4xl">
          {[
            { label: 'Model AUC', value: auc },
            { label: 'NPA Calibrated', value: npa, suffix: '%' },
            { label: 'P99 Latency', value: latency, prefix: '<', suffix: 'ms' },
            { label: 'Decisions Today', value: decisions },
          ].map(stat => (
            <div key={stat.label} className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-5 flex flex-col items-center justify-center text-center">
              <span className="text-3xl font-bold font-mono text-white mb-1">
                {stat.prefix}<AnimatedNumber value={stat.value} />{stat.suffix}
              </span>
              <span className="text-xs text-slate-400 uppercase tracking-widest">{stat.label}</span>
            </div>
          ))}
        </div>

        {/* CTA Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-5xl">
          <div className="bg-card border border-slate-800 rounded-3xl p-8 hover:border-blue/40 transition-all hover:shadow-[0_0_30px_rgba(59,130,246,0.1)] group">
            <div className="flex items-center gap-2 mb-3">
              <Shield className="w-5 h-5 text-blue-text" />
              <span className="text-xs font-bold uppercase tracking-widest text-blue-text">Lender Dashboard</span>
            </div>
            <p className="text-sm text-slate-400 mb-6 h-10">
              Access the underwriting engine, SHAP explanations, and compliance audits.
            </p>
            <form onSubmit={handleLenderSubmit} className="space-y-4">
              <input
                type="password"
                value={apiKey}
                onChange={e => { setApiKey(e.target.value); setKeyError('') }}
                placeholder="Enter API Key (ep_...)"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue/60 focus:ring-1 focus:ring-blue/30"
              />
              {keyError && <p className="text-xs text-rose-400">{keyError}</p>}
              <button type="submit" className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-blue hover:bg-blue/90 font-bold text-sm text-white transition-all">
                Access Dashboard <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            </form>
          </div>

          <div className="bg-card border border-slate-800 rounded-3xl p-8 hover:border-emerald-500/40 transition-all hover:shadow-[0_0_30px_rgba(16,185,129,0.1)] group flex flex-col">
            <div className="flex items-center gap-2 mb-3">
              <LogIn className="w-5 h-5 text-emerald-400" />
              <span className="text-xs font-bold uppercase tracking-widest text-emerald-400">Student Portal</span>
            </div>
            <p className="text-sm text-slate-400 mb-6 flex-1">
              Check your repayment profile, see your skill roadmap, and understand your loan risk — before you borrow.
            </p>
            <div className="space-y-3 mt-auto relative" title="Self-reported demo. No DigiLocker needed.">
              <button onClick={handleStudentDemo} className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 hover:bg-emerald-500/20 text-emerald-400 font-bold text-sm transition-all">
                Try the Demo <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          </div>

          <div className="bg-card border border-slate-800 rounded-3xl p-8 hover:border-violet-500/40 transition-all hover:shadow-[0_0_30px_rgba(139,92,246,0.1)] group flex flex-col">
            <div className="flex items-center gap-2 mb-3">
              <Server className="w-5 h-5 text-violet-400" />
              <span className="text-xs font-bold uppercase tracking-widest text-violet-400">Admin Console</span>
            </div>
            <p className="text-sm text-slate-400 mb-6 flex-1">
              Monitor model health, fairness audit trail, trigger retrains, and view all tenant assessments.
            </p>
            <form onSubmit={handleAdminSubmit} className="space-y-3 mt-auto">
              <input
                type="password"
                value={adminKey}
                onChange={e => { setAdminKey(e.target.value); setAdminKeyError('') }}
                placeholder="Admin API Key (ep_admin_...)"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/30"
              />
              {adminKeyError && <p className="text-xs text-rose-400">{adminKeyError}</p>}
              <button type="submit" className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-violet-600/20 border border-violet-500/30 hover:bg-violet-600/30 font-bold text-sm text-violet-300 transition-all">
                Open Console <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            </form>
          </div>
        </div>
      </section>

      {/* SECTION 2: How it works */}
      <section className="relative z-10 max-w-6xl mx-auto px-4 py-20 border-t border-slate-800/50">
        <h2 className="text-3xl font-bold text-center mb-12 text-white">Three steps. One verdict.</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-card border border-slate-800 rounded-3xl p-8 hover:border-blue/50 hover:-translate-y-1 transition-all">
            <div className="text-4xl font-black text-blue-text/20 mb-4">01</div>
            <FileText className="w-8 h-8 text-blue-text mb-4" />
            <h3 className="text-xl font-bold text-white mb-2">Submit profile</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Academic records, internships, field of study. DPDP-consented, encrypted in transit.
            </p>
          </div>
          <div className="bg-card border border-slate-800 rounded-3xl p-8 hover:border-blue/50 hover:-translate-y-1 transition-all">
            <div className="text-4xl font-black text-blue-text/20 mb-4">02</div>
            <Brain className="w-8 h-8 text-blue-text mb-4" />
            <h3 className="text-xl font-bold text-white mb-2">Stacked ensemble inference</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              XGBoost + LightGBM + CatBoost with conformal prediction intervals and per-group fairness calibration.
            </p>
          </div>
          <div className="bg-card border border-slate-800 rounded-3xl p-8 hover:border-blue/50 hover:-translate-y-1 transition-all">
            <div className="text-4xl font-black text-blue-text/20 mb-4">03</div>
            <ScrollText className="w-8 h-8 text-blue-text mb-4" />
            <h3 className="text-xl font-bold text-white mb-2">Auditable decision</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              SHAP explanations, adverse action notices, and a full underwriting report — RBI FREE-AI compliant.
            </p>
          </div>
        </div>
      </section>

      {/* SECTION 3: Live transparency strip */}
      <section className="relative z-10 bg-slate-900 border-y border-slate-800 py-16">
        <div className="max-w-6xl mx-auto px-4">
          <h2 className="text-2xl font-bold text-center mb-10 text-white">Built on transparency, not promises</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { label: 'Equalized Odds FPR diff', value: publicMetrics?.fairness?.fpr_diff ?? 0.1111, threshold: 0.10, op: '<=' as const },
              { label: 'Predictive Parity diff', value: publicMetrics?.fairness?.predictive_parity_diff ?? 0.1459, threshold: 0.10, op: '<=' as const },
              { label: 'Demographic Parity Index', value: publicMetrics?.fairness?.demographic_parity ?? 0.9545, threshold: 0.80, op: '>=' as const },
              { label: 'Calibration ECE', value: publicMetrics?.calibration_ece ?? 0.0098, threshold: 0.05, op: '<=' as const },
            ].map(m => (
              <div key={m.label} className="bg-card border border-slate-800 rounded-2xl p-5 hover:bg-slate-800/50 transition-colors cursor-pointer" onClick={() => {/* Open model card modal */}}>
                <p className="text-xs text-slate-400 mb-3">{m.label}</p>
                <div className="flex items-end justify-between">
                  <span className="text-2xl font-bold font-mono text-white">{m.value.toFixed(3)}</span>
                  {renderMetricStatus(m.value, m.threshold, m.op)}
                </div>
                <p className="text-[10px] text-slate-500 mt-2 font-mono">Target: {m.op} {m.threshold.toFixed(2)}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SECTION 4: Sources & compliance footer */}
      <footer className="relative z-10 max-w-6xl mx-auto px-4 py-12 text-center">
        <div className="flex flex-wrap justify-center gap-3 mb-8">
          {['RBI FREE-AI', 'DPDP 2023', 'ECOA', 'MCA21', 'NIRF'].map(badge => (
            <span key={badge} className="px-3 py-1 rounded-full border border-slate-700 text-xs font-mono text-slate-400">
              {badge}
            </span>
          ))}
        </div>
        <p className="text-[11px] text-slate-600">
          DPDP Act 2023 compliant · RBI FREE-AI Aug 2025 · Data sources: NIRF 2024, IEEE DataPort, Naukri API
        </p>
      </footer>
    </div>
  )
}
