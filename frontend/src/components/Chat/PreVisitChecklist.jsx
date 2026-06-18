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
    <div style={{ marginTop: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <p className="section-heading">📋 Pre-Visit Checklist</p>
        <span style={{ fontSize: '0.8125rem', color: 'var(--color-gray-400)' }}>
          {checkedCount}/{items.length} done
        </span>
      </div>

      <div style={{
        background: 'var(--color-bg-elevated)',
        borderRadius: 'var(--radius-md)',
        padding: '8px',
        border: '1px solid rgba(255,255,255,0.05)',
      }}>
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
            <span style={{ fontSize: '0.9375rem' }}>{item}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
