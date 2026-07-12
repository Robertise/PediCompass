import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import MessageBubble from './MessageBubble'
import { chatApi } from '../../api/client'
import { useAuthStore } from '../../store/authStore'
import { useAppStore, GUEST_PROFILE_ID } from '../../store/appStore'

export default function ChatWindow({ messages, setMessages }) {
  const { user } = useAuthStore()
  const { selectedProfileId } = useAppStore()
  // Map sentinel "guest" → null so the backend receives a real profile_id or null
  const apiProfileId = (!selectedProfileId || selectedProfileId === GUEST_PROFILE_ID)
    ? null
    : selectedProfileId
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const startSession = async () => {
    try {
      const res = await chatApi.createSession(apiProfileId)
      setSessionId(res.data.session_id)
      return res.data.session_id
    } catch (err) {
      console.error('Failed to create session', err)
      return null
    }
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    let currentSessionId = sessionId
    if (!currentSessionId) {
      currentSessionId = await startSession()
      if (!currentSessionId) {
        setMessages(prev => [...prev, { role: 'agent', content: { type: 'error', reason: 'Failed to connect to server.' } }])
        setLoading(false)
        return
      }
    }

    try {
      const res = await chatApi.sendMessage(currentSessionId, userMessage, apiProfileId)
      setMessages(prev => [...prev, { role: 'agent', content: res.data }])
    } catch (err) {
      console.error(err)
      setMessages(prev => [...prev, { role: 'agent', content: { type: 'error', reason: 'Sorry, I encountered an error processing your request.' } }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <main className="flex-1 flex flex-col h-full bg-surface-lowest relative">
      <div className={`flex-1 relative ${messages.length === 0 ? 'overflow-hidden flex items-center justify-center px-4 md:px-8' : 'overflow-y-auto py-md lg:py-lg px-4 md:px-8 space-y-lg'}`}>
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-on-surface-variant max-w-lg mx-auto text-center gap-sm">
            <img src="/logo_trans_bg.svg" alt="PediCompass Logo" className="w-[50px] h-[50px] object-contain opacity-40 mb-sm grayscale-[20%]" />
            <h2 className="text-headline-md font-headline-md text-on-surface">How can I help you today?</h2>
            <p className="text-body-md font-body-md">
              Select a child profile above and describe their symptoms. I will guide you through evidence-based pediatric care pathways.
            </p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <motion.div 
              key={idx}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="w-full"
            >
              <MessageBubble role={msg.role} content={msg.content} />
            </motion.div>
          ))
        )}

        {loading && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="max-w-4xl mx-auto w-full py-xs"
          >
            <div className="flex items-center gap-3 w-fit text-on-surface-variant font-body-md">
              <div className="flex gap-1.5 items-center">
                <span className="w-2.5 h-2.5 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '0s' }}></span>
                <span className="w-2.5 h-2.5 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '0.15s' }}></span>
                <span className="w-2.5 h-2.5 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '0.3s' }}></span>
              </div>
              <span className="animate-pulse text-sm">Thinking...</span>
            </div>
          </motion.div>
        )}
        <div ref={messagesEndRef} className="h-20"></div> {/* padding bottom */}
      </div>

      {/* Input Area */}
      <div className="py-md px-4 md:px-8 bg-surface border-t border-outline-variant/20 sticky bottom-0 z-10 w-full">
        <div className="max-w-4xl mx-auto flex flex-col items-center">
          <div className="flex items-center w-full bg-surface-container-lowest rounded-full px-sm py-xs border border-outline-variant/40 focus-within:border-primary transition-colors shadow-sm pl-4">
            <textarea
              className="flex-1 bg-transparent border-none focus:ring-0 text-body-md font-body-md text-on-surface placeholder:text-outline py-sm px-sm resize-none"
              placeholder={selectedProfileId ? 'Ask a follow-up question or describe symptoms...' : 'Describe your child\'s symptoms (select a profile above for personalized guidance)...'}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              onInput={(e) => { e.target.style.height = ''; e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px'; }}
            />
            <button 
              className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-on-primary hover:bg-primary-fixed-variant transition-colors shadow-sm disabled:opacity-50"
              onClick={handleSend}
              disabled={!input.trim() || loading}
            >
              <span className="material-symbols-outlined text-[20px]">send</span>
            </button>
          </div>
          <div className="text-center mt-xs text-[11px] text-on-surface-variant flex items-center justify-center gap-xs">
            <span className="material-symbols-outlined text-[14px]">lock</span> Your information is private and secure. Not a medical diagnosis.
          </div>
        </div>
      </div>
    </main>
  )
}
