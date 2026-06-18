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
    <main className="flex-1 flex flex-col h-full bg-surface-lowest overflow-y-auto">
      <div className="w-full max-w-4xl mx-auto px-gutter py-xl">
        <div className="flex justify-between items-center mb-lg">
          <div className="flex items-center gap-sm">
            <button 
              onClick={() => navigate('/')}
              className="w-10 h-10 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container transition-colors"
              aria-label="Back to chat"
            >
              <span className="material-symbols-outlined">arrow_back</span>
            </button>
            <h2 className="text-display-sm font-display-sm font-bold text-on-surface">Manage Profiles</h2>
          </div>
          <button 
            className="bg-primary hover:bg-primary-fixed-variant text-on-primary px-md py-xs rounded-full text-label-md font-label-md font-bold transition-colors flex items-center gap-xs shadow-sm" 
            onClick={handleCreate}
          >
            <span className="material-symbols-outlined text-[20px]">add</span> Add Profile
          </button>
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <span className="material-symbols-outlined animate-spin text-primary text-[40px]">progress_activity</span>
          </div>
        ) : profiles.length === 0 ? (
          <div className="text-center p-xl bg-surface border border-outline-variant/30 rounded-[24px] shadow-sm flex flex-col items-center gap-md">
            <div className="w-16 h-16 rounded-full bg-primary-container/20 flex items-center justify-center">
              <span className="material-symbols-outlined text-primary text-[32px]">child_care</span>
            </div>
            <div>
              <h3 className="text-headline-md font-headline-md text-on-surface mb-xs">No Profiles Yet</h3>
              <p className="text-body-md font-body-md text-on-surface-variant max-w-md mx-auto">
                Create a child profile to get personalized pediatric care pathways and maintain health records.
              </p>
            </div>
            <button 
              className="bg-primary hover:bg-primary-fixed-variant text-on-primary px-lg py-sm rounded-full text-label-lg font-label-lg font-bold transition-colors shadow-sm" 
              onClick={handleCreate}
            >
              Create Your First Profile
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-md">
            {profiles.map(p => {
              const ageDays = ageDaysFromDob(p.dob)
              const ageStr = ageDaysToDisplay(ageDays)
              const stale = isProfileStale(p.last_updated)

              return (
                <div key={p.profile_id} className="bg-surface border border-outline-variant/40 rounded-[20px] p-md shadow-sm flex flex-col hover:shadow-md transition-shadow">
                  <div className="flex justify-between items-start mb-md">
                    <div className="flex items-center gap-sm">
                      <div className="w-12 h-12 rounded-full bg-tertiary-container flex items-center justify-center shrink-0">
                        <span className="text-on-tertiary-container text-headline-sm font-bold uppercase">{p.nickname.charAt(0)}</span>
                      </div>
                      <div className="flex flex-col">
                        <h3 className="text-headline-sm font-headline-sm text-on-surface">{p.nickname}</h3>
                        <span className="text-label-sm font-label-sm text-on-surface-variant">{ageStr} old</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col gap-sm flex-1 bg-surface-container-lowest rounded-xl p-sm border border-outline-variant/20 mb-md">
                    <div className="grid grid-cols-2 gap-y-xs gap-x-sm">
                      <div className="flex flex-col">
                        <span className="text-[11px] font-label-sm text-on-surface-variant uppercase tracking-wider">DOB</span>
                        <span className="text-body-sm font-body-sm text-on-surface">{p.dob}</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[11px] font-label-sm text-on-surface-variant uppercase tracking-wider">Gender</span>
                        <span className="text-body-sm font-body-sm text-on-surface">{p.gender}</span>
                      </div>
                      {p.weight_kg > 0 && (
                        <div className="flex flex-col col-span-2">
                          <span className="text-[11px] font-label-sm text-on-surface-variant uppercase tracking-wider">Weight</span>
                          <span className="text-body-sm font-body-sm text-on-surface">{p.weight_kg} kg</span>
                        </div>
                      )}
                      {p.medical_conditions?.length > 0 && (
                        <div className="flex flex-col col-span-2">
                          <span className="text-[11px] font-label-sm text-on-surface-variant uppercase tracking-wider">Medical Conditions</span>
                          <span className="text-body-sm font-body-sm text-on-surface">{p.medical_conditions.join(', ')}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {stale && (
                    <div className="bg-error-container/10 border border-error-container/30 text-error text-label-sm font-label-sm p-sm rounded-lg flex items-center gap-xs mb-md">
                      <span className="material-symbols-outlined text-[16px]">info</span>
                      Please review and update weight/conditions.
                    </div>
                  )}

                  <div className="flex gap-sm border-t border-outline-variant/30 pt-md mt-auto">
                    <button 
                      className="flex-1 bg-surface-variant hover:bg-surface-container-high text-on-surface rounded-full py-xs text-label-md font-label-md transition-colors" 
                      onClick={() => handleEdit(p)}
                    >
                      Edit Profile
                    </button>
                    <button 
                      className="flex-1 bg-error-container/20 hover:bg-error-container/40 text-error border border-error/20 rounded-full py-xs text-label-md font-label-md transition-colors" 
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
