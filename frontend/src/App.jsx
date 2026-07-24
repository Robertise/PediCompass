import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import { useAppStore } from './store/appStore'
import Navbar from './components/Layout/Navbar'
import ChatPage from './pages/ChatPage'
import ProfilesPage from './pages/ProfilesPage'
import AnalyticsPage from './pages/AnalyticsPage'
import AuthModal from './components/Auth/AuthModal'
import ProfileModal from './components/Profiles/ProfileModal'

// Protected route wrapper
function ProtectedRoute({ children }) {
  const { user } = useAuthStore()
  if (!user) return <Navigate to="/" replace />
  return children
}

function AdminRoute({ children }) {
  const { user, isAdmin } = useAuthStore()
  if (!user || !isAdmin()) return <Navigate to="/" replace />
  return children
}

import { useEffect } from 'react'
import { useThemeStore } from './store/themeStore'

function MainLayout({ children }) {
  const { theme } = useThemeStore()

  useEffect(() => {
    const root = window.document.documentElement
    root.classList.remove('light', 'dark')
    root.classList.add(theme)
  }, [theme])

  // Mobile Visual Viewport Handling: Dynamically adjust app height to fit above mobile virtual keyboard
  useEffect(() => {
    const updateViewportHeight = () => {
      const vvHeight = window.visualViewport ? window.visualViewport.height : window.innerHeight
      document.documentElement.style.setProperty('--vv-height', `${vvHeight}px`)
      if (window.scrollY !== 0) {
        window.scrollTo(0, 0)
      }
    }

    updateViewportHeight()

    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', updateViewportHeight)
      window.visualViewport.addEventListener('scroll', updateViewportHeight)
    }
    window.addEventListener('resize', updateViewportHeight)

    return () => {
      if (window.visualViewport) {
        window.visualViewport.removeEventListener('resize', updateViewportHeight)
        window.visualViewport.removeEventListener('scroll', updateViewportHeight)
      }
      window.removeEventListener('resize', updateViewportHeight)
    }
  }, [])

  return (
    <div 
      style={{ height: 'var(--vv-height, 100vh)', overscrollBehavior: 'none' }}
      className="fixed inset-x-0 top-0 bg-background text-on-surface font-body-md overflow-hidden flex flex-col transition-colors duration-200"
    >
      <Navbar />
      <div className="flex flex-1 overflow-hidden min-h-0 w-full">
        {children}
      </div>
      <AuthModal />
      <ProfileModal />
    </div>
  )
}

export default function App() {
  const { chatResetKey } = useAppStore()
  
  return (
    <BrowserRouter>
      <MainLayout>
        <Routes>
          <Route path="/"          element={<ChatPage key={chatResetKey} />} />
          <Route path="/profiles"  element={
            <ProtectedRoute><ProfilesPage /></ProtectedRoute>
          } />
          <Route path="/analytics" element={
            <AdminRoute><AnalyticsPage /></AdminRoute>
          } />
          <Route path="*"          element={<Navigate to="/" replace />} />
        </Routes>
      </MainLayout>
    </BrowserRouter>
  )
}
