import { useState } from 'react'
import LoginPage from '../components/Auth/LoginPage'
import RegisterPage from '../components/Auth/RegisterPage'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

export default function AuthPage() {
  const [mode, setMode] = useState('login')
  const { user } = useAuthStore()

  if (user) {
    return <Navigate to="/chat" replace />
  }

  return (
    <div className="auth-page">
      {mode === 'login' ? (
        <LoginPage onToggleMode={() => setMode('register')} />
      ) : (
        <RegisterPage onToggleMode={() => setMode('login')} />
      )}
    </div>
  )
}
