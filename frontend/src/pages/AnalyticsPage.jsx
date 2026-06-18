import AnalyticsDashboard from '../components/Admin/AnalyticsDashboard'
import { useNavigate } from 'react-router-dom'

export default function AnalyticsPage() {
  const navigate = useNavigate()

  return (
    <main className="flex-1 flex flex-col h-full bg-surface-lowest overflow-y-auto">
      <div className="w-full max-w-6xl mx-auto px-gutter py-xl">
        <div className="flex items-center gap-sm mb-lg">
          <button 
            onClick={() => navigate('/')}
            className="w-10 h-10 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container transition-colors"
            aria-label="Back to chat"
          >
            <span className="material-symbols-outlined">arrow_back</span>
          </button>
          <h2 className="text-display-sm font-display-sm font-bold text-on-surface">System Analytics</h2>
        </div>
        <AnalyticsDashboard />
      </div>
    </main>
  )
}
