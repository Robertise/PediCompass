import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
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
  return (
    <BrowserRouter>
      <MainLayout>
        <Routes>
          <Route path="/"          element={<ChatPage />} />
          <Route path="/profiles"  element={
            <ProtectedRoute><ProfilesPage /></ProtectedRoute>
          } />
          <Route path="/analytics" element={
            <ProtectedRoute><AnalyticsPage /></ProtectedRoute>
          } />
          <Route path="*"          element={<Navigate to="/" replace />} />
        </Routes>
      </MainLayout>
    </BrowserRouter>
  )
}
