import { motion } from 'framer-motion'
import { ChevronLeft } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function NotFound() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-bg flex flex-col">
      {/* Header */}
      <header className="border-b border-border sticky top-0 z-20 bg-bg/80 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate(-1)} className="p-1.5 rounded-lg hover:bg-card-2 transition-colors" aria-label="Back">
              <ChevronLeft className="w-4 h-4 text-slate-400" />
            </button>
            <div>
              <p className="text-sm font-bold text-slate-200">EduPredict AI</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center"
        >
          <h1 className="text-8xl font-black text-slate-800 tracking-tighter mb-4">404</h1>
          <h2 className="text-2xl font-bold text-slate-200 mb-2">Page not found</h2>
          <p className="text-slate-500 mb-8 max-w-sm mx-auto">This route doesn't exist.</p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={() => navigate('/')}
              className="px-6 py-3 bg-blue hover:bg-blue/90 text-white text-sm font-bold rounded-xl transition-colors w-full sm:w-auto"
            >
              Go home
            </button>
            <button
              onClick={() => navigate('/lender')}
              className="px-6 py-3 bg-card-2 hover:bg-border border border-border text-slate-300 text-sm font-bold rounded-xl transition-colors w-full sm:w-auto"
            >
              Lender portal
            </button>
          </div>
        </motion.div>
      </main>
    </div>
  )
}
