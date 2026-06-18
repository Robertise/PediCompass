import { useState } from 'react'
import { useAuthStore } from '../../store/authStore'
import { useAppStore } from '../../store/appStore'

export default function AuthModal() {
  const { showAuthModal, setShowAuthModal } = useAppStore()
  const { login, register, isLoading, error, clearError } = useAuthStore()
  const [mode, setMode] = useState('login') // 'login' or 'register'
  const [success, setSuccess] = useState(false)
  
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  if (!showAuthModal) return null

  const handleClose = () => {
    setShowAuthModal(false)
    clearError()
    setMode('login')
    setSuccess(false)
    setEmail('')
    setPassword('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    clearError()
    if (mode === 'login') {
      const res = await login(email, password)
      if (res.success) {
        handleClose()
      }
    } else {
      const res = await register(email, password)
      if (res.success) {
        setSuccess(true)
      }
    }
  }

  const toggleMode = () => {
    setMode(mode === 'login' ? 'register' : 'login')
    clearError()
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-inverse-surface/40 backdrop-blur-sm p-4">
      <div className="bg-surface-container-lowest rounded-[24px] shadow-[0_8px_32px_rgba(0,0,0,0.08)] w-full max-w-md overflow-hidden flex flex-col border border-outline-variant/20 relative">
        <button 
          onClick={handleClose}
          className="absolute top-4 right-4 text-on-surface-variant hover:text-on-surface hover:bg-surface-container p-2 rounded-full transition-colors flex items-center justify-center"
        >
          <span className="material-symbols-outlined text-[20px]">close</span>
        </button>
        
        <div className="p-md sm:p-lg flex flex-col gap-md">
          <div className="text-center">
            <h2 className="text-headline-md font-headline-md font-bold text-on-surface mb-xs">
              {success ? 'Registration Successful!' : mode === 'login' ? 'Welcome Back' : 'Create Account'}
            </h2>
            <p className="text-body-sm font-body-sm text-on-surface-variant">
              {success 
                ? 'Please check your email to verify your account.' 
                : mode === 'login' 
                  ? 'Sign in to sync your profiles and history.' 
                  : 'Join PediCompass for personalized guidance.'}
            </p>
          </div>

          {error && (
            <div className="bg-error-container/20 border border-error/20 text-error p-sm rounded-lg text-body-sm font-body-sm text-center">
              {error}
            </div>
          )}

          {!success ? (
            <form onSubmit={handleSubmit} className="flex flex-col gap-sm">
              <div className="flex flex-col gap-xs">
                <label className="text-label-md font-label-md text-on-surface">Email</label>
                <input 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-surface-container-low border border-outline-variant/40 rounded-lg px-sm py-xs text-body-md font-body-md focus:border-primary focus:ring-1 focus:ring-primary transition-colors outline-none"
                  required 
                />
              </div>
              <div className="flex flex-col gap-xs">
                <label className="text-label-md font-label-md text-on-surface">Password</label>
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="bg-surface-container-low border border-outline-variant/40 rounded-lg px-sm py-xs text-body-md font-body-md focus:border-primary focus:ring-1 focus:ring-primary transition-colors outline-none"
                  required 
                  minLength={mode === 'register' ? 8 : undefined}
                />
              </div>
              
              <button 
                type="submit" 
                disabled={isLoading}
                className="mt-xs bg-primary hover:bg-primary-fixed-variant text-on-primary rounded-full py-xs px-md text-label-md font-label-md font-bold transition-colors disabled:opacity-50"
              >
                {isLoading ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}
              </button>
            </form>
          ) : (
            <button 
              onClick={() => { setSuccess(false); setMode('login'); }} 
              className="bg-primary hover:bg-primary-fixed-variant text-on-primary rounded-full py-xs px-md text-label-md font-label-md font-bold transition-colors"
            >
              Go to Sign In
            </button>
          )}

          {!success && (
            <p className="text-center text-body-sm font-body-sm text-on-surface-variant mt-xs">
              {mode === 'login' ? "Don't have an account? " : "Already have an account? "}
              <button 
                onClick={toggleMode} 
                className="text-primary font-bold hover:underline bg-transparent border-none p-0 cursor-pointer"
              >
                {mode === 'login' ? 'Sign up' : 'Log in'}
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
