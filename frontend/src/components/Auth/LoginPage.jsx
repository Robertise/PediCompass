import { useState } from 'react'
import { useAuthStore } from '../../store/authStore'
import { useNavigate } from 'react-router-dom'

export default function LoginPage({ onToggleMode }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { login, isLoading, error, clearError } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    clearError()
    const res = await login(email, password)
    if (res.success) {
      navigate('/chat')
    }
  }

  return (
    <div className="auth-card">
      <h2 style={{ textAlign: 'center', marginBottom: '24px' }}>Welcome Back</h2>
      
      {error && <div className="alert alert--emergency" style={{ marginBottom: '16px' }}>{error}</div>}

      <form onSubmit={handleSubmit} className="form-group">
        <div>
          <label className="input-label">Email</label>
          <input 
            type="email" 
            className="input" 
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required 
          />
        </div>
        <div>
          <label className="input-label">Password</label>
          <input 
            type="password" 
            className="input" 
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required 
          />
        </div>
        <button type="submit" className="btn btn-primary w-full" disabled={isLoading} style={{ marginTop: '16px' }}>
          {isLoading ? 'Signing in...' : 'Sign In'}
        </button>
      </form>

      <p style={{ textAlign: 'center', marginTop: '24px', fontSize: '0.875rem' }}>
        Don't have an account?{' '}
        <button onClick={onToggleMode} className="btn-ghost" style={{ padding: 0 }}>
          Create one
        </button>
      </p>
    </div>
  )
}
