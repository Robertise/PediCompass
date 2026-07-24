import { useState, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const STAGE_META = {
  stage0: {
    label: 'Safety Screen',
    icon: 'health_and_safety',
    description: 'Pediatric emergency red flags — keyword match + Haiku context check',
  },
  content_check: {
    label: 'Content Check',
    icon: 'filter_alt',
    description: 'Rule-based input filtering — greetings, vague, insufficient content',
  },
  intent: {
    label: 'Intent Classification',
    icon: 'psychology_alt',
    description: 'Sonnet tool_use: TRIAGE / GENERAL / HIGH_STAKES_GENERAL',
  },
  stage1: {
    label: 'Query Analysis',
    icon: 'analytics',
    description: 'Age detection and symptom parsing',
  },
  stage2: {
    label: 'Retrieval',
    icon: 'database',
    description: 'Age-stratified guideline retrieval from Qdrant',
  },
  stage3: {
    label: 'Pathway Reasoning',
    icon: 'psychology',
    description: 'Care pathway and urgency assessment via ESI v4',
  },
  openfda_lookup: {
    label: 'Medication Safety',
    icon: 'medication',
    description: 'OpenFDA FAERS pediatric adverse event lookup',
  },
  stage4: {
    label: 'Reflection',
    icon: 'published_with_changes',
    description: 'Completeness and accuracy check',
  },
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
export default function ReasoningTrace({ trace, isStreaming, isOpen, onToggle, width, onWidthChange, isMobile = false }) {
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
      const newWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, (dragStartWidth.current || DEFAULT_WIDTH) + delta))
      onWidthChange?.(newWidth)
    }

    const onMouseUp = () => {
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  }, [width, onWidthChange])

  // ── Collapsed state (Desktop only) ───────────────────────────────────────────
  if (!isOpen && !isMobile) {
    return (
      <aside
        className="w-12 bg-surface-container-low dark:bg-surface-container h-full border-l border-black/5 dark:border-white/5 flex flex-col items-center py-md gap-md shadow-sm shrink-0"
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

  // ── Expanded state (Desktop or Mobile) ───────────────────────────────────────
  return (
    <aside
      className={`bg-surface-container-low dark:bg-surface-container h-full flex flex-col shadow-sm shrink-0 relative ${
        isMobile ? 'w-full border-none' : 'border-l border-black/5 dark:border-white/5'
      }`}
      style={isMobile ? undefined : { width }}
    >
      {/* Drag-to-resize handle — left edge (Desktop only) */}
      {!isMobile && (
        <div
          onMouseDown={handleDragMouseDown}
          className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-primary/30 transition-colors z-20 group"
          title="Drag to resize"
        >
          {/* Visual drag pill */}
          <div className="absolute left-[-2px] top-1/2 -translate-y-1/2 w-1.5 h-10 bg-black/10 dark:bg-white/10 group-hover:bg-primary/50 rounded-full transition-colors" />
        </div>
      )}

      {/* Header */}
      <div className="pl-4 pr-2 py-3 border-b border-black/5 dark:border-white/5 bg-surface-container/50 flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-xs text-on-surface min-w-0">
          <span className="material-symbols-outlined text-[20px] text-tertiary shrink-0">memory</span>
          <h3 className="font-label-md text-label-md uppercase tracking-wider font-bold truncate">
            Reasoning Trace
          </h3>
          {/* Live badge — pulsing dot, only shown during active stream */}
          {isStreaming && (
            <span className="ml-1 flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest text-primary">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary" />
              </span>
              Live
            </span>
          )}
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
        <div className="px-4 py-2 border-b border-black/5 dark:border-white/5 bg-surface-container/30 shrink-0">
          <p className="text-body-sm font-body-sm text-on-surface-variant">
            {trace.iterations || 1} iteration{(trace.iterations || 1) !== 1 ? 's' : ''} completed
            {trace.latencies && Object.keys(trace.latencies).length > 0 && ` · ${Object.values(trace.latencies).reduce((a, b) => a + b, 0) < 1000 ? `${Object.values(trace.latencies).reduce((a, b) => a + b, 0)}ms` : `${(Object.values(trace.latencies).reduce((a, b) => a + b, 0) / 1000).toFixed(1)}s`} total`}
          </p>
        </div>
      ) : (
        <div className="px-4 py-2 border-b border-black/5 dark:border-white/5 shrink-0">
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
                latency_ms={trace.latencies?.[stageKey] ?? null}
                isLast={index === arr.length - 1}
              />
            ))
        )}
      </div>
    </aside>
  )
}

function TraceStageRow({ meta, data, isLast, latency_ms }) {
  const [detailOpen, setDetailOpen] = useState(false)

  return (
    <div className="flex gap-sm">
      <div className="flex flex-col items-center">
        <div className="w-8 h-8 rounded-full bg-surface-variant/50 dark:bg-surface-container-high flex items-center justify-center shrink-0 z-10 shadow-sm">
          <span className="material-symbols-outlined text-[16px] text-primary">{meta.icon}</span>
        </div>
        {!isLast && <div className="w-[2px] h-full bg-black/5 dark:bg-white/5 my-1"></div>}
      </div>
      <div className="flex flex-col gap-xs pb-sm w-full min-w-0">
        <div className="flex justify-between items-start">
          <div className="flex flex-col min-w-0">
            <span className="text-label-md font-label-md text-on-surface">{meta.label}</span>
            <span className="text-body-sm font-body-sm text-on-surface-variant leading-tight">{meta.description}</span>
          </div>
          <div className="flex items-center gap-2 shrink-0 ml-1">
            {latency_ms != null && (
              <span className="text-[11px] font-mono tabular-nums text-on-surface-variant/50">
                {latency_ms < 1000 ? `${latency_ms}ms` : `${(latency_ms / 1000).toFixed(1)}s`}
              </span>
            )}
            {data && (
              <button 
                onClick={() => setDetailOpen(!detailOpen)}
                className="text-[12px] font-label-sm text-primary hover:bg-primary-container/20 px-2 py-1 rounded transition-colors"
              >
                {detailOpen ? 'Hide' : 'View'}
              </button>
            )}
          </div>
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
              <pre className="mt-2 p-sm bg-black/5 dark:bg-black/30 rounded-lg text-[11px] font-mono text-on-surface-variant overflow-x-auto whitespace-pre-wrap break-words max-h-[250px] overflow-y-auto shadow-inner">
                {JSON.stringify(data, null, 2)}
              </pre>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
