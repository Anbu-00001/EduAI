import { ExternalLink } from 'lucide-react'

interface SkillAction {
  priority_i: number
  action: string
  time_estimate: string
  effort_score: number
  probability_lift: number
  resource_url?: string
  resource_label?: string
}

interface SkillRoadmapProps {
  actions: SkillAction[]
  currentTier: 'GREEN' | 'AMBER' | 'RED'
}

const EFFORT_STYLES: Record<string, string> = {
  HIGH:   'bg-amber-dim text-amber-text',
  MEDIUM: 'bg-blue-dim text-blue-text',
  LOW:    'bg-green-dim text-green-text',
}

function effortLabel(score: number): 'HIGH' | 'MEDIUM' | 'LOW' {
  if (score >= 7) return 'HIGH'
  if (score >= 4) return 'MEDIUM'
  return 'LOW'
}

// Default skill actions when backend doesn't provide them
const DEFAULT_ACTIONS: SkillAction[] = [
  { priority_i: 1, action: 'Complete 1 more internship', time_estimate: '~3 months', effort_score: 7, probability_lift: 0.08, resource_url: 'https://internshala.com', resource_label: 'Internshala' },
  { priority_i: 2, action: 'Build 2 GitHub portfolio projects', time_estimate: '~2 months', effort_score: 5, probability_lift: 0.05, resource_url: 'https://kaggle.com', resource_label: 'Kaggle' },
  { priority_i: 3, action: 'Complete a domain certification', time_estimate: '~1 month', effort_score: 4, probability_lift: 0.04, resource_url: 'https://nptel.ac.in', resource_label: 'NPTEL' },
]

export default function SkillRoadmap({ actions = DEFAULT_ACTIONS, currentTier }: SkillRoadmapProps) {
  const sorted = [...actions].sort((a, b) => b.priority_i - a.priority_i)
  const cumLift = sorted.reduce((acc, a) => acc + a.probability_lift, 0)

  return (
    <div>
      <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-4">
        Skill Roadmap — Strengthen Your Profile
      </p>

      <div className="space-y-3">
        {sorted.map((action, i) => {
          const level = effortLabel(action.effort_score)
          return (
            <div
              key={i}
              className="bg-card border border-border rounded-xl p-4 flex items-start gap-3 hover:border-border-2 transition-colors"
            >
              {/* Priority badge */}
              <div className="w-7 h-7 rounded-full bg-card-2 flex items-center justify-center text-xs font-bold text-slate-300 shrink-0">
                {sorted.length - i}
              </div>

              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-200">{action.action}</p>
                <div className="flex flex-wrap items-center gap-2 mt-1.5">
                  <span className="text-[10px] text-slate-500 font-mono">{action.time_estimate}</span>
                  <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded-full ${EFFORT_STYLES[level]}`}>
                    {level} effort
                  </span>
                  <span className="text-[10px] font-mono text-green-text">+{(action.probability_lift * 100).toFixed(0)}%</span>
                </div>
              </div>

              {action.resource_url && (
                <a
                  href={action.resource_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 flex items-center gap-1 text-[10px] text-blue-text hover:text-blue transition-colors"
                >
                  {action.resource_label ?? 'Resource'}
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
          )
        })}
      </div>

      {/* Cumulative lift note */}
      {cumLift > 0 && currentTier !== 'GREEN' && (
        <div className="mt-4 p-3 bg-green-dim border border-green/20 rounded-xl">
          <p className="text-xs text-green-text">
            ✓ Following all steps could improve your probability by ~{(cumLift * 100).toFixed(0)}% — potentially reaching GREEN tier.
          </p>
          <p className="text-[10px] text-slate-500 mt-1">Stop when GREEN · Results may vary by market conditions.</p>
        </div>
      )}
    </div>
  )
}
