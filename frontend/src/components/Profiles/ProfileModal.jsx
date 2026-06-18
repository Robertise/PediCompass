import { useState, useEffect } from 'react'
import { useAppStore } from '../../store/appStore'
import { profileApi } from '../../api/client'

export default function ProfileModal() {
  const { showProfileModal, setShowProfileModal, editingProfile, setEditingProfile, setSelectedProfileId } = useAppStore()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  const [formData, setFormData] = useState({
    nickname: '',
    dob: '',
    gender: 'Unknown',
    weight_kg: '',
    medical_conditions: ''
  })

  useEffect(() => {
    if (showProfileModal) {
      if (editingProfile) {
        setFormData({
          nickname: editingProfile.nickname || '',
          dob: editingProfile.dob || '',
          gender: editingProfile.gender || 'Unknown',
          weight_kg: editingProfile.weight_kg || '',
          medical_conditions: (editingProfile.medical_conditions || []).join(', ')
        })
      } else {
        setFormData({
          nickname: '',
          dob: '',
          gender: 'Unknown',
          weight_kg: '',
          medical_conditions: ''
        })
      }
      setError(null)
    }
  }, [showProfileModal, editingProfile])

  if (!showProfileModal) return null

  const handleClose = () => {
    setShowProfileModal(false)
    setEditingProfile(null)
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    
    const conditionsArray = formData.medical_conditions
      .split(',')
      .map(s => s.trim())
      .filter(s => s.length > 0)

    const payload = {
      nickname: formData.nickname,
      dob: formData.dob,
      gender: formData.gender,
      weight_kg: parseFloat(formData.weight_kg) || 0.0,
      medical_conditions: conditionsArray
    }

    try {
      if (editingProfile) {
        await profileApi.update(editingProfile.profile_id, payload)
      } else {
        const res = await profileApi.create(payload)
        // Auto-select the newly created profile
        if (res.data && res.data.profile_id) {
          setSelectedProfileId(res.data.profile_id)
        }
      }
      handleClose()
      // We might need to trigger a re-fetch in ProfileSelector or ProfilesPage, 
      // but usually ProfileSelector fetches on mount or depends on something else.
      // For a SPA without a global query cache like react-query, we can just rely on the component remounting 
      // or we can pass a callback, but we will just reload window or manage it via state if needed.
      // Easiest is to force a re-fetch in ProfileSelector by updating a timestamp in appStore if necessary.
      window.dispatchEvent(new Event('profilesUpdated'))
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save profile.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-inverse-surface/40 backdrop-blur-sm p-4">
      <div className="bg-surface-container-lowest rounded-[24px] shadow-[0_8px_32px_rgba(0,0,0,0.08)] w-full max-w-lg overflow-hidden flex flex-col border border-outline-variant/20 relative max-h-[90vh]">
        <button 
          onClick={handleClose}
          className="absolute top-4 right-4 text-on-surface-variant hover:text-on-surface hover:bg-surface-container p-2 rounded-full transition-colors flex items-center justify-center z-10"
        >
          <span className="material-symbols-outlined text-[20px]">close</span>
        </button>
        
        <div className="p-md sm:p-lg flex flex-col gap-md overflow-y-auto">
          <div className="text-center">
            <h2 className="text-headline-md font-headline-md font-bold text-on-surface mb-xs">
              {editingProfile ? 'Edit Profile' : 'New Profile'}
            </h2>
            <p className="text-body-sm font-body-sm text-on-surface-variant">
              Provide basic information to get tailored care pathways.
            </p>
          </div>

          {error && (
            <div className="bg-error-container/20 border border-error/20 text-error p-sm rounded-lg text-body-sm font-body-sm text-center">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-sm">
            <div className="flex flex-col gap-xs">
              <label className="text-label-md font-label-md text-on-surface">Child's Name / Nickname</label>
              <input 
                type="text" 
                name="nickname"
                value={formData.nickname}
                onChange={handleChange}
                className="bg-surface-container-low border border-outline-variant/40 rounded-lg px-sm py-xs text-body-md font-body-md focus:border-primary focus:ring-1 focus:ring-primary transition-colors outline-none"
                required 
              />
            </div>
            
            <div className="flex flex-col gap-xs">
              <label className="text-label-md font-label-md text-on-surface">Date of Birth</label>
              <input 
                type="date" 
                name="dob"
                value={formData.dob}
                onChange={handleChange}
                className="bg-surface-container-low border border-outline-variant/40 rounded-lg px-sm py-xs text-body-md font-body-md focus:border-primary focus:ring-1 focus:ring-primary transition-colors outline-none"
                required 
                max={new Date().toISOString().split('T')[0]}
              />
            </div>

            <div className="flex flex-col gap-xs">
              <label className="text-label-md font-label-md text-on-surface">Gender</label>
              <select 
                name="gender" 
                value={formData.gender}
                onChange={handleChange}
                className="bg-surface-container-low border border-outline-variant/40 rounded-lg px-sm py-xs text-body-md font-body-md focus:border-primary focus:ring-1 focus:ring-primary transition-colors outline-none"
              >
                <option value="Unknown">Prefer not to say</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
              </select>
            </div>

            <div className="flex flex-col gap-xs">
              <label className="text-label-md font-label-md text-on-surface">Weight (kg) - Optional</label>
              <input 
                type="number" 
                name="weight_kg"
                step="0.1"
                value={formData.weight_kg}
                onChange={handleChange}
                className="bg-surface-container-low border border-outline-variant/40 rounded-lg px-sm py-xs text-body-md font-body-md focus:border-primary focus:ring-1 focus:ring-primary transition-colors outline-none"
              />
            </div>

            <div className="flex flex-col gap-xs">
              <label className="text-label-md font-label-md text-on-surface">Medical Conditions (comma separated) - Optional</label>
              <input 
                type="text" 
                name="medical_conditions"
                placeholder="e.g. Asthma, Eczema"
                value={formData.medical_conditions}
                onChange={handleChange}
                className="bg-surface-container-low border border-outline-variant/40 rounded-lg px-sm py-xs text-body-md font-body-md focus:border-primary focus:ring-1 focus:ring-primary transition-colors outline-none"
              />
            </div>

            <div className="flex gap-sm mt-xs justify-end">
              <button 
                type="button" 
                onClick={handleClose}
                className="bg-surface-variant hover:bg-outline-variant/30 text-on-surface rounded-full py-xs px-md text-label-md font-label-md transition-colors"
              >
                Cancel
              </button>
              <button 
                type="submit" 
                disabled={loading}
                className="bg-primary hover:bg-primary-fixed-variant text-on-primary rounded-full py-xs px-md text-label-md font-label-md font-bold transition-colors disabled:opacity-50"
              >
                {loading ? 'Saving...' : 'Save Profile'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
