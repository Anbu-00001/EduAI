import { useMutation } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { StudentProfile, AssessmentResponse } from '@/api/types'
import { generateUserHash } from '@/lib/utils'

export function useAssess() {
  return useMutation<AssessmentResponse, Error, StudentProfile>({
    mutationFn: async (profile: StudentProfile) => {
      // Generate user_hash via Web Crypto API for DPDP compliance
      const sessionId = sessionStorage.getItem('ep_session_id') ?? crypto.randomUUID()
      sessionStorage.setItem('ep_session_id', sessionId)
      const userHash = await generateUserHash(sessionId)

      // 1. Record consent
      await apiClient.post('/consent', {
        user_hash: userHash,
        consent_given: true,
        data_sources: ['Academic Records', 'Job Market Data', 'Gov Stats', 'Peer Cohort'],
      })

      // 2. Run assessment
      const res = await apiClient.post<AssessmentResponse>('/assess', {
        ...profile,
        user_hash: userHash,
      })
      return res.data
    },
  })
}
