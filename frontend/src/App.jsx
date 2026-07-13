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
    
    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
      root.classList.remove('light', 'dark')
      root.classList.add(systemTheme)
    } else {
      root.classList.remove('light', 'dark')
      root.classList.add(theme)
    }
  }, [theme])

  return (
    <div className="bg-background text-on-surface font-body-md h-screen overflow-hidden flex flex-col transition-colors duration-200">
      <Navbar />
      <div className="flex flex-1 overflow-hidden w-full">
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
