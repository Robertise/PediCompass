import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/**
 * Sentinel value that means "user has explicitly chosen Guest Mode".
 * This lets us distinguish it from `null` (= "not initialised yet"),
 * which is important for deciding whether to auto-select on first load.
 *
 * All API callers must map GUEST_PROFILE_ID → null before sending to backend.
 */
export const GUEST_PROFILE_ID = 'guest'

export const useAppStore = create(
  persist(
    (set) => ({
      showAuthModal: false,
      setShowAuthModal: (show) => set({ showAuthModal: show }),

      showProfileModal: false,
      setShowProfileModal: (show) => set({ showProfileModal: show }),

      // Optional: tracking which profile is being edited
      editingProfile: null,
      setEditingProfile: (profile) => set({ editingProfile: profile }),

      // null       → not yet initialised (first ever load, no stored value)
      // "guest"    → user explicitly chose Guest Mode
      // "<uuid>"   → a specific child profile
      selectedProfileId: null,
      setSelectedProfileId: (id) => set({ selectedProfileId: id }),

      chatResetKey: 0,
      triggerChatReset: () => set((state) => ({ chatResetKey: state.chatResetKey + 1 })),

      isChatActive: false,
      setIsChatActive: (active) => set({ isChatActive: active }),

      dismissedStaleReminders: {},
      dismissStaleReminder: (profileId) =>
        set((state) => ({
          dismissedStaleReminders: { ...state.dismissedStaleReminders, [profileId]: true },
        })),

      activeTrace: null,
      setActiveTrace: (trace) => set({ activeTrace: trace }),

      isStreaming: false,
      setIsStreaming: (streaming) => set({ isStreaming: streaming }),
    }),
    {
      name: 'pedix-app',
      // Only persist the profile selection — modal states must NOT persist
      // (they should always start closed on every page load).
      partialize: (state) => ({
        selectedProfileId: state.selectedProfileId,
      }),
    }
  )
)
