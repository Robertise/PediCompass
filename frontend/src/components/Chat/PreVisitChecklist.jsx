import { useState } from 'react'

export default function PreVisitChecklist({ items }) {
  const [checked, setChecked] = useState({})
  const [copied, setCopied] = useState(false)

  if (!items || items.length === 0) return null

  const toggle = (idx) =>
    setChecked(prev => ({ ...prev, [idx]: !prev[idx] }))

  const checkedCount = Object.values(checked).filter(Boolean).length

  const getFormattedChecklist = () => {
    const lines = items.map((item, idx) => `${checked[idx] ? '[x]' : '[ ]'} ${item}`)
    return `Pedix — Pre-Visit Checklist\nDate: ${new Date().toLocaleDateString()}\n---------------------------------\n${lines.join('\n')}`
  }

  const handleCopy = () => {
    const text = getFormattedChecklist()
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const handleDownload = () => {
    const text = getFormattedChecklist()
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `Pedix_PreVisit_Checklist_${new Date().toISOString().slice(0, 10)}.txt`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col gap-sm bg-surface-container dark:bg-black/20 p-sm rounded-xl border-none shadow-sm dark:shadow-none">
      <div className="flex justify-between items-center flex-wrap gap-xs">
        <span className="text-label-md font-label-md text-on-surface flex items-center gap-xs">
          <span className="material-symbols-outlined text-primary text-[20px]">checklist</span> Before Your Visit
        </span>
        <div className="flex items-center gap-xs">
          <span className="text-label-sm font-label-sm bg-primary-container text-on-primary-container px-2 py-[2px] rounded-full mr-1">
            {checkedCount}/{items.length} Ready
          </span>
          <button
            onClick={handleCopy}
            title="Copy checklist to clipboard"
            className="flex items-center gap-1 text-xs text-on-surface-variant hover:text-primary bg-surface-container-high hover:bg-surface-variant px-2 py-1 rounded-md transition-colors cursor-pointer"
          >
            <span className="material-symbols-outlined text-[15px]">
              {copied ? 'check' : 'content_copy'}
            </span>
            <span>{copied ? 'Copied!' : 'Copy'}</span>
          </button>
          <button
            onClick={handleDownload}
            title="Download checklist (.txt)"
            className="flex items-center gap-1 text-xs text-on-surface-variant hover:text-primary bg-surface-container-high hover:bg-surface-variant px-2 py-1 rounded-md transition-colors cursor-pointer"
          >
            <span className="material-symbols-outlined text-[15px]">download</span>
            <span>Export</span>
          </button>
        </div>
      </div>
      <div className="flex flex-col gap-[2px]">
        {items.map((item, idx) => {
          const isChecked = !!checked[idx]
          return (
            <label 
              key={idx}
              className={`flex items-start gap-sm p-sm rounded-lg cursor-pointer transition-colors ${isChecked ? 'bg-primary-container/10' : 'hover:bg-surface-variant/50'}`}
            >
              <input
                type="checkbox"
                className="mt-1 w-4 h-4 rounded border-outline-variant text-primary focus:ring-primary accent-primary cursor-pointer"
                checked={isChecked}
                onChange={() => toggle(idx)}
              />
              <span className={`text-xs sm:text-body-md font-body-md transition-colors ${isChecked ? 'text-on-surface-variant line-through' : 'text-on-surface'}`}>
                {item}
              </span>
            </label>
          )
        })}
      </div>
    </div>
  )
}

