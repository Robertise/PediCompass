import { Link } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { useAppStore } from '../../store/appStore'
import ProfileSelector from '../Profiles/ProfileSelector'
import ThemeToggle from './ThemeToggle'

export default function Navbar() {
  const { user, logout } = useAuthStore()
  const { setShowAuthModal, triggerChatReset } = useAppStore()

  return (
    <header className="bg-background sticky top-0 z-50 flex justify-between items-center px-6 py-4 w-full border-b border-black/5 dark:border-white/5 relative">
      <div className="flex items-center gap-sm relative z-10">
        <Link to="/" onClick={() => triggerChatReset()} className="flex items-center gap-sm transition-transform active:scale-95">
          <img src="/logo_light.png" alt="PediCompass Logo" className="w-9 h-9 object-contain dark:hidden block" />
          <img src="/logo_dark.png" alt="PediCompass Logo" className="w-9 h-9 object-contain hidden dark:block" />
          <div className="flex flex-col">
            <span className="text-headline-md font-manrope-md font-bold text-primary dark:text-primary-fixed-dim leading-none">PediCompass</span>
            <span className="text-label-sm font-label-sm text-on-surface-variant hidden sm:block">Pediatric Care Pathway Navigator</span>
          </div>
        </Link>
      </div>

      <div className="absolute left-1/2 -translate-x-1/2 flex items-center justify-center z-20">
        <ProfileSelector />
      </div>

      <div className="flex items-center gap-sm relative z-10">
        <ThemeToggle />
        
        {user ? (
          <div className="relative group">
            <div className="w-8 h-8 rounded-full bg-tertiary-container flex items-center justify-center text-on-tertiary-container text-label-md font-label-md font-bold cursor-pointer transition-colors hover:bg-tertiary/20">
              {user.email ? user.email.charAt(0).toUpperCase() : 'U'}
            </div>
              {/* User Dropdown */}
              <div className="absolute top-full right-0 pt-2 hidden group-hover:block z-50">
                <div className="w-48 bg-surface dark:bg-surface-container-high border border-black/5 dark:border-white/5 rounded-xl shadow-soft dark:shadow-soft-dark flex flex-col py-2">
                  <span className="px-4 py-2 text-label-sm font-label-sm text-on-surface-variant border-b border-black/5 dark:border-white/5 truncate">
                    {user.email}
                  </span>
                  <Link
                    to="/profiles"
                    className="block px-4 py-2 text-label-md font-label-md text-on-surface hover:bg-surface-container transition-colors"
                  >
                    Child Profiles
                  </Link>
                  {useAuthStore.getState().isAdmin() && (
                    <Link
                      to="/analytics"
                      className="block px-4 py-2 text-label-md font-label-md text-on-surface hover:bg-surface-container transition-colors"
                    >
                      System Analytics
                    </Link>
                  )}
                  <button 
                    onClick={logout}
                    className="text-left px-4 py-2 text-label-md font-label-md text-error hover:bg-error-container/20 transition-colors w-full border-t border-black/5 dark:border-white/5 mt-1 pt-2"
                  >
                    Sign out
                  </button>
                </div>
              </div>
          </div>
        ) : (
          <button 
            onClick={() => setShowAuthModal(true)}
            className="text-label-md font-label-md bg-primary text-on-primary px-5 py-2.5 rounded-full hover:bg-primary-fixed-variant transition-colors"
          >
            Log in
          </button>
        )}
      </div>
    </header>
  )
}
