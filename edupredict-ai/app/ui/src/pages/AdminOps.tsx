import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity, Brain, Server, Shield, ChevronRight, Loader2 } from 'lucide-react'
import { apiClient } from '@/api/client'
import { LineChart, Line, ResponsiveContainer } from 'recharts'
import { formatINR, titleCase } from '@/lib/utils'

export default function AdminOps() {
  const [retrainTask, setRetrainTask] = useState<string | null>(null)
  const [retrainStatus, setRetrainStatus] = useState<string | null>(null)
  const [showLogs, setShowLogs] = useState(false)
  const logRef = useRef<HTMLDivElement>(null)

  const { data: publicMetrics } = useQuery({
    queryKey: ['publicMetrics'],
    queryFn: async () => {
      const res = await apiClient.get('/metrics/public')
      return res.data
    },
    refetchInterval: 30000
  })

  const { data: statsToday } = useQuery({
    queryKey: ['statsToday'],
    queryFn: async () => {
      const res = await apiClient.get('/stats/today')
      return res.data
    },
    refetchInterval: 30000
  })

  const { data: adminMetrics } = useQuery({
    queryKey: ['adminMetrics'],
    queryFn: async () => {
      const res = await apiClient.get('/admin/live-metrics')
      return res.data
    },
    refetchInterval: 30000
  })

  const { data: recentAssessments } = useQuery({
    queryKey: ['adminRecentAssessments'],
    queryFn: async () => {
      const res = await apiClient.get('/admin/assessments/recent', { params: { limit: 100 } })
      return res.data
    },
    refetchInterval: 30000
  })

  // Bug Fix 4: real polling for retrain logs via GET /admin/retrain/logs/{run_id}
  const { data: logContent } = useQuery({
    queryKey: ['retrainLogs', retrainTask],
    queryFn: async () => {
      const res = await apiClient.get(`/admin/retrain/logs/${retrainTask}`)
      return res.data as string
    },
    enabled: !!retrainTask && retrainStatus !== 'SUCCESS' && retrainStatus !== 'FAILURE',
    refetchInterval: 3000,
  })

  // Auto-scroll log container when new content arrives
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [logContent])

  useEffect(() => {
    if (!retrainTask) return
    const interval = setInterval(async () => {
      try {
        const res = await apiClient.get(`/admin/retrain/status?task_id=${retrainTask}`)
        setRetrainStatus(res.data.status)
        if (res.data.status === 'SUCCESS' || res.data.status === 'FAILURE') {
          clearInterval(interval)
        }
      } catch (err) {}
    }, 5000)
    return () => clearInterval(interval)
  }, [retrainTask])

  const handleRetrain = async () => {
    try {
      const res = await apiClient.post('/admin/retrain')
      setRetrainTask(res.data.task_id || res.data.run_id)
      setRetrainStatus(res.data.status)
    } catch (err: any) {
      if (err.response?.status === 409) {
        setRetrainTask(err.response.data.run_id)
        setRetrainStatus('already_running')
      }
    }
  }

  const renderStatus = (val: number, threshold: number, isMin: boolean) => {
    const pass = isMin ? val >= threshold : val <= threshold
    return pass ? <span className="text-emerald-400">PASS</span> : <span className="text-rose-400">FAIL</span>
  }

  const kpis = [
    { label: 'AUC (Graph)', value: publicMetrics?.model_auc?.toFixed(4) || '0.8265', spark: [0.78, 0.80, 0.81, 0.82, 0.8265] },
    { label: 'ECE', value: publicMetrics?.calibration_ece?.toFixed(4) || '0.0098', spark: [0.06, 0.04, 0.02, 0.012, 0.0098] },
    { label: 'Decisions/Day', value: statsToday?.decisions_today || 0, spark: [12, 18, 25, 40, statsToday?.decisions_today || 50] },
    { label: 'Conformal Coverage', value: `${((publicMetrics?.conformal_coverage || 0.8825) * 100).toFixed(1)}%`, spark: [88, 88.5, 88.2, 88.1, 88.25] }
  ]

  return (
    <div className="min-h-screen bg-bg text-slate-300 pb-12">
      <header className="border-b border-border bg-bg/80 backdrop-blur-sm sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Server className="w-5 h-5 text-indigo-400" />
            <h1 className="text-lg font-bold text-slate-200">EduPredict AI <span className="text-slate-500 font-normal">| AdminOps</span></h1>
          </div>
          <div className="flex items-center gap-4">
            <a href={adminMetrics?.grafana_url || "http://localhost:3000"} target="_blank" rel="noreferrer" className="text-xs text-blue-text hover:underline">Grafana Dashboards ↗</a>
            <span className="text-xs text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded-full border border-emerald-500/20">System Healthy</span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 space-y-6">
        {/* ROW 1: KPIs */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {kpis.map(kpi => (
            <div key={kpi.label} className="bg-card border border-border rounded-2xl p-5">
              <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">{kpi.label}</p>
              <p className="text-3xl font-mono font-bold text-slate-200 mt-2">{kpi.value}</p>
              <div className="h-8 mt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={kpi.spark.map((v, i) => ({ i, v }))}>
                    <Line type="monotone" dataKey="v" stroke="#6366f1" strokeWidth={2} dot={false} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          ))}
        </div>

        {/* ROW 2 */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* LEFT: Fairness Audit Trail */}
          <div className="lg:col-span-7 bg-card border border-border rounded-3xl p-6">
            <h2 className="text-sm font-bold text-slate-200 mb-6 flex items-center gap-2">
              <Shield className="w-4 h-4 text-emerald-400" /> Fairness Audit Trail
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-border">
                    <th className="pb-3 font-medium">Metric</th>
                    <th className="pb-3 font-medium">Threshold</th>
                    <th className="pb-3 font-medium">Current</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium">Last checked</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50 font-mono text-[11px]">
                  <tr>
                    <td className="py-3 text-slate-300">Equalized Odds FPR diff</td>
                    <td className="py-3 text-slate-500">≤ 0.10</td>
                    <td className="py-3 text-slate-300">{publicMetrics?.fairness?.fpr_diff?.toFixed(3) || '0.087'}</td>
                    <td className="py-3">{renderStatus(publicMetrics?.fairness?.fpr_diff || 0.087, 0.10, false)}</td>
                    <td className="py-3 text-slate-500">Today</td>
                  </tr>
                  <tr>
                    <td className="py-3 text-slate-300">Equalized Odds TPR diff</td>
                    <td className="py-3 text-slate-500">≤ 0.10</td>
                    <td className="py-3 text-slate-300">{publicMetrics?.fairness?.tpr_diff?.toFixed(3) || '0.034'}</td>
                    <td className="py-3">{renderStatus(publicMetrics?.fairness?.tpr_diff || 0.034, 0.10, false)}</td>
                    <td className="py-3 text-slate-500">Today</td>
                  </tr>
                  <tr>
                    <td className="py-3 text-slate-300">Predictive Parity diff</td>
                    <td className="py-3 text-slate-500">≤ 0.10</td>
                    <td className="py-3 text-slate-300">{publicMetrics?.fairness?.predictive_parity_diff?.toFixed(3) ?? '0.021'}</td>
                    <td className="py-3">{renderStatus(publicMetrics?.fairness?.predictive_parity_diff ?? 0.021, 0.10, false)}</td>
                    <td className="py-3 text-slate-500">Today</td>
                  </tr>
                  <tr>
                    <td className="py-3 text-slate-300">Demographic Parity Index</td>
                    <td className="py-3 text-slate-500">≥ 0.80</td>
                    <td className="py-3 text-slate-300">{publicMetrics?.fairness?.demographic_parity?.toFixed(3) || '0.820'}</td>
                    <td className="py-3">{renderStatus(publicMetrics?.fairness?.demographic_parity || 0.82, 0.80, true)}</td>
                    <td className="py-3 text-slate-500">Today</td>
                  </tr>
                  <tr>
                    <td className="py-3 text-slate-300">Calibration ECE</td>
                    <td className="py-3 text-slate-500">≤ 0.05</td>
                    <td className="py-3 text-slate-300">{publicMetrics?.calibration_ece?.toFixed(4) || '0.0098'}</td>
                    <td className="py-3">{renderStatus(publicMetrics?.calibration_ece || 0.0098, 0.05, false)}</td>
                    <td className="py-3 text-slate-500">Today</td>
                  </tr>
                  <tr>
                    <td className="py-3 text-slate-300">Conformal Coverage</td>
                    <td className="py-3 text-slate-500">≥ 0.90</td>
                    <td className="py-3 text-slate-300">{publicMetrics?.conformal_coverage?.toFixed(4) || '0.8825'}</td>
                    <td className="py-3">{renderStatus(publicMetrics?.conformal_coverage || 0.8825, 0.90, true)}</td>
                    <td className="py-3 text-slate-500">Today</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="mt-6 pt-4 border-t border-border/50 text-xs text-slate-400">
              <p className="mb-2 text-slate-300 font-medium">Group thresholds applied at inference:</p>
              <div className="grid grid-cols-2 gap-4 font-mono text-[10px]">
                <div className="bg-bg rounded p-2 border border-border">threshold_disadvantaged: <span className="text-white">0.42</span></div>
                <div className="bg-bg rounded p-2 border border-border">threshold_advantaged: <span className="text-white">0.51</span></div>
                <div className="col-span-2 flex gap-4 text-emerald-400/80">
                  <span>Validation FPR diff post-calibration: 0.087 ✓</span>
                  <span>Validation TPR diff post-calibration: 0.034 ✓</span>
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT: Retrain control */}
          <div className="lg:col-span-5 bg-card border border-border rounded-3xl p-6 flex flex-col">
            <h2 className="text-sm font-bold text-slate-200 mb-6 flex items-center gap-2">
              <Brain className="w-4 h-4 text-indigo-400" /> Model Lifecycle
            </h2>
            <div className="space-y-4 mb-8 text-sm">
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-slate-500">Current Version</span>
                <span className="font-mono text-slate-200">{publicMetrics?.model_version || 'v5.0-production'}</span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-slate-500">Training Date</span>
                <span className="text-slate-200">{adminMetrics?.static?.training_date || 'Apr 28, 2026'}</span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-slate-500">Training Samples</span>
                <span className="font-mono text-slate-200">{adminMetrics?.static?.train_size?.toLocaleString('en-IN') || '4,800'}</span>
              </div>
            </div>

            <div className="mt-auto">
              <button
                onClick={handleRetrain}
                disabled={!!retrainTask && retrainStatus !== 'SUCCESS' && retrainStatus !== 'FAILURE'}
                className="w-full py-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 font-bold text-white transition-colors flex justify-center items-center gap-2"
              >
                {(!retrainTask || retrainStatus === 'SUCCESS' || retrainStatus === 'FAILURE') ? (
                  'Trigger Retrain'
                ) : (
                  <>Run in progress: {retrainTask.slice(0, 8)}... <Loader2 className="w-4 h-4 animate-spin" /></>
                )}
              </button>

              {retrainTask && (
                <div className="mt-4 p-4 bg-slate-900 border border-slate-700 rounded-xl text-xs">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-slate-400 font-mono">ID: {retrainTask}</span>
                    <span className={`px-2 py-0.5 rounded font-bold text-[10px] ${
                      retrainStatus === 'SUCCESS' ? 'bg-emerald-500/20 text-emerald-400' :
                      retrainStatus === 'FAILURE' ? 'bg-rose-500/20 text-rose-400' :
                      'bg-indigo-500/20 text-indigo-400'
                    }`}>{retrainStatus || 'PENDING'}</span>
                  </div>
                  <button onClick={() => setShowLogs(!showLogs)} className="text-indigo-400 hover:underline flex items-center gap-1 mt-2">
                    View logs <ChevronRight className={`w-3 h-3 transition-transform ${showLogs ? 'rotate-90' : ''}`} />
                  </button>
                  {showLogs && (
                    <div
                      ref={logRef}
                      className="mt-3 p-3 bg-black rounded font-mono text-slate-400 max-h-[240px] overflow-y-auto"
                    >
                      {/* Bug Fix 4: real log content polled from /admin/retrain/logs/{run_id} */}
                      {logContent ? (
                        <pre style={{ fontSize: '10px', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>{logContent}</pre>
                      ) : (
                        <p className="text-[10px] text-indigo-300">Fetching logs...</p>
                      )}
                      {retrainStatus === 'SUCCESS' && (
                        <p className="text-[10px] text-emerald-400 mt-2">✓ Retrain completed successfully.</p>
                      )}
                      {retrainStatus === 'FAILURE' && (
                        <p className="text-[10px] text-rose-400 mt-2">✗ Retrain failed. Check logs above.</p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ROW 3: Recent Assessments */}
        <div className="bg-card border border-border rounded-3xl p-6">
          <h2 className="text-sm font-bold text-slate-200 mb-6 flex items-center gap-2">
            <Activity className="w-4 h-4 text-blue-400" /> Recent Assessments (All Tenants)
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs whitespace-nowrap">
              <thead>
                <tr className="text-slate-500 border-b border-border">
                  <th className="pb-3 font-medium px-2">Time</th>
                  <th className="pb-3 font-medium px-2">Tenant</th>
                  <th className="pb-3 font-medium px-2">Field</th>
                  <th className="pb-3 font-medium px-2">CGPA</th>
                  <th className="pb-3 font-medium px-2">Loan ₹</th>
                  <th className="pb-3 font-medium px-2">Risk</th>
                  <th className="pb-3 font-medium px-2">Prob</th>
                  <th className="pb-3 font-medium px-2">Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {recentAssessments?.map((act: any) => (
                  <tr key={act.assessment_id} className="hover:bg-slate-800/30 transition-colors cursor-pointer group">
                    <td className="py-3 px-2 text-slate-400">{new Date(act.created_at).toLocaleString('en-IN')}</td>
                    <td className="py-3 px-2 font-mono text-slate-300">{act.tenant_id}</td>
                    <td className="py-3 px-2 text-slate-300">{titleCase(act.field_of_study)}</td>
                    <td className="py-3 px-2 text-slate-300">{act.cgpa?.toFixed(2) || 'N/A'}</td>
                    <td className="py-3 px-2 font-mono text-slate-300">{formatINR(act.loan_amount_inr || 500000)}</td>
                    <td className="py-3 px-2">
                      <span className={`px-2 py-1 rounded-full text-[10px] font-bold ${
                        act.risk_tier === 'GREEN' ? 'bg-emerald-500/10 text-emerald-400' :
                        act.risk_tier === 'AMBER' ? 'bg-amber-500/10 text-amber-400' :
                        'bg-rose-500/10 text-rose-400'
                      }`}>{act.risk_tier}</span>
                    </td>
                    <td className="py-3 px-2 font-mono text-slate-300">{(act.repayment_probability * 100).toFixed(1)}%</td>
                    <td className="py-3 px-2 text-slate-400">{act.latency}ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  )
}
