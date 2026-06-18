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
    <div className="trace-accordion mt-3">
      {/* Header */}
      <button
        id="reasoning-trace-toggle"
        className="trace-accordion-header"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        aria-controls="reasoning-trace-body"
      >
        <span>🔬 Reasoning Trace ({trace.iterations || 1} iteration{(trace.iterations || 1) !== 1 ? 's' : ''})</span>
        <span className={`text-xs transition-transform duration-200 ${open ? 'rotate-180' : ''}`}>
          ▼
        </span>
      </button>

      {/* Body */}
      <AnimatePresence>
        {open && (
          <motion.div
            id="reasoning-trace-body"
            className="trace-accordion-body overflow-hidden"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
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
      <div className="flex-1">
        <div className="flex justify-between items-center">
          <div>
            <span className="font-semibold text-sm text-white">
              {meta.label}
            </span>
            <span className="text-[0.8125rem] text-gray-400 ml-2">
              {meta.description}
            </span>
          </div>
          {data && (
            <button
              className="btn btn-ghost btn-sm text-xs"
              onClick={() => setDetailOpen(o => !o)}
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
              className="mt-2 p-2.5 bg-bgDeep rounded-md text-xs text-gray-200 overflow-auto max-h-[200px] whitespace-pre-wrap break-words"
            >
              {JSON.stringify(data, null, 2)}
            </motion.pre>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
