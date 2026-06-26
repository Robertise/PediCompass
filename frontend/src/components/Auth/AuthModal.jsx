import { useState } from 'react'
import { useAuthStore } from '../../store/authStore'
import { useAppStore } from '../../store/appStore'

export default function AuthModal() {
  const { showAuthModal, setShowAuthModal } = useAppStore()
  const { login, register, confirm, resendCode, isLoading, error, clearError } = useAuthStore()
  const [mode, setMode] = useState('login') // 'login', 'register', or 'confirm'
  const [success, setSuccess] = useState(false)
  const [infoMessage, setInfoMessage] = useState('')
  
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')

  if (!showAuthModal) return null

  const handleClose = () => {
    setShowAuthModal(false)
    clearError()
    setInfoMessage('')
    setMode('login')
    setSuccess(false)
    setEmail('')
    setPassword('')
    setCode('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    clearError()
    setInfoMessage('')
    if (mode === 'login') {
      const res = await login(email, password)
      if (res.success) {
        handleClose()
      }
    } else if (mode === 'register') {
      const res = await register(email, password)
      if (res.success) {
        setMode('confirm')
      }
    } else if (mode === 'confirm') {
      const res = await confirm(email, code)
      if (res.success) {
        setSuccess(true)
        setMode('login')
      }
    }
  }

  const handleResendCode = async () => {
    clearError()
    setInfoMessage('')
    const res = await resendCode(email)
    if (res.success) {
      setInfoMessage('Verification code resent successfully!')
    }
  }

  const toggleMode = () => {
    setMode(mode === 'login' ? 'register' : 'login')
    clearError()
    setInfoMessage('')
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
              {success 
                ? 'Account Verified!' 
                : mode === 'login' 
                  ? 'Welcome Back' 
                  : mode === 'register' 
                    ? 'Create Account' 
                    : 'Verify Email'}
            </h2>
            <p className="text-body-sm font-body-sm text-on-surface-variant">
              {success 
                ? 'Your email has been verified. You can now log in.' 
                : mode === 'login' 
                  ? 'Sign in to sync your profiles and history.' 
                  : mode === 'register' 
                    ? 'Join PediCompass for personalized guidance.'
                    : `We sent a 6-digit confirmation code to ${email}`}
            </p>
          </div>

          {error && (
            <div className="bg-error-container/20 border border-error/20 text-error p-sm rounded-lg text-body-sm font-body-sm text-center">
              {error}
            </div>
          )}

          {infoMessage && (
            <div className="bg-primary-container/20 border border-primary/20 text-primary p-sm rounded-lg text-body-sm font-body-sm text-center">
              {infoMessage}
            </div>
          )}

          {!success ? (
            <form onSubmit={handleSubmit} className="flex flex-col gap-sm">
              {mode !== 'confirm' && (
                <>
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
                </>
              )}

              {mode === 'confirm' && (
                <div className="flex flex-col gap-xs">
                  <label className="text-label-md font-label-md text-on-surface">Verification Code</label>
                  <input 
                    type="text" 
                    placeholder="123456"
                    maxLength={6}
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                    className="bg-surface-container-low border border-outline-variant/40 rounded-lg px-sm py-xs text-body-md font-body-md focus:border-primary focus:ring-1 focus:ring-primary transition-colors outline-none text-center tracking-[1em] text-lg font-bold"
                    required 
                  />
                </div>
              )}
              
              <button 
                type="submit" 
                disabled={isLoading}
                className="mt-xs bg-primary hover:bg-primary-fixed-variant text-on-primary rounded-full py-xs px-md text-label-md font-label-md font-bold transition-colors disabled:opacity-50"
              >
                {isLoading ? 'Please wait...' : mode === 'login' ? 'Sign In' : mode === 'register' ? 'Create Account' : 'Verify Account'}
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
            <div className="flex flex-col items-center gap-xs mt-xs text-body-sm font-body-sm text-on-surface-variant">
              {mode !== 'confirm' ? (
                <p>
                  {mode === 'login' ? "Don't have an account? " : "Already have an account? "}
                  <button 
                    onClick={toggleMode} 
                    className="text-primary font-bold hover:underline bg-transparent border-none p-0 cursor-pointer"
                  >
                    {mode === 'login' ? 'Sign up' : 'Log in'}
                  </button>
                </p>
              ) : (
                <>
                  <p>
                    Didn't receive the code?{' '}
                    <button 
                      type="button"
                      onClick={handleResendCode} 
                      disabled={isLoading}
                      className="text-primary font-bold hover:underline bg-transparent border-none p-0 cursor-pointer disabled:opacity-50"
                    >
                      Resend code
                    </button>
                  </p>
                  <button 
                    type="button"
                    onClick={() => { setMode('register'); clearError(); setInfoMessage(''); }}
                    className="text-primary font-bold hover:underline bg-transparent border-none p-0 cursor-pointer mt-xs"
                  >
                    Back to Registration
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
