import { useState } from 'react'

/**
 * Downloadable pre-visit preparation checklist.
 *
 * @param {Object}   props
 * @param {string[]} props.items  - Checklist items from AgentResponse
 */
export default function PreVisitChecklist({ items }) {
  const [checked, setChecked] = useState({})

  if (!items || items.length === 0) return null

  const toggle = (idx) =>
    setChecked(prev => ({ ...prev, [idx]: !prev[idx] }))

  const checkedCount = Object.values(checked).filter(Boolean).length

  return (
    <div className="mt-4">
      <div className="flex justify-between items-center mb-2">
        <p className="font-semibold text-teal-400 uppercase tracking-wide text-xs">📋 Pre-Visit Checklist</p>
        <span className="text-[0.8125rem] text-gray-400">
          {checkedCount}/{items.length} done
        </span>
      </div>

      <div className="bg-bgElevated rounded-md p-2 border border-white/5">
        {items.map((item, idx) => (
          <div
            key={idx}
            className={`checklist-item ${checked[idx] ? 'checklist-item--checked' : ''}`}
            onClick={() => toggle(idx)}
            role="checkbox"
            aria-checked={!!checked[idx]}
            tabIndex={0}
            onKeyDown={(e) => e.key === ' ' && toggle(idx)}
            id={`checklist-item-${idx}`}
          >
            <input
              type="checkbox"
              checked={!!checked[idx]}
              onChange={() => toggle(idx)}
              onClick={(e) => e.stopPropagation()}
              aria-label={item}
            />
            <span className="text-[0.9375rem]">{item}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
