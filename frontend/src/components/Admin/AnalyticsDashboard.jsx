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
    return <div className="flex justify-center my-10"><span className="material-symbols-outlined animate-spin text-[40px] text-primary">progress_activity</span></div>
  }

  if (!summary) return null

  const totalQueries = summary.queries_total || 0

  return (
    <div>
      <div className="flex justify-end mb-md">
        <select 
          className="bg-surface-container-low border border-outline-variant/40 rounded-lg px-sm py-xs text-body-md font-body-md focus:border-primary outline-none"
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
        >
          <option value={7}>Last 7 Days</option>
          <option value={30}>Last 30 Days</option>
          <option value={90}>Last 90 Days</option>
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-md mb-xl">
        <div className="bg-surface border border-outline-variant/30 rounded-[20px] p-md shadow-sm flex flex-col items-center justify-center">
          <div className="text-[48px] font-display-md font-bold text-primary">{totalQueries}</div>
          <div className="text-label-md font-label-md text-on-surface-variant uppercase tracking-wider">Total Queries</div>
        </div>
        
        <div className="bg-surface border border-outline-variant/30 rounded-[20px] p-md shadow-sm">
          <h3 className="text-headline-sm font-headline-sm text-on-surface mb-sm">Urgency Distribution</h3>
          {Object.entries(summary.urgency_distribution || {}).length === 0 ? (
            <p className="text-body-sm text-on-surface-variant">No data</p>
          ) : (
            Object.entries(summary.urgency_distribution).map(([level, count]) => (
              <div key={level} className="flex justify-between mb-xs text-body-md font-body-md text-on-surface">
                <span className="capitalize">{level.replace('_', ' ')}</span>
                <span className="font-bold">{count} <span className="text-on-surface-variant font-normal">({Math.round((count/totalQueries)*100)}%)</span></span>
              </div>
            ))
          )}
        </div>

        <div className="bg-surface border border-outline-variant/30 rounded-[20px] p-md shadow-sm">
          <h3 className="text-headline-sm font-headline-sm text-on-surface mb-sm">Age Demographics</h3>
          {Object.entries(summary.age_group_distribution || {}).length === 0 ? (
            <p className="text-body-sm text-on-surface-variant">No data</p>
          ) : (
            Object.entries(summary.age_group_distribution).map(([age, count]) => (
              <div key={age} className="flex justify-between mb-xs text-body-md font-body-md text-on-surface">
                <span className="capitalize">{age.replace('_', ' ')}</span>
                <span className="font-bold">{count} <span className="text-on-surface-variant font-normal">({Math.round((count/totalQueries)*100)}%)</span></span>
              </div>
            ))
          )}
        </div>
      </div>

      <h2 className="text-display-sm font-display-sm font-bold text-on-surface mb-md">Document Registry (KB)</h2>
      <div className="bg-surface border border-outline-variant/30 rounded-[20px] shadow-sm overflow-hidden">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-outline-variant/30 bg-surface-container-low">
              <th className="p-4 text-label-md font-label-md text-on-surface-variant">Document Name</th>
              <th className="p-4 text-label-md font-label-md text-on-surface-variant">Authority</th>
              <th className="p-4 text-label-md font-label-md text-on-surface-variant">Chunks</th>
              <th className="p-4 text-label-md font-label-md text-on-surface-variant">Date Indexed</th>
              <th className="p-4 text-label-md font-label-md text-on-surface-variant">Status</th>
            </tr>
          </thead>
          <tbody>
            {documents.length === 0 ? (
              <tr>
                <td colSpan="5" className="p-md text-center text-on-surface-variant font-body-md">
                  No documents found in registry.
                </td>
              </tr>
            ) : (
              documents.map(doc => (
                <tr key={doc.doc_id} className="border-b border-outline-variant/20 last:border-0 hover:bg-surface-container-lowest transition-colors">
                  <td className="p-4 text-body-md font-body-md text-on-surface">{doc.filename}</td>
                  <td className="p-4">
                    <span className="bg-tertiary-container text-on-tertiary-container px-2 py-1 rounded-md text-label-sm font-label-sm">{doc.source_authority}</span>
                  </td>
                  <td className="p-4 text-body-md font-body-md text-on-surface">{doc.chunk_count}</td>
                  <td className="p-4 text-body-md font-body-md text-on-surface">{new Date(doc.upload_date).toLocaleDateString()}</td>
                  <td className="p-4">
                    <span className={`text-label-sm font-label-sm px-2 py-1 rounded-md ${
                      doc.status === 'complete' 
                        ? 'bg-primary-container/30 text-primary' 
                        : 'bg-error-container/30 text-error'
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
