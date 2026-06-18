import { create } from 'zustand'

export const useAppStore = create((set) => ({
  showAuthModal: false,
  setShowAuthModal: (show) => set({ showAuthModal: show }),
  
  showProfileModal: false,
  setShowProfileModal: (show) => set({ showProfileModal: show }),
  
  // Optional: tracking which profile is being edited
  editingProfile: null,
  setEditingProfile: (profile) => set({ editingProfile: profile }),

  selectedProfileId: null,
  setSelectedProfileId: (id) => set({ selectedProfileId: id }),
}))
