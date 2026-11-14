import axios from 'axios'
import { tokenStorage } from './tokenStorage'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
  headers: { Accept: 'application/json' },
})

// AuthProvider yahan logout callback register karta hai
let onAuthFailure = null
export function setAuthFailureHandler(fn) {
  onAuthFailure = fn
}

// In URLs par 401 ka matlab "galat credentials" hai, refresh try nahi karna
const SKIP_REFRESH = [
  '/auth/login/',
  '/auth/register/',
  '/auth/refresh/',
  '/auth/password/forgot/',
  '/auth/password/reset/',
]

api.interceptors.request.use((config) => {
  const access = tokenStorage.getAccess()
  if (access && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${access}`
  }
  return config
})

// Single-flight refresh: ek saath 5 requests 401 khayein to refresh sirf 1 baar hoga.
// Warna rotation + blacklist ki wajah se baaki 4 refresh calls fail ho jaati.
let refreshPromise = null

function refreshAccessToken() {
  if (!refreshPromise) {
    const refresh = tokenStorage.getRefresh()
    if (!refresh) return Promise.reject(new Error('No refresh token'))

    // Bare axios (interceptors ke bina) taaki infinite loop na bane
    refreshPromise = axios
      .post(`${API_BASE_URL}/auth/refresh/`, { refresh })
      .then(({ data }) => {
        // ROTATE_REFRESH_TOKENS=True: naya refresh token bhi save karna zaroori hai
        tokenStorage.setTokens({ access: data.access, refresh: data.refresh })
        return data.access
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const status = error.response?.status
    const url = original?.url || ''
    const skip = SKIP_REFRESH.some((p) => url.includes(p))

    if (status === 401 && original && !original._retry && !skip && tokenStorage.getRefresh()) {
      original._retry = true
      try {
        const newAccess = await refreshAccessToken()
        original.headers.Authorization = `Bearer ${newAccess}`
        return api(original)
      } catch {
        tokenStorage.clear()
        if (onAuthFailure) onAuthFailure()
        return Promise.reject(error)
      }
    }
    return Promise.reject(error)
  },
)

export default api