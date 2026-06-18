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
      <div className="container flex justify-between items-center" style={{ width: '100%' }}>

        {/* Logo */}
        <Link to="/" className="navbar-logo" id="nav-logo">
          🧭 Pedi<span>Compass</span>
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-2" role="menubar">
          {navLinks.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              id={`nav-${label.toLowerCase()}`}
              role="menuitem"
              className="btn btn-ghost btn-sm"
              style={{
                color: location.pathname === to
                  ? 'var(--color-teal)'
                  : 'var(--color-gray-400)',
                borderColor: location.pathname === to
                  ? 'rgba(0,180,216,0.3)'
                  : 'transparent',
              }}
            >
              {label}
            </Link>
          ))}
        </div>

        {/* Auth controls */}
        <div className="flex items-center gap-2">
          {user ? (
            <>
              <span style={{ fontSize: '0.875rem', color: 'var(--color-gray-400)' }}>
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
