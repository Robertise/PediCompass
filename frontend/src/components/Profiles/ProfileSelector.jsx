import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { profileApi } from '../../api/client'
import { useAuthStore } from '../../store/authStore'
import { useAppStore } from '../../store/appStore'
import { ageDaysFromDob, ageDaysToDisplay } from '../../utils/ageUtils'

export default function ProfileSelector() {
  const { user } = useAuthStore()
  const { setShowAuthModal, setShowProfileModal, selectedProfileId, setSelectedProfileId } = useAppStore()
  const [profiles, setProfiles] = useState([])
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    async function loadProfiles() {
      if (!user) {
        setProfiles([])
        setSelectedProfileId(null)
        return
      }
      try {
        const res = await profileApi.list()
        setProfiles(res.data)
        if (res.data.length > 0 && !selectedProfileId) {
          setSelectedProfileId(res.data[0].profile_id)
        }
      } catch (err) {
        console.error('Failed to load profiles', err)
      }
    }
    loadProfiles()
  }, [user, selectedProfileId, setSelectedProfileId])

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (id) => {
    setSelectedProfileId(id)
    setIsOpen(false)
  }

  const handleCreateNew = () => {
    setIsOpen(false)
    if (!user) {
      setShowAuthModal(true)
    } else {
      setShowProfileModal(true)
    }
  }

  const handleManage = () => {
    setIsOpen(false)
    if (!user) {
      setShowAuthModal(true)
    } else {
      navigate('/profiles')
    }
  }

  const selectedProfile = profiles.find(p => p.profile_id === selectedProfileId)
  
  let displayText = 'Guest Mode'
  if (selectedProfile) {
    const ageDays = ageDaysFromDob(selectedProfile.dob)
    const ageStr = ageDaysToDisplay(ageDays)
    displayText = `${selectedProfile.nickname} • ${ageStr}`
  } else if (user) {
    displayText = 'Select a child'
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-sm bg-surface-container-low px-sm py-xs rounded-full border border-outline-variant/30 hover:bg-surface-container transition-colors max-w-[200px] sm:max-w-xs"
      >
        <div className="w-8 h-8 rounded-full bg-primary-container/20 flex items-center justify-center shrink-0">
          <span className="material-symbols-outlined text-primary text-[20px]">child_care</span>
        </div>
        <span className="text-label-md font-label-md text-on-surface truncate">{displayText}</span>
        <span className="material-symbols-outlined text-on-surface-variant text-[20px]">
          {isOpen ? 'keyboard_arrow_up' : 'keyboard_arrow_down'}
        </span>
      </button>

      {isOpen && (
        <div className="absolute top-full mt-2 left-1/2 -translate-x-1/2 w-64 bg-surface-container-lowest border border-outline-variant/30 rounded-xl shadow-[0_8px_32px_rgba(0,0,0,0.12)] overflow-hidden z-50 flex flex-col">
          <div className="max-h-60 overflow-y-auto py-1">
            <button 
              onClick={() => handleSelect(null)}
              className={`w-full text-left px-4 py-3 text-label-md font-label-md hover:bg-surface-container transition-colors flex items-center gap-sm ${!selectedProfileId ? 'bg-primary-container/10 text-primary' : 'text-on-surface'}`}
            >
              <div className="w-6 h-6 rounded-full bg-surface-variant flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined text-[16px]">person</span>
              </div>
              <span>Guest Mode</span>
            </button>
            
            {profiles.map(p => {
              const ageDays = ageDaysFromDob(p.dob)
              const ageStr = ageDaysToDisplay(ageDays)
              return (
                <button 
                  key={p.profile_id}
                  onClick={() => handleSelect(p.profile_id)}
                  className={`w-full text-left px-4 py-3 text-label-md font-label-md hover:bg-surface-container transition-colors flex items-center gap-sm ${selectedProfileId === p.profile_id ? 'bg-primary-container/10 text-primary' : 'text-on-surface'}`}
                >
                  <div className="w-6 h-6 rounded-full bg-primary-container/20 flex items-center justify-center shrink-0">
                    <span className="material-symbols-outlined text-primary text-[16px]">child_care</span>
                  </div>
                  <span className="truncate">{p.nickname} • {ageStr}</span>
                </button>
              )
            })}
          </div>
          
          <div className="border-t border-outline-variant/30 bg-surface-container-low p-2 flex flex-col gap-1">
            <button 
              onClick={handleManage}
              className="w-full text-left px-2 py-2 text-label-md font-label-md text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/50 rounded-lg transition-colors flex items-center gap-xs"
            >
              <span className="material-symbols-outlined text-[18px]">manage_accounts</span> Manage Profiles
            </button>
            <button 
              onClick={handleCreateNew}
              className="w-full text-left px-2 py-2 text-label-md font-label-md text-primary hover:bg-primary-container/20 rounded-lg transition-colors flex items-center gap-xs"
            >
              <span className="material-symbols-outlined text-[18px]">add_circle</span> Create New Profile
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
