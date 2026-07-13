import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useThemeStore = create(
  persist(
    (set) => ({
      theme: 'light', // 'light' | 'dark'
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: 'pedicompass-theme-storage',
    }
  )
)
