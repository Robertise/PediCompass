import { useState, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const STAGE_META = {
  stage0: { label: 'Safety Screen',      icon: 'health_and_safety', description: 'Pediatric emergency red flags checked' },
  stage1: { label: 'Query Analysis',     icon: 'analytics',         description: 'Age detection and symptom parsing'     },
  stage2: { label: 'Retrieval',          icon: 'database',          description: 'Age-stratified guideline retrieval'    },
  stage3: { label: 'Pathway Reasoning',  icon: 'psychology',        description: 'Care pathway and urgency assessment'   },
  stage4: { label: 'Reflection',         icon: 'published_with_changes', description: 'Completeness and accuracy check'       },
}

const MIN_WIDTH = 260
const MAX_WIDTH = 560
const DEFAULT_WIDTH = 360

/**
 * ReasoningTrace panel.
 *
 * Props:
 *   trace        — reasoning trace object from the last agent response (or null)
 *   isOpen       — whether the panel is expanded or collapsed
 *   onToggle     — callback to toggle open/closed (controlled by ChatPage)
 *   width        — controlled width in px
 *   onWidthChange — callback(newWidth) from drag-to-resize
 */
export default function ReasoningTrace({ trace, isOpen, onToggle, width, onWidthChange }) {
  // ── Drag-to-resize ───────────────────────────────────────────────────────────
  const dragStartX = useRef(null)
  const dragStartWidth = useRef(null)

  const handleDragMouseDown = useCallback((e) => {
    e.preventDefault()
    dragStartX.current = e.clientX
    dragStartWidth.current = width

    const onMouseMove = (moveEvent) => {
      // Dragging the left handle leftward increases width (panel is on the right)
      const delta = dragStartX.current - moveEvent.clientX
      const newWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, dragStartWidth.current + delta))
      onWidthChange(newWidth)
    }

    const onMouseUp = () => {
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  }, [width, onWidthChange])

  // ── Collapsed state — show only a slim icon strip ────────────────────────────
  if (!isOpen) {
    return (
      <aside
        className="w-12 bg-surface-container-low dark:bg-surface-container-highest h-full border-l border-outline-variant/30 flex flex-col items-center py-md gap-md shadow-sm shrink-0"
        style={{ width: 48 }}
      >
        {/* Re-open button */}
        <button
          onClick={onToggle}
          title="Show reasoning trace"
          className="w-9 h-9 rounded-full flex items-center justify-center text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors"
        >
          <span className="material-symbols-outlined text-[20px]">memory</span>
        </button>
        {/* Vertical label */}
        <span
          className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant opacity-50 select-none"
          style={{ writingMode: 'vertical-rl', textOrientation: 'mixed', transform: 'rotate(180deg)' }}
        >
          Reasoning
        </span>
      </aside>
    )
  }

  // ── Expanded state ───────────────────────────────────────────────────────────
  return (
    <aside
      className="bg-surface-container-low dark:bg-surface-container-highest h-full border-l border-outline-variant/30 flex flex-col shadow-sm shrink-0 relative"
      style={{ width }}
    >
      {/* Drag-to-resize handle — left edge */}
      <div
        onMouseDown={handleDragMouseDown}
        className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-primary/30 transition-colors z-20 group"
        title="Drag to resize"
      >
        {/* Visual drag pill */}
        <div className="absolute left-[-2px] top-1/2 -translate-y-1/2 w-1.5 h-10 bg-outline-variant/40 group-hover:bg-primary/50 rounded-full transition-colors" />
      </div>

      {/* Header */}
      <div className="pl-4 pr-2 py-3 border-b border-outline-variant/30 bg-surface-container/50 flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-xs text-on-surface min-w-0">
          <span className="material-symbols-outlined text-[20px] text-tertiary shrink-0">memory</span>
          <h3 className="font-label-md text-label-md uppercase tracking-wider font-bold truncate">
            Reasoning Trace
          </h3>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {/* Collapse button */}
          <button
            onClick={onToggle}
            title="Collapse panel"
            className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">chevron_right</span>
          </button>
        </div>
      </div>

      {/* Sub-header: iteration/latency info */}
      {trace ? (
        <div className="px-4 py-2 border-b border-outline-variant/20 bg-surface-container/30 shrink-0">
          <p className="text-body-sm font-body-sm text-on-surface-variant">
            {trace.iterations || 1} iteration{(trace.iterations || 1) !== 1 ? 's' : ''} completed
            {trace.latency_ms ? ` in ${(trace.latency_ms / 1000).toFixed(1)}s` : ''}
          </p>
        </div>
      ) : (
        <div className="px-4 py-2 border-b border-outline-variant/20 shrink-0">
          <p className="text-body-sm font-body-sm text-on-surface-variant">
            Waiting for AI analysis…
          </p>
        </div>
      )}

      {/* Stage rows */}
      <div className="flex-1 overflow-y-auto p-md space-y-md">
        {!trace ? (
          <div className="flex flex-col items-center gap-sm text-center text-on-surface-variant opacity-50 mt-8">
            <span className="material-symbols-outlined text-[48px]">troubleshoot</span>
            <p className="text-body-md font-body-md">Clinical reasoning steps will appear here.</p>
          </div>
        ) : (
          Object.entries(STAGE_META)
            .filter(([key]) => trace[key])
            .map(([stageKey, meta], index, arr) => (
              <TraceStageRow
                key={stageKey}
                meta={meta}
                data={trace[stageKey]}
                isLast={index === arr.length - 1}
              />
            ))
        )}
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
      <div className="flex flex-col gap-xs pb-sm w-full min-w-0">
        <div className="flex justify-between items-start">
          <div className="flex flex-col min-w-0">
            <span className="text-label-md font-label-md text-on-surface">{meta.label}</span>
            <span className="text-body-sm font-body-sm text-on-surface-variant leading-tight">{meta.description}</span>
          </div>
          {data && (
            <button 
              onClick={() => setDetailOpen(!detailOpen)}
              className="text-[12px] font-label-sm text-primary hover:bg-primary-container/20 px-2 py-1 rounded transition-colors shrink-0 ml-1"
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
