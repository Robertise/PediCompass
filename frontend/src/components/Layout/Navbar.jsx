import { Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'

export default function Navbar() {
  const location = useLocation()
  const { user, logout } = useAuthStore()

  const navLinks = [
    { to: '/',          label: 'Home'      },
    { to: '/chat',      label: 'Chat'      },
    ...(user ? [{ to: '/profiles', label: 'Profiles' }] : []),
    ...(user?.isAdmin ? [{ to: '/analytics', label: 'Analytics' }] : []),
  ]

  return (
    <nav className="navbar" role="navigation" aria-label="Main navigation">
      <div className="container flex flex-wrap justify-between items-center w-full">

        {/* Logo */}
        <Link to="/" className="navbar-logo shrink-0" id="nav-logo">
          🧭 Pedi<span className="text-teal-400">Compass</span>
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-1 md:gap-2 mt-2 md:mt-0 overflow-x-auto" role="menubar">
          {navLinks.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              id={`nav-${label.toLowerCase()}`}
              role="menuitem"
              className={`btn btn-ghost btn-sm ${location.pathname === to ? 'text-teal-400 border-teal-400/30' : 'text-gray-400 border-transparent'}`}
            >
              {label}
            </Link>
          ))}
        </div>

        {/* Auth controls */}
        <div className="flex items-center gap-2 mt-2 md:mt-0">
          {user ? (
            <>
              <span className="text-sm text-gray-400 hidden sm:inline-block">
                {user.email}
              </span>
              <button
                id="nav-logout"
                className="btn btn-ghost btn-sm"
                onClick={logout}
              >
                Sign out
              </button>
            </>
          ) : (
            <Link to="/auth" id="nav-signin" className="btn btn-primary btn-sm">
              Sign in
            </Link>
          )}
        </div>
      </div>
    </nav>
  )
}
