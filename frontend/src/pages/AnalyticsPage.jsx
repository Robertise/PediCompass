import AnalyticsDashboard from '../components/Admin/AnalyticsDashboard'
import { useAuthStore } from '../store/authStore'
import { Navigate } from 'react-router-dom'

export default function AnalyticsPage() {
  const { user } = useAuthStore()

  // In a real app, verify user.isAdmin here
  // For this prototype, we'll allow any logged-in user to see it if they manually navigate,
  // but the navbar link is hidden for non-admins.
  if (!user) {
    return <Navigate to="/auth" replace />
  }

  return (
    <div className="page container">
      <h2 style={{ marginBottom: '24px' }}>System Analytics</h2>
      <AnalyticsDashboard />
    </div>
  )
}
