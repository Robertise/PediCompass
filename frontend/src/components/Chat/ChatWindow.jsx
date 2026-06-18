import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import MessageBubble from './MessageBubble'
import ProfileSelector from '../Profiles/ProfileSelector'
import { chatApi } from '../../api/client'
import { useAuthStore } from '../../store/authStore'

export default function ChatWindow() {
  const { user } = useAuthStore()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [selectedProfileId, setSelectedProfileId] = useState(null)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const startSession = async () => {
    try {
      const res = await chatApi.createSession(selectedProfileId)
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
      const res = await chatApi.sendMessage(currentSessionId, userMessage, selectedProfileId)
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
    <div className="chat-main flex flex-col h-full w-full max-w-[760px] mx-auto px-4 md:px-0">
      {user && (
        <div className="py-4 border-b border-white/5">
          <ProfileSelector 
            selectedId={selectedProfileId} 
            onChange={setSelectedProfileId} 
            disabled={messages.length > 0} 
          />
        </div>
      )}

      <div className="chat-messages flex-1 overflow-y-auto py-6 flex flex-col gap-4">
        {messages.length === 0 ? (
          <div className="text-center mt-10 text-gray-400">
            <p className="text-xl mb-2">👋 Welcome to PediCompass</p>
            <p>Describe your child's symptoms to get started.</p>
            {!user && <p className="mt-2 text-sm">You are using Guest Mode. I will ask for your child's age first.</p>}
          </div>
        ) : (
          messages.map((msg, idx) => (
            <motion.div 
              key={idx}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <MessageBubble role={msg.role} content={msg.content} />
            </motion.div>
          ))
        )}
        
        {loading && (
          <div className="flex gap-2 p-4">
            <div className="spinner" />
            <span className="text-gray-400 text-sm">Analyzing...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-bar py-4 border-t border-white/5">
        <div className="flex gap-2 items-end">
          <textarea
            className="chat-textarea flex-1 resize-none min-h-[52px] max-h-[200px] p-3 bg-bgElevated border border-gray-600 rounded-lg text-white font-sans text-[15px] leading-relaxed outline-none transition-colors focus:border-teal-400 focus:ring-2 focus:ring-teal-400/30 overflow-y-auto"
            placeholder="Type your message here..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            rows={1}
          />
          <button 
            className="btn btn-primary h-[52px] px-6 shrink-0" 
            onClick={handleSend}
            disabled={!input.trim() || loading}
          >
            Send
          </button>
        </div>
        <p className="text-xs text-gray-400 text-center mt-2">
          For informational purposes only. In a medical emergency, call 999 or 911.
        </p>
      </div>
    </div>
  )
}
