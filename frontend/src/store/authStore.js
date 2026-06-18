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
      user: null,          // { email, userId, isAdmin }
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
          const message = err.response?.data?.detail || 'Login failed. Please check your credentials.'
          set({ isLoading: false, error: message })
          return { success: false, error: message }
        }
      },

      register: async (email, password) => {
        set({ isLoading: true, error: null })
        try {
          await authApi.register(email, password)
          set({ isLoading: false })
          return { success: true }
        } catch (err) {
          const message = err.response?.data?.detail || 'Registration failed.'
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
