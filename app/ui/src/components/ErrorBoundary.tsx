import React from 'react'
import { AlertTriangle } from 'lucide-react'

interface Props {
  children: React.ReactNode
  fallback?: React.ReactNode
  label?: string
}

interface State {
  hasError: boolean
  errorMessage: string
}

export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, errorMessage: '' }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error.message }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }
      
      return (
        <div className="flex flex-col items-center justify-center p-6 bg-card border border-border rounded-xl text-center">
          <AlertTriangle className="w-8 h-8 text-slate-500 mb-3" />
          <h3 className="text-sm font-bold text-slate-300">
            {this.props.label ?? 'Component'} unavailable
          </h3>
          <p className="text-xs text-slate-500 mt-1 max-w-[200px]">
            This panel failed to render. Other panels are unaffected.
          </p>
        </div>
      )
    }

    return this.props.children
  }
}
