import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useThemeStore = create(
  persist(
    (set) => ({
      theme: 'system', // 'light' | 'dark' | 'system'
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: 'pedicompass-theme-storage',
    }
  )
)
