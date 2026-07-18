import { useState, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import ChatWindow from '../components/Chat/ChatWindow'
import ReasoningTrace from '../components/Chat/ReasoningTrace'

const DEFAULT_TRACE_WIDTH = 360

export default function ChatPage() {
  const [messages, setMessages] = useState([])
  const [selectedMessageIndex, setSelectedMessageIndex] = useState(null)
  const [isTraceOpen, setIsTraceOpen] = useState(true)
  const [traceWidth, setTraceWidth] = useState(DEFAULT_TRACE_WIDTH)

  // Auto-select the latest agent message that has a trace (reasoning_trace or is streaming).
  // Condition includes type==='streaming' so sidebar updates immediately when placeholder is added
  // (streaming placeholder doesn't have reasoning_trace yet, but should still be selected).
  // Uses reduce() instead of findLastIndex() for broader browser compatibility (ES2023).
  useEffect(() => {
    const lastAgentIdx = messages.reduce(
      (acc, m, i) =>
        m.role === 'agent' &&
        (m.content?.reasoning_trace || m.content?.type === 'streaming')
          ? i
          : acc,
      -1
    )
    if (lastAgentIdx !== -1) setSelectedMessageIndex(lastAgentIdx)
  }, [messages.length])

  const selectedMsg = selectedMessageIndex !== null ? messages[selectedMessageIndex] : null
  const activeTrace = selectedMsg?.content?.reasoning_trace ?? null
  // isStreaming: true while the selected message is still a streaming placeholder
  const isStreaming = selectedMsg?.content?.type === 'streaming'

  return (
    <>
      <ChatWindow
        messages={messages}
        setMessages={setMessages}
        selectedMessageIndex={selectedMessageIndex}
        onSelectMessage={setSelectedMessageIndex}
      />

      {/* Reasoning Trace Panel — only visible on xl screens when there are messages */}
      <AnimatePresence>
        {messages.length > 0 && (
          <motion.div
            key="trace-panel"
            initial={{ width: 0, opacity: 0 }}
            animate={{
              width: isTraceOpen ? traceWidth : 48,
              opacity: 1,
            }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ type: 'spring', bounce: 0, duration: 0.4 }}
            className="hidden xl:block shrink-0 overflow-hidden h-full"
          >
            <ReasoningTrace
              trace={activeTrace}
              isStreaming={isStreaming}
              isOpen={isTraceOpen}
              onToggle={() => setIsTraceOpen(prev => !prev)}
              width={traceWidth}
              onWidthChange={setTraceWidth}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
