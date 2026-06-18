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

function MainLayout({ children }) {
  return (
    <div className="bg-background text-on-surface font-body-md h-screen overflow-hidden flex flex-col">
      <Navbar />
      <div className="flex flex-1 overflow-hidden max-w-[1600px] mx-auto w-full">
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
