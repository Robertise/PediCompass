/**
 * CitedSources — displays clinical guideline citations from AgentResponse.
 *
 * @param {Object}   props
 * @param {Array}    props.sources  - Array of { source_authority, content_type, text_snippet, chunk_id }
 */
export default function CitedSources({ sources }) {
  if (!sources || sources.length === 0) return null

  const authorityColors = {
    WHO:  '#00B4D8',
    NICE: '#2A9D8F',
    CDC:  '#F4A261',
    AAP:  '#52B788',
  }

  return (
    <div className="mt-4">
      <p className="font-semibold text-teal-400 uppercase tracking-wide text-xs mb-2">📎 Clinical Sources</p>
      <div className="citations-list">
        {sources.map((source, idx) => (
          <div key={source.chunk_id || idx} className="citation-item">
            <span
              className="citation-authority"
              style={{ color: authorityColors[source.source_authority] || 'var(--color-teal)' }}
            >
              {source.source_authority}
            </span>
            <span className="text-gray-400 text-xs mx-1">•</span>
            <span>{source.text_snippet || source.content_type || 'Clinical guideline'}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
