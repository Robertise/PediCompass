import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { profileApi } from '../api/client'
import { ageDaysFromDob, ageDaysToDisplay, isProfileStale } from '../utils/ageUtils'
import { useAppStore } from '../store/appStore'

export default function ProfilesPage() {
  const [profiles, setProfiles] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  
  const { setShowProfileModal, setEditingProfile } = useAppStore()

  const loadProfiles = async () => {
    setLoading(true)
    try {
      const res = await profileApi.list()
      setProfiles(res.data)
    } catch (err) {
      console.error('Failed to load profiles', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProfiles()
    
    // Listen for custom event from ProfileModal
    const handleUpdate = () => loadProfiles()
    window.addEventListener('profilesUpdated', handleUpdate)
    return () => window.removeEventListener('profilesUpdated', handleUpdate)
  }, [])

  const handleCreate = () => {
    setEditingProfile(null)
    setShowProfileModal(true)
  }

  const handleEdit = (profile) => {
    setEditingProfile(profile)
    setShowProfileModal(true)
  }

  const handleDelete = async (profileId) => {
    if (!window.confirm('Are you sure you want to delete this profile? This action cannot be undone.')) return
    try {
      await profileApi.delete(profileId)
      await loadProfiles()
      // Trigger update so ProfileSelector updates
      window.dispatchEvent(new Event('profilesUpdated'))
    } catch (err) {
      console.error('Failed to delete profile', err)
      alert('Failed to delete profile. Please try again.')
    }
  }

  return (
    <main className="flex-1 flex flex-col h-full bg-transparent overflow-y-auto">
      <div className="w-full max-w-4xl mx-auto px-4 sm:px-6 py-md sm:py-xl">
        <div className="flex justify-between items-center mb-sm sm:mb-lg">
          <div className="flex items-center gap-2">
            <button 
              onClick={() => navigate('/')}
              className="w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container transition-colors"
              aria-label="Back to chat"
            >
              <span className="material-symbols-outlined text-[20px]">arrow_back</span>
            </button>
            <h2 className="text-lg sm:text-display-sm font-bold text-on-surface">Manage Profiles</h2>
          </div>
          <button 
            className="bg-primary hover:bg-primary-fixed-variant text-on-primary px-3.5 py-1.5 sm:px-6 sm:py-2.5 rounded-full text-xs sm:text-label-md font-bold transition-colors flex items-center gap-1 shadow-sm" 
            onClick={handleCreate}
          >
            <span className="material-symbols-outlined text-[16px] sm:text-[20px]">add</span> Add Profile
          </button>
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <span className="material-symbols-outlined animate-spin text-primary text-[40px]">progress_activity</span>
          </div>
        ) : profiles.length === 0 ? (
          <div className="text-center p-md sm:p-xl flex flex-col items-center gap-sm sm:gap-md">
            <div>
              <h3 className="text-base sm:text-headline-md font-bold text-on-surface mb-xs">No Profiles Yet</h3>
              <p className="text-xs sm:text-body-md text-on-surface-variant max-w-md mx-auto">
                Create a child profile to get personalized pediatric care pathways and maintain health records.
              </p>
            </div>
            <button 
              className="bg-primary hover:bg-primary-fixed-variant text-on-primary px-5 py-2 sm:px-8 sm:py-3 rounded-full text-sm sm:text-label-lg font-bold transition-colors shadow-sm" 
              onClick={handleCreate}
            >
              Create Your First Profile
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-sm sm:gap-md">
            {profiles.map(p => {
              const ageDays = ageDaysFromDob(p.dob)
              const ageStr = ageDaysToDisplay(ageDays)
              const stale = isProfileStale(p.last_updated)

              return (
                <div key={p.profile_id} className="bg-surface dark:bg-surface-container-high rounded-[16px] sm:rounded-[20px] p-3 sm:p-md border border-black/5 dark:border-white/5 flex flex-col">
                  <div className="flex justify-between items-start mb-sm sm:mb-md">
                    <div className="flex items-center gap-sm">
                      <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-tertiary-container flex items-center justify-center shrink-0">
                        <span className="text-on-tertiary-container text-sm sm:text-headline-sm font-bold uppercase">{p.nickname.charAt(0)}</span>
                      </div>
                      <div className="flex flex-col">
                        <h3 className="text-sm sm:text-headline-sm font-bold text-on-surface">{p.nickname}</h3>
                        <span className="text-[11px] sm:text-label-sm text-on-surface-variant">{ageStr}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col gap-xs sm:gap-sm flex-1 bg-surface-container-low dark:bg-black/20 rounded-xl p-2.5 sm:p-sm mb-sm sm:mb-md">
                    <div className="grid grid-cols-2 gap-y-xs gap-x-sm">
                      <div className="flex flex-col">
                        <span className="text-[10px] sm:text-[11px] font-medium text-on-surface-variant uppercase tracking-wider">DOB</span>
                        <span className="text-xs sm:text-body-sm text-on-surface">{p.dob}</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[10px] sm:text-[11px] font-medium text-on-surface-variant uppercase tracking-wider">Gender</span>
                        <span className="text-xs sm:text-body-sm text-on-surface">{p.gender}</span>
                      </div>
                      {p.weight_kg > 0 && (
                        <div className="flex flex-col col-span-2">
                          <span className="text-[10px] sm:text-[11px] font-medium text-on-surface-variant uppercase tracking-wider">Weight</span>
                          <span className="text-xs sm:text-body-sm text-on-surface">{p.weight_kg} kg</span>
                        </div>
                      )}
                      {p.medical_conditions?.length > 0 && (
                        <div className="flex flex-col col-span-2">
                          <span className="text-[10px] sm:text-[11px] font-medium text-on-surface-variant uppercase tracking-wider">Medical Conditions</span>
                          <span className="text-xs sm:text-body-sm text-on-surface">{p.medical_conditions.join(', ')}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {stale && (
                    <div className="bg-error-container/10 border border-error-container/30 text-error text-[11px] sm:text-label-sm p-2 sm:p-sm rounded-lg flex items-center gap-xs mb-sm sm:mb-md">
                      <span className="material-symbols-outlined text-[16px]">info</span>
                      Please review and update weight/conditions.
                    </div>
                  )}

                  <div className="flex gap-2 sm:gap-sm">
                    <button 
                      className="flex-1 bg-surface-variant/50 hover:bg-surface-container-high text-on-surface rounded-full py-2 sm:py-3.5 text-xs sm:text-label-md font-medium transition-colors" 
                      onClick={() => handleEdit(p)}
                    >
                      Edit Profile
                    </button>
                    <button 
                      className="flex-1 bg-[#ef4444]/15 hover:bg-[#ef4444]/25 text-[#ef4444] rounded-full py-2 sm:py-3.5 text-xs sm:text-label-md font-medium transition-colors border-none" 
                      onClick={() => handleDelete(p.profile_id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </main>
  )
}
