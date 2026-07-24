import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { profileApi } from '../../api/client'
import { useAuthStore } from '../../store/authStore'
import { useAppStore, GUEST_PROFILE_ID } from '../../store/appStore'
import { ageDaysFromDob, ageDaysToDisplay } from '../../utils/ageUtils'

export default function ProfileSelector() {
  const { user } = useAuthStore()
  const { setShowAuthModal, setShowProfileModal, selectedProfileId, setSelectedProfileId, isChatActive, triggerChatReset } = useAppStore()
  const [profiles, setProfiles] = useState([])
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    async function loadProfiles() {
      if (!user) {
        setProfiles([])
        if (selectedProfileId !== null) {
          setSelectedProfileId(null)
          triggerChatReset()
        }
        return
      }
      try {
        const res = await profileApi.list()
        setProfiles(res.data)

        // Only auto-select if:
        //  1. There are profiles available
        //  2. The user has NOT already made an explicit selection
        //     (null = uninitialised; "guest" or a UUID = explicit choice)
        const isUninitialised = selectedProfileId === null
        if (res.data.length > 0 && isUninitialised) {
          setSelectedProfileId(res.data[0].profile_id)
        }
      } catch (err) {
        console.error('Failed to load profiles', err)
      }
    }
    loadProfiles()

    window.addEventListener('profilesUpdated', loadProfiles)
    return () => window.removeEventListener('profilesUpdated', loadProfiles)
  // selectedProfileId intentionally excluded — we read it once at startup via
  // the closure capture and must not re-trigger when the user changes selection.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user])

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
    // Use the sentinel so we can distinguish "guest chosen" from "uninitialised"
    const targetId = id === null ? GUEST_PROFILE_ID : id

    // Treat null (uninitialised) and GUEST_PROFILE_ID ("guest") as equivalent when checking if target changed
    const currentNormalized = (!selectedProfileId || selectedProfileId === GUEST_PROFILE_ID) ? GUEST_PROFILE_ID : selectedProfileId
    const targetNormalized = (!targetId || targetId === GUEST_PROFILE_ID) ? GUEST_PROFILE_ID : targetId

    if (targetNormalized === currentNormalized) {
      setSelectedProfileId(targetId)
      setIsOpen(false)
      return
    }

    if (isChatActive) {
      const confirm = window.confirm("You have an active chat. Switching profiles will clear the current chat history. Do you want to proceed?")
      if (!confirm) {
        setIsOpen(false)
        return
      }
    }

    setSelectedProfileId(targetId)
    triggerChatReset()
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

  // Resolve the active profile object (null when in guest / uninitialised)
  const isGuest = !selectedProfileId || selectedProfileId === GUEST_PROFILE_ID
  const selectedProfile = isGuest ? null : profiles.find(p => p.profile_id === selectedProfileId)

  let displayText = 'Guest Mode'
  if (selectedProfile) {
    const ageDays = ageDaysFromDob(selectedProfile.dob)
    const ageStr = ageDaysToDisplay(ageDays)
    displayText = `${selectedProfile.nickname} • ${ageStr}`
  } else if (user && profiles.length === 0) {
    displayText = 'No profiles yet'
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-xs sm:gap-sm bg-surface dark:bg-surface-container-high px-2 sm:px-sm py-1 sm:py-xs rounded-full hover:bg-surface-container dark:hover:bg-surface-container transition-colors max-w-[155px] xs:max-w-[180px] sm:max-w-xs shadow-[0_0_10px_1px_rgba(0,0,0,0.1)] dark:shadow-soft-dark"
      >
        <div className="w-6 h-6 sm:w-8 sm:h-8 rounded-full bg-primary-container/20 flex items-center justify-center shrink-0">
          <span className="material-symbols-outlined text-primary text-[16px] sm:text-[20px]">child_care</span>
        </div>
        <span className="text-xs sm:text-label-md font-label-md text-on-surface truncate max-w-[85px] sm:max-w-none">{displayText}</span>
        <span className="material-symbols-outlined text-on-surface-variant text-[14px] sm:text-[20px] shrink-0">
          {isOpen ? 'keyboard_arrow_up' : 'keyboard_arrow_down'}
        </span>
      </button>

      {isOpen && (
        <div className="absolute top-full mt-2 left-1/2 -translate-x-1/2 w-56 sm:w-64 bg-surface dark:bg-surface-container-high border border-black/5 dark:border-white/5 rounded-xl shadow-soft dark:shadow-soft-dark overflow-hidden z-50 flex flex-col">
          <div className="max-h-60 overflow-y-auto py-1">
            {/* Guest Mode option */}
            <button
              onClick={() => handleSelect(null)}
              className={`w-full text-left px-3 py-2.5 sm:py-3 text-xs sm:text-sm font-medium hover:bg-surface-container transition-colors flex items-center gap-2 ${isGuest ? 'bg-primary-container/10 text-primary font-bold' : 'text-on-surface'}`}
            >
              <div className="w-5 h-5 sm:w-6 sm:h-6 rounded-full bg-surface-variant flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined text-[16px] sm:text-[20px]">person</span>
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
                  className={`w-full text-left px-3 py-2.5 sm:py-3 text-xs sm:text-sm font-medium transition-colors flex items-center gap-2 ${selectedProfileId === p.profile_id ? 'bg-primary-container/30 text-primary font-bold' : 'text-on-surface hover:bg-surface-container-low dark:hover:bg-surface-container'}`}
                >
                  <div className="w-5 h-5 sm:w-6 sm:h-6 rounded-full bg-primary-container/20 flex items-center justify-center shrink-0">
                    <span className="material-symbols-outlined text-primary text-[16px] sm:text-[20px]">child_care</span>
                  </div>
                  <span className="truncate">{p.nickname} - {ageStr}</span>
                </button>
              )
            })}
          </div>

          <div className="border-t border-black/5 dark:border-white/5 bg-surface-container/30 p-1.5 sm:p-2 flex flex-col gap-1">
            <button
              onClick={handleManage}
              className="w-full text-left px-2 py-2 sm:py-2.5 text-xs sm:text-sm text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low dark:hover:bg-surface-container rounded-lg transition-colors flex items-center gap-2 font-medium"
            >
              <span className="material-symbols-outlined text-[18px]">manage_accounts</span> Manage Profiles
            </button>
            <button
              onClick={handleCreateNew}
              className="w-full text-left px-2 py-2 text-xs sm:text-sm text-primary font-bold hover:bg-primary-container/20 rounded-lg transition-colors flex items-center gap-1"
            > + Create New Profile
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
