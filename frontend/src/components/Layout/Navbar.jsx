import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { useAuthStore } from '../../store/authStore'
import { useAppStore } from '../../store/appStore'
import ProfileSelector from '../Profiles/ProfileSelector'
import ThemeToggle from './ThemeToggle'
import ReasoningTrace from '../Chat/ReasoningTrace'
import { useThemeStore } from '../../store/themeStore'

export default function Navbar({ activeTrace: propsTrace, isStreaming: propsStreaming }) {
  const { user, logout } = useAuthStore()
  const { setShowAuthModal, triggerChatReset, activeTrace: storeTrace, isStreaming: storeStreaming } = useAppStore()
  const activeTrace = propsTrace ?? storeTrace
  const isStreaming = propsStreaming ?? storeStreaming
  const { theme, toggleTheme } = useThemeStore()
  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState(false)

  return (
    <>
      <header className="bg-background sticky top-0 z-40 flex justify-between items-center px-4 md:px-6 py-3 md:py-4 w-full border-b border-black/5 dark:border-white/5 relative">
        {/* Mobile Left: Hamburger Button | Desktop Left: Logo */}
        <div className="flex items-center gap-xs sm:gap-sm relative z-10">
          <button
            onClick={() => setIsMobileDrawerOpen(true)}
            className="md:hidden w-9 h-9 rounded-full flex items-center justify-center text-on-surface hover:bg-surface-container active:scale-95 transition-transform"
            title="Open Menu & Reasoning Trace"
          >
            <span className="material-symbols-outlined text-[24px]">menu</span>
          </button>

          <Link to="/" onClick={() => triggerChatReset()} className="hidden md:flex items-center gap-sm transition-transform active:scale-95">
            <img src="/logo_light.png" alt="Pedix Logo" className="w-9 h-9 object-contain dark:hidden block" />
            <img src="/logo_dark.png" alt="Pedix Logo" className="w-9 h-9 object-contain hidden dark:block" />
            <div className="flex flex-col">
              <span className="text-headline-md font-manrope-md font-bold text-primary dark:text-primary-fixed-dim leading-none">Pedix</span>
              <span className="text-label-sm font-label-sm text-on-surface-variant hidden sm:block">Pediatric Care Pathway Navigator</span>
            </div>
          </Link>
        </div>

        {/* Center: Profile Selector (Styled compactly for mobile & centered on desktop) */}
        <div className="md:absolute md:left-1/2 md:-translate-x-1/2 flex items-center justify-center z-20">
          <ProfileSelector />
        </div>

        {/* Right Actions: Theme Toggle & Avatar / Login */}
        <div className="flex items-center gap-xs sm:gap-sm relative z-10">
          <div className="hidden md:block">
            <ThemeToggle />
          </div>
          
          {user ? (
            <div className="relative group">
              <div className="w-8 h-8 rounded-full bg-tertiary-container flex items-center justify-center text-on-tertiary-container text-label-md font-label-md font-bold cursor-pointer transition-colors hover:bg-tertiary/20">
                {user.email ? user.email.charAt(0).toUpperCase() : 'U'}
              </div>
              {/* User Dropdown */}
              <div className="absolute top-full right-0 pt-2 hidden group-hover:block z-50">
                <div className="w-52 bg-surface dark:bg-surface-container-high border border-black/5 dark:border-white/5 rounded-xl shadow-soft dark:shadow-soft-dark flex flex-col py-2">
                  <span className="px-4 py-2 text-label-sm font-label-sm text-on-surface-variant border-b border-black/5 dark:border-white/5 truncate">
                    {user.email}
                  </span>
                  
                  {/* Theme Switcher inside Dropdown on Mobile */}
                  <button
                    onClick={toggleTheme}
                    className="md:hidden flex items-center justify-between w-full px-4 py-2 text-label-md font-label-md text-on-surface hover:bg-surface-container transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-[18px]">
                        {theme === 'dark' ? 'dark_mode' : 'light_mode'}
                      </span>
                      Theme
                    </span>
                    <span className="text-xs uppercase font-bold text-primary">
                      {theme === 'dark' ? 'Dark' : 'Light'}
                    </span>
                  </button>

                  <Link
                    to="/profiles"
                    className="block px-4 py-2 text-xs sm:text-sm font-medium text-on-surface hover:bg-surface-container transition-colors"
                  >
                    Child Profiles
                  </Link>
                  {useAuthStore.getState().isAdmin() && (
                    <Link
                      to="/analytics"
                      className="block px-4 py-2 text-xs sm:text-sm font-medium text-on-surface hover:bg-surface-container transition-colors"
                    >
                      System Analytics
                    </Link>
                  )}
                  <button 
                    onClick={logout}
                    className="text-left px-4 py-2 text-xs sm:text-sm font-medium text-error hover:bg-error-container/20 transition-colors w-full border-t border-black/5 dark:border-white/5 mt-1 pt-2"
                  >
                    Sign out
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-xs">
              <button 
                onClick={() => setShowAuthModal(true)}
                className="text-label-sm sm:text-label-md font-label-md bg-primary text-on-primary px-3.5 py-1.5 sm:px-5 sm:py-2.5 rounded-full hover:bg-primary-fixed-variant transition-colors"
              >
                Log in
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Mobile Slide-over Drawer (Left Side) */}
      <AnimatePresence>
        {isMobileDrawerOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsMobileDrawerOpen(false)}
              className="fixed inset-0 bg-black/50 z-50 md:hidden"
            />

            {/* Slide-in Drawer */}
            <motion.div
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="fixed inset-y-0 left-0 w-[85vw] max-w-xs bg-surface dark:bg-surface-container-high z-50 md:hidden shadow-2xl flex flex-col overflow-hidden"
            >
              {/* Drawer Top Header */}
              <div className="p-4 border-b border-black/5 dark:border-white/5 flex items-center justify-between bg-surface-container-low dark:bg-surface-container">
                <Link to="/" onClick={() => { triggerChatReset(); setIsMobileDrawerOpen(false); }} className="flex items-center gap-2">
                  <img src="/logo_light.png" alt="Pedix Logo" className="w-7 h-7 object-contain dark:hidden block" />
                  <img src="/logo_dark.png" alt="Pedix Logo" className="w-7 h-7 object-contain hidden dark:block" />
                  <span className="text-headline-sm font-bold text-primary dark:text-primary-fixed-dim">Pedix</span>
                </Link>
                <button
                  onClick={() => setIsMobileDrawerOpen(false)}
                  className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:text-on-surface"
                >
                  <span className="material-symbols-outlined text-[20px]">close</span>
                </button>
              </div>

              {/* Drawer Content — Mobile-optimized Reasoning Trace */}
              <div className="flex-1 overflow-y-auto">
                <ReasoningTrace
                  trace={activeTrace}
                  isStreaming={isStreaming}
                  isOpen={true}
                  onToggle={() => setIsMobileDrawerOpen(false)}
                  isMobile={true}
                />
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}

