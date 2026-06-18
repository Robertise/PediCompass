import { useState, useEffect } from 'react'
import { analyticsApi } from '../../api/client'

export default function AnalyticsDashboard() {
  const [summary, setSummary] = useState(null)
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(7)

  useEffect(() => {
    async function loadData() {
      setLoading(true)
      try {
        const [sumRes, docRes] = await Promise.all([
          analyticsApi.getSummary(days),
          analyticsApi.getDocuments()
        ])
        setSummary(sumRes.data)
        setDocuments(docRes.data)
      } catch (err) {
        console.error('Failed to load analytics', err)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [days])

  if (loading) {
    return <div className="spinner mx-auto my-10" />
  }

  if (!summary) return null

  const totalQueries = summary.queries_total || 0

  return (
    <div>
      <div className="flex justify-end mb-6">
        <select 
          className="input w-[200px]" 
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
        >
          <option value={7}>Last 7 Days</option>
          <option value={30}>Last 30 Days</option>
          <option value={90}>Last 90 Days</option>
        </select>
      </div>

      <div className="analytics-grid mb-10">
        <div className="stat-card">
          <div className="stat-value">{totalQueries}</div>
          <div className="stat-label">Total Queries</div>
        </div>
        
        {/* Placeholder for real charts - rendering basic text for now */}
        <div className="card">
          <h3 className="text-base mb-4">Urgency Distribution</h3>
          {Object.entries(summary.urgency_distribution || {}).length === 0 ? (
            <p className="text-gray-400 text-sm">No data</p>
          ) : (
            Object.entries(summary.urgency_distribution).map(([level, count]) => (
              <div key={level} className="flex justify-between mb-2 text-sm">
                <span className="capitalize">{level.replace('_', ' ')}</span>
                <span className="font-semibold">{count} ({Math.round((count/totalQueries)*100)}%)</span>
              </div>
            ))
          )}
        </div>

        <div className="card">
          <h3 className="text-base mb-4">Age Demographics</h3>
          {Object.entries(summary.age_group_distribution || {}).length === 0 ? (
            <p className="text-gray-400 text-sm">No data</p>
          ) : (
            Object.entries(summary.age_group_distribution).map(([age, count]) => (
              <div key={age} className="flex justify-between mb-2 text-sm">
                <span className="capitalize">{age.replace('_', ' ')}</span>
                <span className="font-semibold">{count} ({Math.round((count/totalQueries)*100)}%)</span>
              </div>
            ))
          )}
        </div>
      </div>

      <h2 className="mb-6">Document Registry (KB)</h2>
      <div className="card overflow-x-auto p-0">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-white/10 bg-bgSurface">
              <th className="p-4 text-sm text-gray-400 font-semibold">Document Name</th>
              <th className="p-4 text-sm text-gray-400 font-semibold">Authority</th>
              <th className="p-4 text-sm text-gray-400 font-semibold">Chunks</th>
              <th className="p-4 text-sm text-gray-400 font-semibold">Date Indexed</th>
              <th className="p-4 text-sm text-gray-400 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody>
            {documents.length === 0 ? (
              <tr>
                <td colSpan="5" className="p-6 text-center text-gray-400">
                  No documents found in registry.
                </td>
              </tr>
            ) : (
              documents.map(doc => (
                <tr key={doc.doc_id} className="border-b border-white/5">
                  <td className="p-4 text-[0.9375rem]">{doc.filename}</td>
                  <td className="p-4"><span className="tag tag--teal">{doc.source_authority}</span></td>
                  <td className="p-4 text-[0.9375rem] text-gray-200">{doc.chunk_count}</td>
                  <td className="p-4 text-[0.9375rem] text-gray-200">{new Date(doc.upload_date).toLocaleDateString()}</td>
                  <td className="p-4">
                    <span className={`text-xs px-2 py-1 rounded-sm ${
                      doc.status === 'complete' 
                        ? 'bg-[#52B788]/15 text-[#52B788]' 
                        : 'bg-[#E9C46A]/15 text-[#E9C46A]'
                    }`}>
                      {doc.status.toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
