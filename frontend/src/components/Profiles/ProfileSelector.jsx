import { useState, useEffect } from 'react'
import { profileApi } from '../../api/client'
import { ageDaysFromDob, ageDaysToDisplay } from '../../utils/ageUtils'

export default function ProfileSelector({ selectedId, onChange, disabled }) {
  const [profiles, setProfiles] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadProfiles() {
      try {
        const res = await profileApi.list()
        setProfiles(res.data)
        // Auto-select first profile if none selected
        if (res.data.length > 0 && !selectedId && !disabled) {
          onChange(res.data[0].profile_id)
        }
      } catch (err) {
        console.error('Failed to load profiles', err)
      } finally {
        setLoading(false)
      }
    }
    loadProfiles()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) return <div className="skeleton h-[42px] w-[200px]" />

  if (profiles.length === 0) {
    return (
      <div className="text-sm text-gray-400">
        No profiles found. You can chat as a guest or create a profile first.
      </div>
    )
  }

  return (
    <div className="flex items-center gap-3">
      <label className="text-sm text-gray-200">
        Chatting about:
      </label>
      <select 
        className="profile-select w-auto min-w-[200px]"
        value={selectedId || ''} 
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      >
        <option value="">-- Guest (No Profile) --</option>
        {profiles.map(p => {
          const ageDays = ageDaysFromDob(p.dob)
          const ageStr = ageDaysToDisplay(ageDays)
          return (
            <option key={p.profile_id} value={p.profile_id}>
              {p.nickname} ({ageStr})
            </option>
          )
        })}
      </select>
    </div>
  )
}
