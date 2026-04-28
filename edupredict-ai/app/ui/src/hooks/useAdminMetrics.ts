import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

export interface AdminMetrics {
  live: {
    auc:             number | null
    ece:             number | null
    dpi:             number | null
    predictions_1h:  number | null
    cache_age_hours: number | null
    macro_fallbacks: number | null
    drift_psi:       number | null
    p50_latency_ms:  number | null
    p99_latency_ms:  number | null
  }
  static: {
    auc:           number | null
    ece:           number | null
    train_size:    number | null
    model_version: string | null
    n_features:    number
  }
  grafana_url:    string
  prometheus_url: string
}

export function useAdminMetrics() {
  return useQuery<AdminMetrics, Error>({
    queryKey: ['admin-metrics'],
    queryFn: async () => {
      const res = await apiClient.get<AdminMetrics>('/admin/live-metrics')
      return res.data
    },
    refetchInterval: 15_000,
    retry: 1,
  })
}
