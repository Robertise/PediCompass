import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const STAGE_META = {
  stage0: { label: 'Safety Screen',      icon: 'health_and_safety', description: 'Pediatric emergency red flags checked' },
  stage1: { label: 'Query Analysis',     icon: 'analytics',         description: 'Age detection and symptom parsing'     },
  stage2: { label: 'Retrieval',          icon: 'database',          description: 'Age-stratified guideline retrieval'    },
  stage3: { label: 'Pathway Reasoning',  icon: 'psychology',        description: 'Care pathway and urgency assessment'   },
  stage4: { label: 'Reflection',         icon: 'published_with_changes', description: 'Completeness and accuracy check'       },
}

export default function ReasoningTrace({ trace }) {
  if (!trace) {
    return (
      <aside className="w-[360px] bg-surface-container-low dark:bg-surface-container-highest h-full border-l border-outline-variant/30 flex flex-col hidden xl:flex shadow-sm">
        <div className="p-md border-b border-outline-variant/30 bg-surface-container/50">
          <div className="flex items-center gap-xs text-on-surface">
            <span className="material-symbols-outlined text-[20px] text-tertiary">memory</span>
            <h3 className="font-label-md text-label-md uppercase tracking-wider font-bold">Reasoning Trace</h3>
          </div>
          <p className="text-body-sm font-body-sm text-on-surface-variant mt-1">
            Waiting for AI analysis...
          </p>
        </div>
        <div className="flex-1 overflow-y-auto p-md flex items-center justify-center text-on-surface-variant text-center opacity-50">
          <div className="flex flex-col items-center gap-sm">
            <span className="material-symbols-outlined text-[48px]">troubleshoot</span>
            <p className="text-body-md font-body-md">Clinical reasoning steps will appear here.</p>
          </div>
        </div>
      </aside>
    )
  }

  const stages = Object.entries(STAGE_META).filter(([key]) => trace[key])

  return (
    <aside className="w-[360px] bg-surface-container-low dark:bg-surface-container-highest h-full border-l border-outline-variant/30 flex flex-col hidden xl:flex shadow-sm">
      <div className="p-md border-b border-outline-variant/30 bg-surface-container/50">
        <div className="flex items-center gap-xs text-on-surface">
          <span className="material-symbols-outlined text-[20px] text-tertiary">memory</span>
          <h3 className="font-label-md text-label-md uppercase tracking-wider font-bold">Reasoning Trace</h3>
        </div>
        <p className="text-body-sm font-body-sm text-on-surface-variant mt-1">
          {trace.iterations || 1} iteration{(trace.iterations || 1) !== 1 ? 's' : ''} completed in {(trace.latency_ms / 1000).toFixed(1)}s
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-md space-y-md">
        {stages.map(([stageKey, meta], index) => (
          <TraceStageRow
            key={stageKey}
            meta={meta}
            data={trace[stageKey]}
            isLast={index === stages.length - 1}
          />
        ))}
      </div>
    </aside>
  )
}

function TraceStageRow({ meta, data, isLast }) {
  const [detailOpen, setDetailOpen] = useState(false)

  return (
    <div className="flex gap-sm">
      <div className="flex flex-col items-center">
        <div className="w-8 h-8 rounded-full bg-surface-container-high flex items-center justify-center border border-outline-variant/30 shrink-0 z-10">
          <span className="material-symbols-outlined text-[16px] text-on-surface-variant">{meta.icon}</span>
        </div>
        {!isLast && <div className="w-[2px] h-full bg-outline-variant/30 my-1"></div>}
      </div>
      <div className="flex flex-col gap-xs pb-sm w-full">
        <div className="flex justify-between items-start">
          <div className="flex flex-col">
            <span className="text-label-md font-label-md text-on-surface">{meta.label}</span>
            <span className="text-body-sm font-body-sm text-on-surface-variant leading-tight">{meta.description}</span>
          </div>
          {data && (
            <button 
              onClick={() => setDetailOpen(!detailOpen)}
              className="text-[12px] font-label-sm text-primary hover:bg-primary-container/20 px-2 py-1 rounded transition-colors"
            >
              {detailOpen ? 'Hide' : 'View'}
            </button>
          )}
        </div>
        
        <AnimatePresence>
          {detailOpen && data && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="overflow-hidden"
            >
              <pre className="mt-2 p-sm bg-surface-container-lowest rounded-lg border border-outline-variant/30 text-[11px] font-mono text-on-surface-variant overflow-x-auto whitespace-pre-wrap break-words max-h-[250px] overflow-y-auto shadow-inner">
                {JSON.stringify(data, null, 2)}
              </pre>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
