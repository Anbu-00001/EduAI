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

      const payload = {
        ...profile,
        user_hash: userHash,
        consent: {
          data_sources: ['Academic Records', 'Job Market Data', 'Gov Stats', 'Peer Cohort'],
          notice_version: '1.0',
        },
      }

      const res = await apiClient.post<AssessmentResponse>('/assess', payload)
      return res.data
    },
  })
}
