import { useState } from 'react'
import { useAuthStore } from '../../store/authStore'

export default function RegisterPage({ onToggleMode }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { register, isLoading, error, clearError } = useAuthStore()
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    clearError()
    const res = await register(email, password)
    if (res.success) {
      setSuccess(true)
    }
  }

  if (success) {
    return (
      <div className="auth-card text-center">
        <h2 className="mb-4">Registration Successful!</h2>
        <p className="text-gray-200 mb-6">
          Please check your email to verify your account. Once verified, you can sign in.
        </p>
        <button onClick={onToggleMode} className="btn btn-primary w-full">
          Go to Sign In
        </button>
      </div>
    )
  }

  return (
    <div className="auth-card">
      <h2 className="text-center mb-6">Create Account</h2>
      
      {error && <div className="alert alert--emergency mb-4">{error}</div>}

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
            minLength={8}
          />
        </div>
        <button type="submit" className="btn btn-primary w-full mt-4" disabled={isLoading}>
          {isLoading ? 'Creating...' : 'Create Account'}
        </button>
      </form>

      <p className="text-center mt-6 text-sm">
        Already have an account?{' '}
        <button onClick={onToggleMode} className="btn-ghost p-0">
          Sign in
        </button>
      </p>
    </div>
  )
}
