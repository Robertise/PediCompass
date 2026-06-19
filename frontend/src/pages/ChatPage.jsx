import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import ChatWindow from '../components/Chat/ChatWindow'
import ReasoningTrace from '../components/Chat/ReasoningTrace'

export default function ChatPage() {
  const [messages, setMessages] = useState([])
  
  // Extract reasoning trace from the latest agent message
  const latestTrace = [...messages].reverse().find(m => m.role === 'agent' && m.content?.reasoning_trace)?.content?.reasoning_trace

  return (
    <>
      <ChatWindow messages={messages} setMessages={setMessages} />
      <AnimatePresence>
        {messages.length > 0 && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 360, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ type: 'spring', bounce: 0, duration: 0.5 }}
            className="hidden xl:block shrink-0 overflow-hidden"
          >
            <ReasoningTrace trace={latestTrace} />
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
