import { useState, useEffect } from 'react'
import { profileApi } from '../api/client'
import ProfileForm from '../components/Profiles/ProfileForm'
import { ageDaysFromDob, ageDaysToDisplay, isProfileStale } from '../utils/ageUtils'

export default function ProfilesPage() {
  const [profiles, setProfiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [isEditing, setIsEditing] = useState(false)
  const [currentProfile, setCurrentProfile] = useState(null)

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
  }, [])

  const handleCreate = () => {
    setCurrentProfile(null)
    setIsEditing(true)
  }

  const handleEdit = (profile) => {
    setCurrentProfile(profile)
    setIsEditing(true)
  }

  const handleDelete = async (profileId) => {
    if (!window.confirm('Are you sure you want to delete this profile?')) return
    try {
      await profileApi.delete(profileId)
      await loadProfiles()
    } catch (err) {
      console.error('Failed to delete profile', err)
    }
  }

  const handleFormSubmit = async (data) => {
    try {
      if (currentProfile) {
        await profileApi.update(currentProfile.profile_id, data)
      } else {
        await profileApi.create(data)
      }
      setIsEditing(false)
      await loadProfiles()
    } catch (err) {
      console.error('Failed to save profile', err)
      alert('Failed to save profile. Please try again.')
    }
  }

  if (loading) {
    return <div className="page container flex justify-center py-10"><div className="spinner" /></div>
  }

  return (
    <div className="page container">
      <div className="flex justify-between items-center mb-6">
        <h2>Child Profiles</h2>
        {!isEditing && (
          <button className="btn btn-primary" onClick={handleCreate}>
            + Add Profile
          </button>
        )}
      </div>

      {isEditing ? (
        <div className="max-w-[600px] mx-auto">
          <h3 className="mb-4">{currentProfile ? 'Edit Profile' : 'New Profile'}</h3>
          <ProfileForm 
            initialData={currentProfile} 
            onSubmit={handleFormSubmit}
            onCancel={() => setIsEditing(false)}
          />
        </div>
      ) : (
        <div className="feature-grid">
          {profiles.length === 0 ? (
            <div className="col-span-full text-center p-10 bg-bgCard rounded-lg">
              <p className="text-gray-400 mb-4">You haven't created any profiles yet.</p>
              <button className="btn btn-primary" onClick={handleCreate}>Create Your First Profile</button>
            </div>
          ) : (
            profiles.map(p => {
              const ageDays = ageDaysFromDob(p.dob)
              const ageStr = ageDaysToDisplay(ageDays)
              const stale = isProfileStale(p.last_updated)

              return (
                <div key={p.profile_id} className="card flex flex-col justify-between">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-teal-400 mb-1">{p.nickname}</h3>
                      <div className="tag tag--teal">{ageStr}</div>
                    </div>
                  </div>

                  <div className="text-[0.875rem] text-gray-200 mb-4 flex flex-col gap-2 flex-1">
                    <p><strong>DOB:</strong> {p.dob}</p>
                    <p><strong>Gender:</strong> {p.gender}</p>
                    {p.weight_kg > 0 && <p><strong>Weight:</strong> {p.weight_kg} kg</p>}
                    {p.medical_conditions?.length > 0 && (
                      <p><strong>Conditions:</strong> {p.medical_conditions.join(', ')}</p>
                    )}
                  </div>

                  {stale && (
                    <div className="alert alert--warning text-xs p-2 mb-4">
                      ⚠️ Please review and update weight/conditions.
                    </div>
                  )}

                  <div className="flex gap-2 border-t border-white/5 pt-4">
                    <button className="btn btn-secondary btn-sm flex-1" onClick={() => handleEdit(p)}>Edit</button>
                    <button className="btn btn-danger btn-sm flex-1" onClick={() => handleDelete(p.profile_id)}>Delete</button>
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}
