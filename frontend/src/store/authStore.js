import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { authApi } from '../api/client'

/**
 * Global auth state managed by Zustand with localStorage persistence.
 * Stores the Cognito ID token (JWT) and basic user info.
 */
export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,          // { email, user_id, isAdmin }
      token: null,         // Cognito id_token (JWT)
      refreshToken: null,  // Cognito refresh_token
      isLoading: false,
      error: null,

      // ── Actions ───────────────────────────────────────────────────────────

      login: async (email, password) => {
        set({ isLoading: true, error: null })
        try {
          const res = await authApi.login(email, password)
          const { id_token, refresh_token, user } = res.data
          set({
            user,
            token: id_token,
            refreshToken: refresh_token,
            isLoading: false,
            error: null,
          })
          return { success: true }
        } catch (err) {
          // Backend returns { message, error_code } inside detail for auth errors
          const detail = err.response?.data?.detail
          const message = (typeof detail === 'object' ? detail?.message : detail)
            || 'Login failed. Please check your credentials.'
          const errorCode = (typeof detail === 'object' ? detail?.error_code : null) || null
          set({ isLoading: false, error: message })
          return { success: false, error: message, errorCode }
        }
      },

      register: async (email, password) => {
        set({ isLoading: true, error: null })
        try {
          await authApi.register(email, password)
          set({ isLoading: false })
          return { success: true }
        } catch (err) {
          const message = err.response?.data?.detail || 'Registration failed. Please try again.'
          set({ isLoading: false, error: message })
          return { success: false, error: message }
        }
      },

      verify: async (email, code) => {
        set({ isLoading: true, error: null })
        try {
          await authApi.verify(email, code)
          set({ isLoading: false })
          return { success: true }
        } catch (err) {
          const message = err.response?.data?.detail || 'Verification failed. Please try again.'
          set({ isLoading: false, error: message })
          return { success: false, error: message }
        }
      },

      resendCode: async (email) => {
        set({ isLoading: true, error: null })
        try {
          await authApi.resendCode(email)
          set({ isLoading: false })
          return { success: true }
        } catch (err) {
          const message = err.response?.data?.detail || 'Could not resend code. Please try again.'
          set({ isLoading: false, error: message })
          return { success: false, error: message }
        }
      },

      logout: async () => {
        try {
          await authApi.logout()
        } catch {
          // Ignore logout API errors — always clear local state
        }
        set({ user: null, token: null, refreshToken: null, error: null })
      },

      clearError: () => set({ error: null }),

      refreshTokens: async () => {
        const { refreshToken } = get()
        if (!refreshToken) return false
        try {
          const res = await authApi.refresh(refreshToken)
          set({
            token: res.data.id_token,
            refreshToken: res.data.refresh_token || refreshToken,
          })
          return true
        } catch {
          return false
        }
      },

      // Utility: is the current user an admin?
      isAdmin: () => get().user?.isAdmin === true,
    }),
    {
      name: 'pedicompass-auth',
      // Only persist these fields — don't persist loading/error state
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
      }),
    }
  )
)
