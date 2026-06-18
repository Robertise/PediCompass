import { useState } from 'react'

export default function PreVisitChecklist({ items }) {
  const [checked, setChecked] = useState({})

  if (!items || items.length === 0) return null

  const toggle = (idx) =>
    setChecked(prev => ({ ...prev, [idx]: !prev[idx] }))

  const checkedCount = Object.values(checked).filter(Boolean).length

  return (
    <div className="flex flex-col gap-sm bg-surface-container-low p-sm rounded-xl border border-outline-variant/30">
      <div className="flex justify-between items-center">
        <span className="text-label-md font-label-md text-on-surface flex items-center gap-xs">
          <span className="material-symbols-outlined text-primary text-[20px]">checklist</span> Before Your Visit
        </span>
        <span className="text-label-sm font-label-sm bg-primary-container text-on-primary-container px-2 py-[2px] rounded-full">
          {checkedCount}/{items.length} Ready
        </span>
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
              <span className={`text-body-md font-body-md transition-colors ${isChecked ? 'text-on-surface-variant line-through' : 'text-on-surface'}`}>
                {item}
              </span>
            </label>
          )
        })}
      </div>
    </div>
  )
}
