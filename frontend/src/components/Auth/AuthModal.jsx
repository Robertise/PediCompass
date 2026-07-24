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
  // Show/hide password visibility per form
  const [showLoginPw, setShowLoginPw]     = useState(false)
  const [showRegisterPw, setShowRegisterPw] = useState(false)
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
    verify:   verifySuccess ? 'Email Verified!' : 'Verify Your Email',
  }

  const subtitles = {
    login:    'Sign in to sync your profiles and history.',
    register: 'Join Pedix for personalised guidance.',
    verify:   verifySuccess
      ? 'Your account is ready. Signing you in…'
      : `We sent a 6-digit code to ${maskEmail(email)}`,
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-inverse-surface/40 backdrop-blur-sm p-3 sm:p-4">
      <div className="bg-surface dark:bg-surface-container-high rounded-[20px] sm:rounded-[24px] shadow-soft-lg dark:shadow-soft-dark w-[95vw] max-w-md overflow-hidden flex flex-col relative">

        {/* Close button */}
        <button
          onClick={handleClose}
          className="absolute top-3 right-3 sm:top-4 sm:right-4 text-on-surface-variant hover:text-on-surface hover:bg-surface-container p-1.5 sm:p-2 rounded-full transition-colors flex items-center justify-center"
        >
          <span className="material-symbols-outlined text-[18px] sm:text-[20px]">close</span>
        </button>

        <div className="p-4 sm:p-lg flex flex-col gap-sm sm:gap-md">

          {/* Header */}
          <div className="text-center">
            <h2 className="text-lg sm:text-headline-md font-headline-md font-bold text-on-surface mb-xs">
              {titles[mode]}
            </h2>
            <p className="text-xs sm:text-body-sm font-body-sm text-on-surface-variant">
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
              <div className="flex flex-col bg-surface-container dark:bg-black/20 rounded-xl px-3 py-1.5 sm:px-4 sm:py-2 focus-within:ring-2 focus-within:ring-primary/30 transition-all">
                <label className="text-[10px] sm:text-[11px] font-label-sm text-on-surface-variant font-bold mb-0.5">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  className="bg-transparent border-none outline-none p-0 text-xs sm:text-body-md font-body-md text-on-surface w-full focus:ring-0"
                  required
                />
              </div>

              <div className="flex flex-col bg-surface-container dark:bg-black/20 rounded-xl px-3 py-1.5 sm:px-4 sm:py-2 focus-within:ring-2 focus-within:ring-primary/30 transition-all relative">
                <label className="text-[10px] sm:text-[11px] font-label-sm text-on-surface-variant font-bold mb-0.5">Password</label>
                <div className="flex items-center">
                  <input
                    type={showLoginPw ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    className="bg-transparent border-none outline-none p-0 pr-8 text-xs sm:text-body-md font-body-md text-on-surface w-full focus:ring-0"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowLoginPw((v) => !v)}
                    className="absolute right-3 text-on-surface-variant hover:text-on-surface p-1 rounded transition-colors flex items-center justify-center"
                    tabIndex={-1}
                    aria-label={showLoginPw ? 'Hide password' : 'Show password'}
                  >
                    <span className="material-symbols-outlined text-[18px]">
                      {showLoginPw ? 'visibility_off' : 'visibility'}
                    </span>
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading || !canSubmitLogin}
                className="mt-xs bg-primary hover:bg-primary-fixed-variant text-on-primary rounded-full py-2.5 sm:py-3.5 px-6 text-xs sm:text-label-md font-label-md font-bold transition-colors disabled:opacity-50 shadow-sm"
              >
                {isLoading ? 'Signing in…' : 'Sign In'}
              </button>
            </form>
          )}

          {/* ── REGISTER form ─────────────────────────────────────────────── */}
          {mode === 'register' && (
            <form onSubmit={handleSubmit} className="flex flex-col gap-sm" noValidate>
              <div className="flex flex-col bg-surface-container dark:bg-black/20 rounded-xl px-3 py-1.5 sm:px-4 sm:py-2 focus-within:ring-2 focus-within:ring-primary/30 transition-all">
                <label className="text-[10px] sm:text-[11px] font-label-sm text-on-surface-variant font-bold mb-0.5">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  className="bg-transparent border-none outline-none p-0 text-xs sm:text-body-md font-body-md text-on-surface w-full focus:ring-0"
                  required
                />
              </div>

              <div className={`flex flex-col rounded-xl px-3 py-1.5 sm:px-4 sm:py-2 focus-within:ring-2 transition-all relative ${
                  passwordTouched && passwordValid
                    ? 'bg-emerald-500/10 focus-within:ring-emerald-500/50'
                    : 'bg-surface-container dark:bg-black/20 focus-within:ring-primary/30'
              }`}>
                <label className="text-[10px] sm:text-[11px] font-label-sm text-on-surface-variant font-bold mb-0.5">Password</label>
                <div className="flex items-center">
                  <input
                    type={showRegisterPw ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onFocus={() => setPasswordTouched(true)}
                    autoComplete="new-password"
                    className="bg-transparent border-none outline-none p-0 pr-8 text-xs sm:text-body-md font-body-md text-on-surface w-full focus:ring-0"
                  />
                  <button
                    type="button"
                    onClick={() => setShowRegisterPw((v) => !v)}
                    className="absolute right-3 text-on-surface-variant hover:text-on-surface p-1 rounded transition-colors flex items-center justify-center"
                    tabIndex={-1}
                    aria-label={showRegisterPw ? 'Hide password' : 'Show password'}
                  >
                    <span className="material-symbols-outlined text-[16px] sm:text-[18px]">
                      {showRegisterPw ? 'visibility_off' : 'visibility'}
                    </span>
                  </button>
                </div>
              </div>
              <PasswordChecklist password={password} show={passwordTouched} />

              <button
                type="submit"
                disabled={isLoading || !canSubmitRegister}
                className="mt-xs bg-primary hover:bg-primary-fixed-variant text-on-primary rounded-full py-2.5 sm:py-3.5 px-6 text-xs sm:text-label-md font-label-md font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
              >
                {isLoading ? 'Creating account…' : 'Create Account'}
              </button>
            </form>
          )}

          {/* ── VERIFY form ───────────────────────────────────────────────── */}
          {mode === 'verify' && !verifySuccess && (
            <form onSubmit={handleSubmit} className="flex flex-col gap-sm" noValidate>
              <div className="flex flex-col gap-xs">
                <div className="flex flex-col bg-surface-container dark:bg-black/20 rounded-xl px-3 py-1.5 sm:px-4 sm:py-2 focus-within:ring-2 focus-within:ring-primary/30 transition-all">
                  <label className="text-[10px] sm:text-[11px] font-label-sm text-on-surface-variant font-bold mb-0.5 text-center">
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
                    className="bg-transparent border-none outline-none p-0 text-xs sm:text-body-md font-body-md text-on-surface w-full focus:ring-0 tracking-[0.3em] text-center text-headline-sm placeholder:text-outline-variant/60"
                  />
                </div>
                <p className="text-xs sm:text-label-sm font-label-sm text-on-surface-variant text-center mt-1">
                  Check your spam folder if you don't see it.
                </p>
              </div>

              <button
                type="submit"
                disabled={isLoading || !canSubmitVerify}
                className="bg-primary hover:bg-primary-fixed-variant text-on-primary rounded-full py-2.5 sm:py-3.5 px-6 text-xs sm:text-label-md font-label-md font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
              >
                {isLoading ? 'Verifying…' : 'Verify Email'}
              </button>

              {/* Resend code */}
              <div className="text-center">
                <button
                  type="button"
                  onClick={handleResend}
                  disabled={resendCooldown > 0 || isLoading}
                  className="text-primary hover:underline text-xs sm:text-label-sm font-label-sm disabled:text-on-surface-variant/50 disabled:no-underline disabled:cursor-not-allowed transition-colors"
                >
                  {resendCooldown > 0 ? `Resend code in ${resendCooldown}s` : 'Resend code'}
                </button>
              </div>
            </form>
          )}

          {/* Success state inside verify */}
          {mode === 'verify' && verifySuccess && (
            <div className="flex flex-col items-center gap-sm py-sm">
              <span className="material-symbols-outlined text-emerald-500 text-[40px] sm:text-[48px]">check_circle</span>
              <p className="text-xs sm:text-body-md font-body-md text-on-surface text-center">
                Redirecting to sign in…
              </p>
            </div>
          )}

          {/* ── Bottom link — toggle between login / register ─────────────── */}
          {mode !== 'verify' && (
            <p className="text-center text-xs sm:text-body-sm font-body-sm text-on-surface-variant">
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
