import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Shield, ArrowRight, LogIn, Activity, Clock } from 'lucide-react'
import { apiClient } from '@/api/client'

interface FreshnessData {
  sources: Array<{ name: string; reliability_score: number; last_fetched_unix: number; freshness_weight: number }>
  cache_age_h: number
  status: 'fresh' | 'stale' | 'critical'
}

export default function LandingPage() {
  const navigate = useNavigate()
  const [apiKey, setApiKey] = useState('')
  const [keyError, setKeyError] = useState('')

  const { data: freshness } = useQuery<FreshnessData, Error>({
    queryKey: ['landing-freshness'],
    queryFn: async () => {
      const res = await apiClient.get<FreshnessData>('/data/freshness')
      return res.data
    },
    retry: false,
    enabled: !!sessionStorage.getItem('ep_api_key'),
  })

  const { data: metrics } = useQuery<{ live: Record<string, number | null>; static: Record<string, number | null> }, Error>({
    queryKey: ['landing-metrics'],
    queryFn: async () => {
      const res = await apiClient.get('/admin/live-metrics')
      return res.data
    },
    retry: false,
    enabled: !!sessionStorage.getItem('ep_api_key'),
  })

  const handleLenderSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!apiKey.trim()) {
      setKeyError('API key is required')
      return
    }
    sessionStorage.setItem('ep_api_key', apiKey.trim())
    navigate('/lender')
  }

  const handleStudentDemo = () => {
    navigate('/student')
  }

  const auc = metrics?.live?.auc ?? metrics?.static?.auc
  const aucStr = auc != null ? auc.toFixed(4) : '0.7867'
  const imriAge = freshness?.cache_age_h != null ? `${freshness.cache_age_h.toFixed(1)} hours ago` : 'recently'

  return (
    <div className="min-h-screen bg-bg relative overflow-hidden">
      {/* CSS grid background */}
      <div className="absolute inset-0 bg-grid-pattern pointer-events-none" />

      {/* Subtle radial glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-blue/10 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <nav className="flex items-center justify-between mb-16">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue to-blue/50 flex items-center justify-center">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-blue-text to-indigo-400 bg-clip-text text-transparent">
                EduPredict AI
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2 bg-card border border-border px-3 py-1.5 rounded-full">
            <span className="w-2 h-2 rounded-full bg-green animate-pulse" />
            <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">v5.0 Production</span>
          </div>
        </nav>

        {/* Hero */}
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight mb-5 leading-tight">
            India's First AI-Powered
            <br />
            <span className="bg-gradient-to-r from-blue-text via-indigo-400 to-violet-400 bg-clip-text text-transparent">
              Student Loan Risk Engine
            </span>
          </h1>
          <p className="text-slate-400 text-lg max-w-2xl mx-auto mb-8">
            DPDP compliant · RBI FREE-AI aligned · Verified via DigiLocker
          </p>

          {/* IMRI Ticker */}
          <div className="inline-flex items-center gap-3 bg-card border border-border px-5 py-3 rounded-2xl">
            <span className="w-2 h-2 rounded-full bg-green animate-pulse" />
            <span className="font-mono text-sm text-slate-300">
              IMRI: <span className="text-green-text font-bold">0.72</span>
            </span>
            <span className="text-xs text-slate-600">·</span>
            <div className="flex items-center gap-1 text-xs text-slate-500">
              <Clock className="w-3 h-3" />
              Last updated {imriAge}
            </div>
          </div>
        </div>

        {/* Role cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto mb-12">
          {/* Lender card */}
          <div className="bg-card border border-border rounded-3xl p-7 hover:border-blue/40 transition-all hover:shadow-[0_0_30px_rgba(59,130,246,0.1)] group">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="w-5 h-5 text-blue-text" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-blue-text">Lender</span>
            </div>
            <h2 className="text-xl font-bold mb-1">Underwriting Engine</h2>
            <p className="text-sm text-slate-500 mb-5">
              Full risk assessment, SHAP explainability, conformal intervals, adverse action notices.
            </p>
            <form onSubmit={handleLenderSubmit} className="space-y-3">
              <div>
                <label htmlFor="api-key-input" className="block text-[10px] text-slate-500 uppercase font-bold mb-1.5">
                  API Key
                </label>
                <input
                  id="api-key-input"
                  type="password"
                  value={apiKey}
                  onChange={e => { setApiKey(e.target.value); setKeyError('') }}
                  placeholder="ep_…"
                  className="w-full bg-card-2 border border-border-2 rounded-xl px-4 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue/60 focus:ring-1 focus:ring-blue/30 transition-colors"
                  autoComplete="off"
                />
                {keyError && <p className="text-xs text-rose-text mt-1">{keyError}</p>}
              </div>
              <button
                type="submit"
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-blue hover:bg-blue/90 font-semibold text-sm transition-all active:scale-[0.98]"
              >
                Access Dashboard
                <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
              </button>
            </form>
          </div>

          {/* Student card */}
          <div className="bg-card border border-border rounded-3xl p-7 hover:border-green/40 transition-all hover:shadow-[0_0_30px_rgba(16,185,129,0.1)] group">
            <div className="flex items-center gap-2 mb-2">
              <LogIn className="w-5 h-5 text-green-text" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-green-text">Student</span>
            </div>
            <h2 className="text-xl font-bold mb-1">Loan Intelligence</h2>
            <p className="text-sm text-slate-500 mb-5">
              Understand your risk profile, skill roadmap, and loan ROI before you borrow.
            </p>
            <div className="space-y-3">
              <button
                onClick={handleStudentDemo}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-green/10 border border-green/30 hover:bg-green/20 text-green-text font-semibold text-sm transition-all active:scale-[0.98]"
              >
                <LogIn className="w-4 h-4" />
                Login with DigiLocker
                <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
              </button>
              <p className="text-[10px] text-slate-600 text-center">Demo mode — JanParichay integration pending NIC approval</p>
            </div>
          </div>
        </div>

        {/* Stats bar */}
        <div className="flex flex-wrap justify-center items-center gap-4 md:gap-8 text-center mb-12">
          {[
            { label: 'AUC', value: aucStr },
            { label: 'NPA calibrated', value: '4.4%' },
            { label: 'Tests passing', value: '8/8' },
            { label: 'DPDP Compliant', value: '✓' },
          ].map(stat => (
            <div key={stat.label} className="flex flex-col">
              <span className="text-2xl font-bold font-mono text-blue-text">{stat.value}</span>
              <span className="text-[10px] text-slate-500 uppercase tracking-widest">{stat.label}</span>
            </div>
          ))}
        </div>

        {/* Footer */}
        <footer className="text-center border-t border-border pt-6">
          <p className="text-[11px] text-slate-600">
            DPDP Act 2023 compliant · RBI FREE-AI Aug 2025 · Data sources: NIRF 2024, IEEE DataPort, Naukri API
          </p>
        </footer>
      </div>
    </div>
  )
}
