import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/v1'

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' },
})

// Inject auth header on every request
apiClient.interceptors.request.use((config) => {
  const apiKey = sessionStorage.getItem('ep_api_key')
  const jwtToken = sessionStorage.getItem('ep_jwt')
  
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey
  } else if (jwtToken) {
    config.headers['Authorization'] = `Bearer ${jwtToken}`
  }
  return config
})

// Handle 401 — clear session and redirect to login
apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      sessionStorage.clear()
      window.location.href = '/'
    }
    return Promise.reject(err)
  }
)
