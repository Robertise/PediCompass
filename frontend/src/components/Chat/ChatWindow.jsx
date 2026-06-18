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
    <div className="chat-main">
      {user && (
        <div style={{ padding: '16px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <ProfileSelector 
            selectedId={selectedProfileId} 
            onChange={setSelectedProfileId} 
            disabled={messages.length > 0} 
          />
        </div>
      )}

      <div className="chat-messages">
        {messages.length === 0 ? (
          <div style={{ textAlign: 'center', marginTop: '40px', color: 'var(--color-gray-400)' }}>
            <p style={{ fontSize: '1.25rem', marginBottom: '8px' }}>👋 Welcome to PediCompass</p>
            <p>Describe your child's symptoms to get started.</p>
            {!user && <p style={{ marginTop: '8px', fontSize: '0.875rem' }}>You are using Guest Mode. I will ask for your child's age first.</p>}
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
          <div style={{ display: 'flex', gap: '8px', padding: '16px' }}>
            <div className="spinner" />
            <span style={{ color: 'var(--color-gray-400)', fontSize: '0.875rem' }}>Analyzing...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-bar">
        <div className="chat-input-wrapper">
          <textarea
            className="chat-textarea"
            placeholder="Type your message here..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            rows={1}
          />
          <button 
            className="btn btn-primary" 
            onClick={handleSend}
            disabled={!input.trim() || loading}
            style={{ height: '52px', padding: '0 24px' }}
          >
            Send
          </button>
        </div>
        <p style={{ fontSize: '0.75rem', color: 'var(--color-gray-400)', textAlign: 'center', marginTop: '8px' }}>
          For informational purposes only. In a medical emergency, call 999 or 911.
        </p>
      </div>
    </div>
  )
}
