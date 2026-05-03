import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Brain, CheckCircle2, ChevronRight, Loader2 } from 'lucide-react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { PsychometricQuestion, PsychometricResult } from '@/api/types'

interface PsychometricQuizProps {
  baseProb: number
  onResult?: (adjustedProb: number, profileType: string) => void
}

export default function PsychometricQuiz({ baseProb, onResult }: PsychometricQuizProps) {
  const [started, setStarted] = useState(false)
  const [currentQ, setCurrentQ] = useState(0)
  const [answers, setAnswers] = useState<number[]>([])
  const [result, setResult] = useState<PsychometricResult | null>(null)
  const [selectedScore, setSelectedScore] = useState<number | null>(null)

  const { data: questions, isLoading: questionsLoading } = useQuery({
    queryKey: ['psychometric-questions'],
    queryFn: async () => {
      const res = await apiClient.get('/student/psychometric-questions')
      return res.data.questions as PsychometricQuestion[]
    },
    enabled: started,
  })

  const { mutate: submitAnswers, isPending: submitting } = useMutation({
    mutationFn: async (finalAnswers: number[]) => {
      const res = await apiClient.post('/student/psychometric', {
        answers: finalAnswers,
        base_probability: baseProb,
      })
      return res.data as PsychometricResult
    },
    onSuccess: (data) => {
      setResult(data)
      onResult?.(data.adjusted_probability, data.profile_type)
    },
  })

  const handleAnswer = (score: number) => {
    if (selectedScore !== null) return
    setSelectedScore(score)
    const newAnswers = [...answers, score]

    setTimeout(() => {
      setAnswers(newAnswers)
      setSelectedScore(null)
      if (questions && currentQ < questions.length - 1) {
        setCurrentQ(q => q + 1)
      } else {
        submitAnswers(newAnswers)
      }
    }, 350)
  }

  if (!started) {
    return (
      <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-5">
        <div className="flex items-start gap-3 mb-4">
          <Brain size={18} className="text-purple-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-white">5-Question Psychometric Assessment</p>
            <p className="text-xs text-slate-400 mt-0.5">
              ~2 minutes · Refines your repayment probability by up to ±5%
            </p>
          </div>
        </div>
        <button
          onClick={() => setStarted(true)}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600/20 border border-purple-500/30 hover:bg-purple-600/30 text-purple-300 text-sm font-medium rounded-xl transition-colors"
        >
          Start assessment <ChevronRight size={14} />
        </button>
      </div>
    )
  }

  if (result) {
    const adj = result.adjustment
    const adjColor = adj >= 0 ? 'text-emerald-400' : 'text-red-400'
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-5"
      >
        <div className="flex items-center gap-2 mb-4">
          <CheckCircle2 size={16} className="text-emerald-400" />
          <span className="text-sm font-semibold text-white">Assessment Complete</span>
        </div>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="bg-slate-800/50 rounded-xl p-3 text-center">
            <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-1">Profile Type</p>
            <p className="text-xs font-semibold text-white leading-tight">{result.profile_type}</p>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-3 text-center">
            <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-1">Adjustment</p>
            <p className={`text-xl font-bold ${adjColor}`}>
              {adj >= 0 ? '+' : ''}{(adj * 100).toFixed(1)}%
            </p>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-3 text-center">
            <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-1">Adjusted Prob.</p>
            <p className="text-xl font-bold text-white">{Math.round(result.adjusted_probability * 100)}%</p>
          </div>
        </div>
        <p className="text-xs text-slate-400 leading-relaxed">{result.insight}</p>
      </motion.div>
    )
  }

  if (questionsLoading || !questions) {
    return (
      <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-5 flex items-center gap-3">
        <Loader2 size={16} className="animate-spin text-purple-400" />
        <p className="text-sm text-slate-400">Loading questions…</p>
      </div>
    )
  }

  if (submitting) {
    return (
      <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-5 flex items-center gap-3">
        <Loader2 size={16} className="animate-spin text-purple-400" />
        <p className="text-sm text-slate-400">Analysing your responses…</p>
      </div>
    )
  }

  const q = questions[currentQ]
  const progressPct = (currentQ / questions.length) * 100

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-5">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Brain size={14} className="text-purple-400" />
          <span className="text-[11px] text-slate-400 uppercase tracking-wide">{q.category}</span>
        </div>
        <span className="text-[11px] text-slate-500 font-mono">
          {currentQ + 1} / {questions.length}
        </span>
      </div>

      <div className="w-full bg-slate-800 h-1 rounded-full mb-4">
        <motion.div
          className="bg-purple-500 h-full rounded-full"
          animate={{ width: `${progressPct}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={currentQ}
          initial={{ opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -16 }}
          transition={{ duration: 0.2 }}
        >
          <p className="text-sm font-medium text-slate-100 mb-4 leading-snug">{q.question}</p>
          <div className="space-y-2">
            {q.options.map(opt => {
              const isSelected = selectedScore === opt.score
              return (
                <button
                  key={opt.label}
                  onClick={() => handleAnswer(opt.score)}
                  disabled={selectedScore !== null}
                  className={`w-full text-left px-4 py-3 rounded-xl text-sm transition-all border ${
                    isSelected
                      ? 'bg-purple-600/30 border-purple-500 text-white'
                      : 'bg-slate-800 hover:bg-slate-700 border-slate-700 hover:border-purple-500/40 text-slate-300'
                  } disabled:cursor-default`}
                >
                  <span className="font-semibold text-purple-400 mr-2">{opt.label}.</span>
                  {opt.text}
                </button>
              )
            })}
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
