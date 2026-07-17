import axios from 'axios'
import { useAuthStore } from '../store/authStore'
import { useAppStore } from '../store/appStore'

// In development, Vite proxies /api → localhost:8000
// In production, update VITE_API_BASE_URL env var
const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 60000, // 60s — Agentic RAG loops with multiple LLM calls can take up to 45-50s
})

// Attach JWT token to every request if authenticated
api.interceptors.request.use((config) => {
  const { token } = useAuthStore.getState()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 globally — refresh token and retry, or force re-login.
// Auth endpoints (/api/auth/*) are excluded: they handle their own errors
// and must NOT trigger logout (which would wipe the error message from the store).
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const isAuthEndpoint = originalRequest?.url?.includes('/api/auth/')

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !isAuthEndpoint           // ← skip retry logic for all /api/auth/* routes
    ) {
      originalRequest._retry = true
      const success = await useAuthStore.getState().refreshTokens()
      if (success) {
        return api(originalRequest)
      } else {
        useAuthStore.getState().logout()
        useAppStore.getState().setShowAuthModal(true)
      }
    }
    return Promise.reject(error)
  }
)


// ── Auth endpoints ───────────────────────────────────────────────────────────

export const authApi = {
  register: (email, password) =>
    api.post('/api/auth/register', { email, password }),

  verify: (email, code) =>
    api.post('/api/auth/verify', { email, code }),

  resendCode: (email) =>
    api.post('/api/auth/resend-code', { email }),

  login: (email, password) =>
    api.post('/api/auth/login', { email, password }),

  logout: () =>
    api.post('/api/auth/logout'),

  refresh: (refreshToken) =>
    api.post('/api/auth/refresh', { refresh_token: refreshToken }),
}

// ── Chat endpoints ───────────────────────────────────────────────────────────

export const chatApi = {
  createSession: (profileId = null) =>
    api.post('/api/chat/session', { profile_id: profileId }),

  sendMessage: (sessionId, message, profileId = null) =>
    api.post('/api/chat/message', {
      session_id: sessionId,
      message,
      profile_id: profileId,
    }),

  getHistory: (sessionId) =>
    api.get(`/api/chat/history/${sessionId}`),
}

// ── Profile endpoints ────────────────────────────────────────────────────────

export const profileApi = {
  list: () =>
    api.get('/api/profiles'),

  create: (profileData) =>
    api.post('/api/profiles', profileData),

  update: (profileId, profileData) =>
    api.put(`/api/profiles/${profileId}`, profileData),

  delete: (profileId) =>
    api.delete(`/api/profiles/${profileId}`),
}

// ── Analytics endpoints ──────────────────────────────────────────────────────

export const analyticsApi = {
  getSummary: (days = 7) =>
    api.get('/api/analytics/summary', { params: { days } }),

  getDocuments: () =>
    api.get('/api/analytics/documents'),
}

export default api
