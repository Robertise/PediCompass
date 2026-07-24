import AnalyticsDashboard from '../components/Admin/AnalyticsDashboard'
import { useNavigate } from 'react-router-dom'

export default function AnalyticsPage() {
  const navigate = useNavigate()

  return (
    <main className="flex-1 flex flex-col h-full bg-transparent overflow-y-auto">
      <div className="w-full max-w-6xl mx-auto px-4 sm:px-6 py-md sm:py-xl">
        <div className="flex items-center gap-2 mb-sm sm:mb-lg">
          <button 
            onClick={() => navigate('/')}
            className="w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container transition-colors"
            aria-label="Back to chat"
          >
            <span className="material-symbols-outlined text-[20px]">arrow_back</span>
          </button>
          <h2 className="text-lg sm:text-display-sm font-bold text-on-surface">System Analytics</h2>
        </div>
        <AnalyticsDashboard />
      </div>
    </main>
  )
}
