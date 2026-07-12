import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import ChatWindow from '../components/Chat/ChatWindow'
import ReasoningTrace from '../components/Chat/ReasoningTrace'

const DEFAULT_TRACE_WIDTH = 360

export default function ChatPage() {
  const [messages, setMessages] = useState([])
  const [isTraceOpen, setIsTraceOpen] = useState(true)
  const [traceWidth, setTraceWidth] = useState(DEFAULT_TRACE_WIDTH)

  // Extract reasoning trace from the latest agent message
  const latestTrace = [...messages]
    .reverse()
    .find(m => m.role === 'agent' && m.content?.reasoning_trace)
    ?.content?.reasoning_trace

  const hasMessages = messages.length > 0

  return (
    <>
      <ChatWindow messages={messages} setMessages={setMessages} />

      {/* Reasoning Trace Panel — only visible on xl screens when there are messages */}
      <AnimatePresence>
        {hasMessages && (
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
              trace={latestTrace}
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
