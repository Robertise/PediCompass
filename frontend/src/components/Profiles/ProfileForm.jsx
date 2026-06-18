import { useState, useEffect } from 'react'

export default function ProfileForm({ initialData, onSubmit, onCancel }) {
  const [formData, setFormData] = useState({
    nickname: '',
    dob: '',
    gender: 'Unknown',
    weight_kg: '',
    medical_conditions: ''
  })

  useEffect(() => {
    if (initialData) {
      setFormData({
        nickname: initialData.nickname || '',
        dob: initialData.dob || '',
        gender: initialData.gender || 'Unknown',
        weight_kg: initialData.weight_kg || '',
        medical_conditions: (initialData.medical_conditions || []).join(', ')
      })
    }
  }, [initialData])

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    
    // Process conditions string into array
    const conditionsArray = formData.medical_conditions
      .split(',')
      .map(s => s.trim())
      .filter(s => s.length > 0)

    onSubmit({
      nickname: formData.nickname,
      dob: formData.dob,
      gender: formData.gender,
      weight_kg: parseFloat(formData.weight_kg) || 0.0,
      medical_conditions: conditionsArray
    })
  }

  return (
    <form onSubmit={handleSubmit} className="form-group bg-bgElevated p-6 rounded-lg">
      <div>
        <label className="input-label">Child's Name / Nickname</label>
        <input 
          type="text" 
          name="nickname"
          className="input" 
          value={formData.nickname}
          onChange={handleChange}
          required 
        />
      </div>
      
      <div>
        <label className="input-label">Date of Birth</label>
        <input 
          type="date" 
          name="dob"
          className="input" 
          value={formData.dob}
          onChange={handleChange}
          required 
          max={new Date().toISOString().split('T')[0]} // Cannot be in future
        />
      </div>

      <div>
        <label className="input-label">Gender</label>
        <select 
          name="gender" 
          className="input" 
          value={formData.gender}
          onChange={handleChange}
        >
          <option value="Unknown">Prefer not to say</option>
          <option value="Male">Male</option>
          <option value="Female">Female</option>
          <option value="Other">Other</option>
        </select>
      </div>

      <div>
        <label className="input-label">Weight (kg) - Optional</label>
        <input 
          type="number" 
          name="weight_kg"
          step="0.1"
          className="input" 
          value={formData.weight_kg}
          onChange={handleChange}
        />
      </div>

      <div>
        <label className="input-label">Medical Conditions (comma separated) - Optional</label>
        <input 
          type="text" 
          name="medical_conditions"
          className="input" 
          placeholder="e.g. Asthma, Eczema"
          value={formData.medical_conditions}
          onChange={handleChange}
        />
      </div>

      <div className="flex gap-3 mt-4 justify-end">
        <button type="button" className="btn btn-secondary" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary">
          Save Profile
        </button>
      </div>
    </form>
  )
}
