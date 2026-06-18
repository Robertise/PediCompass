import { Link } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { useAppStore } from '../../store/appStore'
import ProfileSelector from '../Profiles/ProfileSelector'

export default function Navbar() {
  const { user, logout } = useAuthStore()
  const { setShowAuthModal } = useAppStore()

  return (
    <header className="bg-surface/80 dark:bg-surface-container/80 backdrop-blur-lg sticky top-0 z-50 flex justify-between items-center px-gutter py-base w-full max-w-full border-b border-outline-variant/30">
      <div className="flex items-center gap-sm">
        <Link to="/" className="flex items-center gap-sm transition-transform active:scale-95">
          <span className="material-symbols-outlined text-primary text-3xl">explore</span>
          <div className="flex flex-col">
            <span className="text-headline-md font-headline-md font-bold text-primary dark:text-primary-fixed-dim leading-none">PediCompass</span>
            <span className="text-label-sm font-label-sm text-on-surface-variant hidden sm:block">Pediatric Care Pathway Navigator</span>
          </div>
        </Link>
      </div>

      <div className="flex items-center justify-center flex-1">
        <ProfileSelector />
      </div>

      <div className="flex items-center gap-sm">
        <button className="hidden md:flex items-center gap-xs text-on-surface-variant hover:bg-primary-container/20 transition-colors px-sm py-xs rounded-full text-label-md font-label-md">
          <span className="material-symbols-outlined text-[20px]">info</span>
          <span>About</span>
        </button>
        
        {user ? (
          <div className="relative group">
            <div className="w-10 h-10 rounded-full bg-tertiary-container flex items-center justify-center text-on-tertiary-container text-label-md font-label-md font-bold cursor-pointer transition-colors hover:bg-tertiary/20">
              {user.email ? user.email.charAt(0).toUpperCase() : 'U'}
            </div>
            {/* User Dropdown */}
            <div className="absolute right-0 mt-2 w-48 bg-surface-container-lowest rounded-xl shadow-[0_8px_32px_rgba(0,0,0,0.12)] border border-outline-variant/20 hidden group-hover:flex flex-col py-2 z-50">
              <span className="px-4 py-2 text-label-sm font-label-sm text-on-surface-variant border-b border-outline-variant/20 truncate">
                {user.email}
              </span>
              <button 
                onClick={logout}
                className="text-left px-4 py-2 text-label-md font-label-md text-error hover:bg-error-container/20 transition-colors w-full"
              >
                Sign out
              </button>
            </div>
          </div>
        ) : (
          <button 
            onClick={() => setShowAuthModal(true)}
            className="text-label-md font-label-md bg-primary text-on-primary px-4 py-2 rounded-full hover:bg-primary-fixed-variant transition-colors"
          >
            Log in
          </button>
        )}
      </div>
    </header>
  )
}
