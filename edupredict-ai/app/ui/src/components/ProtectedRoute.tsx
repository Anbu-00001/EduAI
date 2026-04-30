import React from 'react'
import { Navigate } from 'react-router-dom'
import { parseJwt, isTokenExpired } from '@/lib/auth'

interface ProtectedRouteProps {
  children: React.ReactNode
  requireRole: 'lender' | 'admin' | 'student'
}

export default function ProtectedRoute({ children, requireRole }: ProtectedRouteProps) {
  const apiKey = sessionStorage.getItem('ep_api_key')
  const jwt = sessionStorage.getItem('ep_jwt')
  const studentJwt = sessionStorage.getItem('ep_student_jwt')

  if (requireRole === 'student') {
    if (!studentJwt) {
      return <Navigate to="/" replace />
    }
    return <>{children}</>
  }

  if (requireRole === 'lender') {
    if (!apiKey) {
      return <Navigate to="/" replace />
    }
    return <>{children}</>
  }

  if (requireRole === 'admin') {
    if (!jwt) {
      return <Navigate to="/" replace />
    }
    const payload = parseJwt(jwt)
    if (!payload || isTokenExpired(payload)) {
      sessionStorage.removeItem('ep_jwt')
      return <Navigate to="/" replace />
    }
    if (payload.sub !== 'admin') {
      return <Navigate to="/" replace />
    }
    return <>{children}</>
  }

  // default fallback
  return <>{children}</>
}
