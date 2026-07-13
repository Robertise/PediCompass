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
      <div className="bg-surface dark:bg-surface-container-high rounded-[24px] shadow-soft-lg dark:shadow-soft-dark w-full max-w-lg overflow-hidden flex flex-col relative max-h-[90vh]">
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

          <form onSubmit={handleSubmit} className="flex flex-col gap-[14px]">
            <div className="flex flex-col bg-surface-container dark:bg-black/20 rounded-xl px-4 py-2 focus-within:ring-2 focus-within:ring-primary/30 transition-all">
              <label className="text-[11px] font-label-sm text-on-surface-variant font-bold mb-0.5">Child's Name / Nickname</label>
              <input 
                type="text" 
                name="nickname"
                value={formData.nickname}
                onChange={handleChange}
                className="bg-transparent border-none outline-none p-0 text-body-md font-body-md text-on-surface w-full focus:ring-0"
                required 
              />
            </div>
            
            <div className="flex flex-col bg-surface-container dark:bg-black/20 rounded-xl px-4 py-2 focus-within:ring-2 focus-within:ring-primary/30 transition-all">
              <label className="text-[11px] font-label-sm text-on-surface-variant font-bold mb-0.5">Date of Birth</label>
              <input 
                type="date" 
                name="dob"
                value={formData.dob}
                onChange={handleChange}
                className="bg-transparent border-none outline-none p-0 text-body-md font-body-md text-on-surface w-full focus:ring-0 dark:[color-scheme:dark]"
                required 
                max={new Date().toISOString().split('T')[0]}
              />
            </div>

            <div className="flex flex-col bg-surface-container dark:bg-black/20 rounded-xl px-4 py-2 focus-within:ring-2 focus-within:ring-primary/30 transition-all">
              <label className="text-[11px] font-label-sm text-on-surface-variant font-bold mb-0.5">Gender</label>
              <select 
                name="gender" 
                value={formData.gender}
                onChange={handleChange}
                className="bg-transparent border-none outline-none p-0 pr-6 bg-[position:right_0_center] text-body-md font-body-md text-on-surface w-full focus:ring-0 cursor-pointer dark:[color-scheme:dark]"
              >
                <option value="Unknown" className="bg-surface dark:bg-surface-container-high text-on-surface">Prefer not to say</option>
                <option value="Male" className="bg-surface dark:bg-surface-container-high text-on-surface">Male</option>
                <option value="Female" className="bg-surface dark:bg-surface-container-high text-on-surface">Female</option>
                <option value="Other" className="bg-surface dark:bg-surface-container-high text-on-surface">Other</option>
              </select>
            </div>

            <div className="flex flex-col bg-surface-container dark:bg-black/20 rounded-xl px-4 py-2 focus-within:ring-2 focus-within:ring-primary/30 transition-all">
              <label className="text-[11px] font-label-sm text-on-surface-variant font-bold mb-0.5">Weight (kg) - Optional</label>
              <input 
                type="number" 
                name="weight_kg"
                step="0.1"
                min="2"
                value={formData.weight_kg}
                onChange={handleChange}
                className="bg-transparent border-none outline-none p-0 text-body-md font-body-md text-on-surface w-full focus:ring-0"
              />
            </div>

            <div className="flex flex-col bg-surface-container dark:bg-black/20 rounded-xl px-4 py-2 focus-within:ring-2 focus-within:ring-primary/30 transition-all">
              <label className="text-[11px] font-label-sm text-on-surface-variant font-bold mb-0.5">Medical Conditions (comma separated) - Optional</label>
              <input 
                type="text" 
                name="medical_conditions"
                placeholder="e.g. Asthma, Eczema"
                value={formData.medical_conditions}
                onChange={handleChange}
                className="bg-transparent border-none outline-none p-0 text-body-md font-body-md text-on-surface w-full focus:ring-0 placeholder:text-outline-variant/60"
              />
            </div>

            <div className="flex gap-sm mt-sm justify-end">
              <button 
                type="button" 
                onClick={handleClose}
                className="text-on-surface-variant hover:bg-surface-container px-6 py-3.5 rounded-full text-label-md font-label-md transition-colors font-bold"
              >
                Cancel
              </button>
              <button 
                type="submit" 
                disabled={loading}
                className="bg-primary hover:bg-primary-fixed-variant text-on-primary px-6 py-3.5 rounded-full text-label-md font-label-md font-bold transition-colors disabled:opacity-50 shadow-sm"
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
