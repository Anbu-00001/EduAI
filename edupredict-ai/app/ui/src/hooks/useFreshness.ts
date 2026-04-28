import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { FreshnessResponse } from '@/api/types'

export function useFreshness() {
  const qc = useQueryClient()

  const query = useQuery<FreshnessResponse, Error>({
    queryKey: ['freshness'],
    queryFn: async () => {
      const res = await apiClient.get<FreshnessResponse>('/data/freshness')
      return res.data
    },
    refetchInterval: 60_000,
    retry: 1,
  })

  const refresh = useMutation({
    mutationFn: async () => {
      await apiClient.post('/data/refresh')
    },
    onSuccess: () => {
      // Invalidate after ~5s so the message shows first
      setTimeout(() => qc.invalidateQueries({ queryKey: ['freshness'] }), 5000)
    },
  })

  return { ...query, refresh }
}
