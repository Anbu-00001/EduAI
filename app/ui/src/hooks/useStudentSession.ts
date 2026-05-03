import { useEffect, useState } from 'react'
import { apiClient } from '@/api/client'
import { generateUserHash } from '@/lib/utils'

export function useStudentSession() {
  const [userHash, setUserHash] = useState<string>('')
  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    async function initSession() {
      const existingToken = sessionStorage.getItem('ep_student_jwt')
      let hash = sessionStorage.getItem('ep_student_hash')

      if (!hash) {
        const sessionId = sessionStorage.getItem('ep_session_id') ?? crypto.randomUUID()
        sessionStorage.setItem('ep_session_id', sessionId)
        hash = await generateUserHash(sessionId)
        sessionStorage.setItem('ep_student_hash', hash)
      }

      setUserHash(hash)

      if (!existingToken) {
        try {
          const res = await apiClient.post('/auth/student-session', { user_hash: hash })
          sessionStorage.setItem('ep_student_jwt', res.data.access_token)
          setIsReady(true)
        } catch (e) {
          console.error("Failed to create student session", e)
          // Fallback or handle error
          setIsReady(true) // Still set ready so the UI can show the form/error
        }
      } else {
        setIsReady(true)
      }
    }

    initSession()
  }, [])

  return { userHash, isReady }
}
