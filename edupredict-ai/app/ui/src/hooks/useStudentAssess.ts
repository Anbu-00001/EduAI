import { useMutation } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { StudentProfile, AssessmentResponse } from '@/api/types'

export function useStudentAssess() {
  return useMutation<AssessmentResponse, Error, StudentProfile>({
    mutationFn: async (profile: StudentProfile) => {
      // The student_jwt is injected by client.ts
      const payload = {
        ...profile,
        consent: {
          data_sources: ['Academic Records', 'Self-Reported Profile'],
          notice_version: '1.0',
        },
      }

      const res = await apiClient.post<AssessmentResponse>('/assess', payload)
      return res.data
    },
  })
}
