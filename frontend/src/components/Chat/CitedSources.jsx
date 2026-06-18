export default function CitedSources({ sources }) {
  if (!sources || sources.length === 0) return null

  const authorityIcons = {
    WHO:  'public',
    NICE: 'health_metrics',
    CDC:  'shield',
    AAP:  'child_care',
  }

  return (
    <div className="flex flex-col gap-sm border-t border-outline-variant/20 pt-md">
      <span className="text-label-md font-label-md text-on-surface flex items-center gap-xs">
        <span className="material-symbols-outlined text-[18px]">menu_book</span> Guidelines Referenced
      </span>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-sm">
        {sources.map((source, idx) => (
          <div key={source.chunk_id || idx} className="flex gap-sm p-xs bg-surface-container-lowest rounded-xl border border-outline-variant/20 items-center">
            <div className="w-8 h-8 rounded-full bg-tertiary-container flex items-center justify-center shrink-0">
              <span className="material-symbols-outlined text-on-tertiary-container text-[16px]">
                {authorityIcons[source.source_authority] || 'menu_book'}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-label-sm font-label-sm text-on-surface">{source.source_authority}</span>
              <span className="text-[11px] font-body-sm text-on-surface-variant truncate w-40 md:w-48" title={source.text_snippet || source.content_type}>
                {source.text_snippet || source.content_type || 'Clinical guideline'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
