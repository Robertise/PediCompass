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
    return <div className="page container"><div className="spinner" style={{ margin: '40px auto' }}/></div>
  }

  return (
    <div className="page container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2>Child Profiles</h2>
        {!isEditing && (
          <button className="btn btn-primary" onClick={handleCreate}>
            + Add Profile
          </button>
        )}
      </div>

      {isEditing ? (
        <div style={{ maxWidth: '600px', margin: '0 auto' }}>
          <h3 style={{ marginBottom: '16px' }}>{currentProfile ? 'Edit Profile' : 'New Profile'}</h3>
          <ProfileForm 
            initialData={currentProfile} 
            onSubmit={handleFormSubmit}
            onCancel={() => setIsEditing(false)}
          />
        </div>
      ) : (
        <div className="feature-grid">
          {profiles.length === 0 ? (
            <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '40px', background: 'var(--color-bg-card)', borderRadius: 'var(--radius-lg)' }}>
              <p style={{ color: 'var(--color-gray-400)', marginBottom: '16px' }}>You haven't created any profiles yet.</p>
              <button className="btn btn-primary" onClick={handleCreate}>Create Your First Profile</button>
            </div>
          ) : (
            profiles.map(p => {
              const ageDays = ageDaysFromDob(p.dob)
              const ageStr = ageDaysToDisplay(ageDays)
              const stale = isProfileStale(p.last_updated)

              return (
                <div key={p.profile_id} className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                    <div>
                      <h3 style={{ color: 'var(--color-teal)', marginBottom: '4px' }}>{p.nickname}</h3>
                      <div className="tag tag--teal">{ageStr}</div>
                    </div>
                  </div>

                  <div style={{ fontSize: '0.875rem', color: 'var(--color-gray-200)', marginBottom: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <p><strong>DOB:</strong> {p.dob}</p>
                    <p><strong>Gender:</strong> {p.gender}</p>
                    {p.weight_kg > 0 && <p><strong>Weight:</strong> {p.weight_kg} kg</p>}
                    {p.medical_conditions?.length > 0 && (
                      <p><strong>Conditions:</strong> {p.medical_conditions.join(', ')}</p>
                    )}
                  </div>

                  {stale && (
                    <div className="alert alert--warning" style={{ fontSize: '0.75rem', padding: '8px', marginBottom: '16px' }}>
                      ⚠️ Please review and update weight/conditions.
                    </div>
                  )}

                  <div style={{ display: 'flex', gap: '8px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '16px' }}>
                    <button className="btn btn-secondary btn-sm" style={{ flex: 1 }} onClick={() => handleEdit(p)}>Edit</button>
                    <button className="btn btn-danger btn-sm" style={{ flex: 1 }} onClick={() => handleDelete(p.profile_id)}>Delete</button>
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
