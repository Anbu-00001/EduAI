import React from 'react'
import { Navigate } from 'react-router-dom'

interface ProtectedRouteProps {
  children: React.ReactNode
  requireRole: 'lender' | 'admin' | 'student'
}

export default function ProtectedRoute({ children, requireRole }: ProtectedRouteProps) {
  const apiKey = sessionStorage.getItem('ep_api_key')
  const jwt = sessionStorage.getItem('ep_jwt')

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
    // Very basic decode just for UI check (backend still verifies signature)
    try {
      const payloadBase64 = jwt.split('.')[1]
      const payload = JSON.parse(atob(payloadBase64))
      if (payload.tenant_id !== 'admin') {
        return <Navigate to="/" replace />
      }
    } catch {
      return <Navigate to="/" replace />
    }
    return <>{children}</>
  }

  // default fallback
  return <>{children}</>
}
