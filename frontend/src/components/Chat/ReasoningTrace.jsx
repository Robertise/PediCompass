import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const STAGE_META = {
  stage0: { label: 'Safety Screen',      icon: '🛡️', description: 'Pediatric emergency red flags checked' },
  stage1: { label: 'Query Analysis',     icon: '🔍', description: 'Age detection and symptom parsing'     },
  stage2: { label: 'Retrieval',          icon: '📚', description: 'Age-stratified guideline retrieval'    },
  stage3: { label: 'Pathway Reasoning',  icon: '🧠', description: 'Care pathway and urgency assessment'   },
  stage4: { label: 'Reflection',         icon: '🔄', description: 'Completeness and accuracy check'       },
}

/**
 * Collapsible reasoning trace panel.
 * Shows each agent stage with its key decision data.
 *
 * @param {Object} props
 * @param {Object} props.trace  - ReasoningTrace object from AgentResponse
 */
export default function ReasoningTrace({ trace }) {
  const [open, setOpen] = useState(false)

  if (!trace) return null

  const stages = Object.entries(STAGE_META).filter(([key]) => trace[key])

  return (
    <div className="trace-accordion" style={{ marginTop: '12px' }}>
      {/* Header */}
      <button
        id="reasoning-trace-toggle"
        className="trace-accordion-header"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        aria-controls="reasoning-trace-body"
      >
        <span>🔬 Reasoning Trace ({trace.iterations || 1} iteration{(trace.iterations || 1) !== 1 ? 's' : ''})</span>
        <span style={{ fontSize: '0.75rem', transition: 'transform 200ms' }}>
          {open ? '▲' : '▼'}
        </span>
      </button>

      {/* Body */}
      <AnimatePresence>
        {open && (
          <motion.div
            id="reasoning-trace-body"
            className="trace-accordion-body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{ overflow: 'hidden' }}
          >
            {stages.map(([stageKey, meta]) => (
              <TraceStageRow
                key={stageKey}
                meta={meta}
                data={trace[stageKey]}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function TraceStageRow({ meta, data }) {
  const [detailOpen, setDetailOpen] = useState(false)

  return (
    <div className="trace-stage">
      <div className="trace-stage-icon" aria-hidden="true">
        {meta.icon}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--color-white)' }}>
              {meta.label}
            </span>
            <span style={{ fontSize: '0.8125rem', color: 'var(--color-gray-400)', marginLeft: '8px' }}>
              {meta.description}
            </span>
          </div>
          {data && (
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setDetailOpen(o => !o)}
              style={{ fontSize: '0.75rem' }}
            >
              {detailOpen ? 'Hide' : 'Details'}
            </button>
          )}
        </div>

        <AnimatePresence>
          {detailOpen && data && (
            <motion.pre
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.15 }}
              style={{
                marginTop: '8px',
                padding: '10px',
                background: 'var(--color-bg-deep)',
                borderRadius: '6px',
                fontSize: '0.75rem',
                color: 'var(--color-gray-200)',
                overflow: 'auto',
                maxHeight: '200px',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {JSON.stringify(data, null, 2)}
            </motion.pre>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
