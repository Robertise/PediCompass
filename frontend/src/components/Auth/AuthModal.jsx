import { useState, useEffect, useRef } from 'react'
import { useAuthStore } from '../../store/authStore'
import { useAppStore } from '../../store/appStore'

// ── Password policy (must match Cognito User Pool settings) ──────────────────
const PASSWORD_RULES = [
  { id: 'length',    label: 'At least 8 characters',      test: (p) => p.length >= 8 },
  { id: 'uppercase', label: 'One uppercase letter (A–Z)',  test: (p) => /[A-Z]/.test(p) },
  { id: 'lowercase', label: 'One lowercase letter (a–z)',  test: (p) => /[a-z]/.test(p) },
  { id: 'number',    label: 'One number (0–9)',            test: (p) => /[0-9]/.test(p) },
  { id: 'special',   label: 'One special character (!@#$…)', test: (p) => /[^A-Za-z0-9]/.test(p) },
]

const maskEmail = (email) => {
  const [user, domain] = email.split('@')
  if (!domain) return email
  const visible = user.slice(0, 2)
  return `${visible}${'*'.repeat(Math.max(1, user.length - 2))}@${domain}`
}

// ── Sub-components ────────────────────────────────────────────────────────────

function PasswordChecklist({ password, show }) {
  if (!show) return null
  return (
    <ul className="flex flex-col gap-[4px] mt-xs">
      {PASSWORD_RULES.map((rule) => {
        const pass = rule.test(password)
        return (
          <li key={rule.id} className={`flex items-center gap-xs text-label-sm font-label-sm transition-colors ${pass ? 'text-emerald-500' : 'text-on-surface-variant/60'}`}>
            <span className="material-symbols-outlined text-[14px]">
              {pass ? 'check_circle' : 'radio_button_unchecked'}
            </span>
            {rule.label}
          </li>
        )
      })}
    </ul>
  )
}

function ErrorBanner({ message, onVerify }) {
  if (!message) return null
  return (
    <div className="bg-error-container/20 border border-error/20 text-error p-sm rounded-lg text-body-sm font-body-sm text-center flex flex-col gap-xs">
      <span>{message}</span>
      {onVerify && (
        <button
          type="button"
          onClick={onVerify}
          className="text-primary font-bold hover:underline text-label-sm self-center"
        >
          Enter verification code →
        </button>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function AuthModal() {
  const { showAuthModal, setShowAuthModal } = useAppStore()
  const { login, register, verify, resendCode, isLoading, error, clearError } = useAuthStore()

  // mode: 'login' | 'register' | 'verify'
  const [mode, setMode] = useState('login')
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode]         = useState('')

  // Track whether password field has been touched (to show checklist)
  const [passwordTouched, setPasswordTouched] = useState(false)
  // Tracks the login error code so we can show contextual actions
  const [loginErrorCode, setLoginErrorCode] = useState(null)

  // Resend cooldown: countdown in seconds (0 = button active)
  const [resendCooldown, setResendCooldown] = useState(0)
  const cooldownRef = useRef(null)

  // Success banner in 'verify' → 'login' transition
  const [verifySuccess, setVerifySuccess] = useState(false)

  if (!showAuthModal) return null

  // ── Derived state ──────────────────────────────────────────────────────────

  const passwordValid = PASSWORD_RULES.every((r) => r.test(password))

  const canSubmitRegister = email.trim() !== '' && passwordValid
  const canSubmitLogin    = email.trim() !== '' && password.trim() !== ''
  const canSubmitVerify   = code.trim().length === 6

  // ── Handlers ───────────────────────────────────────────────────────────────

  const resetModal = () => {
    setMode('login')
    setEmail('')
    setPassword('')
    setCode('')
    setPasswordTouched(false)
    setLoginErrorCode(null)
    setVerifySuccess(false)
    setResendCooldown(0)
    clearError()
    if (cooldownRef.current) clearInterval(cooldownRef.current)
  }

  const handleClose = () => {
    setShowAuthModal(false)
    resetModal()
  }

  const startResendCooldown = () => {
    setResendCooldown(60)
    cooldownRef.current = setInterval(() => {
      setResendCooldown((prev) => {
        if (prev <= 1) {
          clearInterval(cooldownRef.current)
          return 0
        }
        return prev - 1
      })
    }, 1000)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    clearError()
    setLoginErrorCode(null)

    if (mode === 'login') {
      const res = await login(email, password)
      if (res.success) {
        handleClose()
      } else {
        setLoginErrorCode(res.errorCode || null)
      }

    } else if (mode === 'register') {
      // Client-side guard (button should already be disabled, but double-check)
      if (!passwordValid) return
      const res = await register(email, password)
      if (res.success) {
        // Move to verification step, start resend cooldown
        setMode('verify')
        setPassword('')
        startResendCooldown()
      }

    } else if (mode === 'verify') {
      const res = await verify(email, code)
      if (res.success) {
        setVerifySuccess(true)
        setCode('')
        setTimeout(() => {
          setMode('login')
          setVerifySuccess(false)
          clearError()
        }, 1800)
      }
    }
  }

  const handleResend = async () => {
    if (resendCooldown > 0 || isLoading) return
    clearError()
    const res = await resendCode(email)
    if (res.success) {
      startResendCooldown()
    }
  }

  const goToVerify = () => {
    setMode('verify')
    setPassword('')
    clearError()
    setLoginErrorCode(null)
  }

  // ── Titles & subtitles per mode ────────────────────────────────────────────

  const titles = {
    login:    'Welcome Back',
    register: 'Create Account',
    verify:   verifySuccess ? 'Email Verified! 🎉' : 'Verify Your Email',
  }

  const subtitles = {
    login:    'Sign in to sync your profiles and history.',
    register: 'Join PediCompass for personalised guidance.',
    verify:   verifySuccess
      ? 'Your account is ready. Signing you in…'
      : `We sent a 6-digit code to ${maskEmail(email)}`,
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-inverse-surface/40 backdrop-blur-sm p-4">
      <div className="bg-surface-container-lowest rounded-[24px] shadow-[0_8px_32px_rgba(0,0,0,0.08)] w-full max-w-md overflow-hidden flex flex-col border border-outline-variant/20 relative">

        {/* Close button */}
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 text-on-surface-variant hover:text-on-surface hover:bg-surface-container p-2 rounded-full transition-colors flex items-center justify-center"
        >
          <span className="material-symbols-outlined text-[20px]">close</span>
        </button>

        <div className="p-md sm:p-lg flex flex-col gap-md">

          {/* Header */}
          <div className="text-center">
            <h2 className="text-headline-md font-headline-md font-bold text-on-surface mb-xs">
              {titles[mode]}
            </h2>
            <p className="text-body-sm font-body-sm text-on-surface-variant">
              {subtitles[mode]}
            </p>
          </div>

          {/* Error banner */}
          <ErrorBanner
            message={error}
            onVerify={loginErrorCode === 'EMAIL_NOT_CONFIRMED' ? goToVerify : null}
          />

          {/* ── LOGIN form ───────────────────────────────────────────────── */}
          {mode === 'login' && (
            <form onSubmit={handleSubmit} className="flex flex-col gap-sm" noValidate>
              <div className="flex flex-col gap-xs">
                <label className="text-label-md font-label-md text-on-surface">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
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
                  autoComplete="current-password"
                  className="bg-surface-container-low border border-outline-variant/40 rounded-lg px-sm py-xs text-body-md font-body-md focus:border-primary focus:ring-1 focus:ring-primary transition-colors outline-none"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={isLoading || !canSubmitLogin}
                className="mt-sm bg-primary hover:bg-primary-fixed-variant text-on-primary rounded-full py-sm px-md text-label-md font-label-md font-bold transition-colors disabled:opacity-50"
              >
                {isLoading ? 'Signing in…' : 'Sign In'}
              </button>
            </form>
          )}

          {/* ── REGISTER form ─────────────────────────────────────────────── */}
          {mode === 'register' && (
            <form onSubmit={handleSubmit} className="flex flex-col gap-sm" noValidate>
              <div className="flex flex-col gap-xs">
                <label className="text-label-md font-label-md text-on-surface">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
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
                  onFocus={() => setPasswordTouched(true)}
                  autoComplete="new-password"
                  className={`bg-surface-container-low border rounded-lg px-sm py-xs text-body-md font-body-md focus:ring-1 transition-colors outline-none ${
                    passwordTouched && !passwordValid
                      ? 'border-error focus:border-error focus:ring-error'
                      : passwordTouched && passwordValid
                        ? 'border-emerald-500 focus:border-emerald-500 focus:ring-emerald-500'
                        : 'border-outline-variant/40 focus:border-primary focus:ring-primary'
                  }`}
                />
                <PasswordChecklist password={password} show={passwordTouched} />
              </div>

              <button
                type="submit"
                disabled={isLoading || !canSubmitRegister}
                className="mt-sm bg-primary hover:bg-primary-fixed-variant text-on-primary rounded-full py-sm px-md text-label-md font-label-md font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Creating account…' : 'Create Account'}
              </button>
            </form>
          )}

          {/* ── VERIFY form ───────────────────────────────────────────────── */}
          {mode === 'verify' && !verifySuccess && (
            <form onSubmit={handleSubmit} className="flex flex-col gap-sm" noValidate>
              <div className="flex flex-col gap-xs">
                <label className="text-label-md font-label-md text-on-surface">
                  Verification Code
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="123456"
                  autoComplete="one-time-code"
                  className="bg-surface-container-low border border-outline-variant/40 rounded-lg px-sm py-xs text-body-md font-body-md focus:border-primary focus:ring-1 focus:ring-primary transition-colors outline-none tracking-[0.3em] text-center text-headline-sm"
                />
                <p className="text-label-sm font-label-sm text-on-surface-variant">
                  Check your spam folder if you don't see it.
                </p>
              </div>

              <button
                type="submit"
                disabled={isLoading || !canSubmitVerify}
                className="bg-primary hover:bg-primary-fixed-variant text-on-primary rounded-full py-sm px-md text-label-md font-label-md font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Verifying…' : 'Verify Email'}
              </button>

              {/* Resend code */}
              <div className="text-center">
                <button
                  type="button"
                  onClick={handleResend}
                  disabled={resendCooldown > 0 || isLoading}
                  className="text-primary hover:underline text-label-sm font-label-sm disabled:text-on-surface-variant/50 disabled:no-underline disabled:cursor-not-allowed transition-colors"
                >
                  {resendCooldown > 0 ? `Resend code in ${resendCooldown}s` : 'Resend code'}
                </button>
              </div>
            </form>
          )}

          {/* Success state inside verify */}
          {mode === 'verify' && verifySuccess && (
            <div className="flex flex-col items-center gap-sm py-sm">
              <span className="material-symbols-outlined text-emerald-500 text-[48px]">check_circle</span>
              <p className="text-body-md font-body-md text-on-surface text-center">
                Redirecting to sign in…
              </p>
            </div>
          )}

          {/* ── Bottom link — toggle between login / register ─────────────── */}
          {mode !== 'verify' && (
            <p className="text-center text-body-sm font-body-sm text-on-surface-variant">
              {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
              <button
                type="button"
                onClick={() => {
                  setMode(mode === 'login' ? 'register' : 'login')
                  setPassword('')
                  setPasswordTouched(false)
                  clearError()
                  setLoginErrorCode(null)
                }}
                className="text-primary font-bold hover:underline bg-transparent border-none p-0 cursor-pointer"
              >
                {mode === 'login' ? 'Sign up' : 'Log in'}
              </button>
            </p>
          )}

          {/* Back link inside verify */}
          {mode === 'verify' && !verifySuccess && (
            <p className="text-center text-body-sm font-body-sm text-on-surface-variant">
              Wrong email?{' '}
              <button
                type="button"
                onClick={() => { setMode('register'); clearError() }}
                className="text-primary font-bold hover:underline bg-transparent border-none p-0 cursor-pointer"
              >
                Go back
              </button>
            </p>
          )}

        </div>
      </div>
    </div>
  )
}
