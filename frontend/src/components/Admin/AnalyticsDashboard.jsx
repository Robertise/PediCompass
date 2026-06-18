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
    return <div className="spinner" style={{ margin: '40px auto' }} />
  }

  if (!summary) return null

  const totalQueries = summary.queries_total || 0

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '24px' }}>
        <select 
          className="input" 
          style={{ width: '200px' }}
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
        >
          <option value={7}>Last 7 Days</option>
          <option value={30}>Last 30 Days</option>
          <option value={90}>Last 90 Days</option>
        </select>
      </div>

      <div className="analytics-grid" style={{ marginBottom: '40px' }}>
        <div className="stat-card">
          <div className="stat-value">{totalQueries}</div>
          <div className="stat-label">Total Queries</div>
        </div>
        
        {/* Placeholder for real charts - rendering basic text for now */}
        <div className="card">
          <h3 style={{ fontSize: '1rem', marginBottom: '16px' }}>Urgency Distribution</h3>
          {Object.entries(summary.urgency_distribution || {}).length === 0 ? (
            <p style={{ color: 'var(--color-gray-400)', fontSize: '0.875rem' }}>No data</p>
          ) : (
            Object.entries(summary.urgency_distribution).map(([level, count]) => (
              <div key={level} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.875rem' }}>
                <span style={{ textTransform: 'capitalize' }}>{level.replace('_', ' ')}</span>
                <span style={{ fontWeight: 600 }}>{count} ({Math.round((count/totalQueries)*100)}%)</span>
              </div>
            ))
          )}
        </div>

        <div className="card">
          <h3 style={{ fontSize: '1rem', marginBottom: '16px' }}>Age Demographics</h3>
          {Object.entries(summary.age_group_distribution || {}).length === 0 ? (
            <p style={{ color: 'var(--color-gray-400)', fontSize: '0.875rem' }}>No data</p>
          ) : (
            Object.entries(summary.age_group_distribution).map(([age, count]) => (
              <div key={age} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.875rem' }}>
                <span style={{ textTransform: 'capitalize' }}>{age.replace('_', ' ')}</span>
                <span style={{ fontWeight: 600 }}>{count} ({Math.round((count/totalQueries)*100)}%)</span>
              </div>
            ))
          )}
        </div>
      </div>

      <h2 style={{ marginBottom: '24px' }}>Document Registry (KB)</h2>
      <div className="card" style={{ overflowX: 'auto', padding: 0 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', background: 'var(--color-bg-surface)' }}>
              <th style={{ padding: '16px', fontSize: '0.875rem', color: 'var(--color-gray-400)', fontWeight: 600 }}>Document Name</th>
              <th style={{ padding: '16px', fontSize: '0.875rem', color: 'var(--color-gray-400)', fontWeight: 600 }}>Authority</th>
              <th style={{ padding: '16px', fontSize: '0.875rem', color: 'var(--color-gray-400)', fontWeight: 600 }}>Chunks</th>
              <th style={{ padding: '16px', fontSize: '0.875rem', color: 'var(--color-gray-400)', fontWeight: 600 }}>Date Indexed</th>
              <th style={{ padding: '16px', fontSize: '0.875rem', color: 'var(--color-gray-400)', fontWeight: 600 }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {documents.length === 0 ? (
              <tr>
                <td colSpan="5" style={{ padding: '24px', textAlign: 'center', color: 'var(--color-gray-400)' }}>
                  No documents found in registry.
                </td>
              </tr>
            ) : (
              documents.map(doc => (
                <tr key={doc.doc_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '16px', fontSize: '0.9375rem' }}>{doc.filename}</td>
                  <td style={{ padding: '16px' }}><span className="tag tag--teal">{doc.source_authority}</span></td>
                  <td style={{ padding: '16px', fontSize: '0.9375rem', color: 'var(--color-gray-200)' }}>{doc.chunk_count}</td>
                  <td style={{ padding: '16px', fontSize: '0.9375rem', color: 'var(--color-gray-200)' }}>{new Date(doc.upload_date).toLocaleDateString()}</td>
                  <td style={{ padding: '16px' }}>
                    <span style={{ 
                      fontSize: '0.75rem', 
                      padding: '4px 8px', 
                      borderRadius: 'var(--radius-sm)',
                      background: doc.status === 'complete' ? 'rgba(42,157,143,0.15)' : 'rgba(233,196,106,0.15)',
                      color: doc.status === 'complete' ? '#52B788' : '#E9C46A'
                    }}>
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
