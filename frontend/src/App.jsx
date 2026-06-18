import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Navbar from './components/Layout/Navbar'
import HomePage from './pages/HomePage'
import ChatPage from './pages/ChatPage'
import AuthPage from './pages/AuthPage'
import ProfilesPage from './pages/ProfilesPage'
import AnalyticsPage from './pages/AnalyticsPage'

// Protected route wrapper
function ProtectedRoute({ children }) {
  const { user } = useAuthStore()
  if (!user) return <Navigate to="/auth" replace />
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/"          element={<HomePage />} />
        <Route path="/chat"      element={<ChatPage />} />
        <Route path="/auth"      element={<AuthPage />} />
        <Route path="/profiles"  element={
          <ProtectedRoute><ProfilesPage /></ProtectedRoute>
        } />
        <Route path="/analytics" element={
          <ProtectedRoute><AnalyticsPage /></ProtectedRoute>
        } />
        <Route path="*"          element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
